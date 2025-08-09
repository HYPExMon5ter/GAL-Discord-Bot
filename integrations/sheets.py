# integrations/sheets.py

import asyncio
import logging
import os
import json
import time
from typing import Dict, List, Optional, Tuple, Any

# ---------- BotLogger (graceful) ----------
try:
    from helpers.logging_helper import BotLogger
except Exception:
    BotLogger = None

def _bl(level: str, msg: str, tag: str = "SHEETS"):
    try:
        if BotLogger:
            getattr(BotLogger, level)(msg, tag)
        else:
            getattr(logging, level)(msg)
    except Exception:
        try:
            getattr(logging, level)(msg)
        except Exception:
            pass

# ---------- Google Sheets deps ----------
SHEETS_AVAILABLE = True
try:
    import gspread_asyncio
    from google.oauth2.service_account import Credentials
except Exception as e:
    SHEETS_AVAILABLE = False
    gspread_asyncio = None
    Credentials = None
    _bl("warning", f"Google Sheets dependencies not installed - running in fallback mode: {e}")

# ---------- Config & helpers ----------
from config import get_sheet_settings, col_to_index, BotConstants
from core.persistence import get_event_mode_for_guild

# ---------- Globals ----------
_client = None                # authorized gspread client (async)
_client_loop: Optional[asyncio.AbstractEventLoop] = None
cache_lock = asyncio.Lock()
sheet_cache: Dict[str, Any] = {
    "users": {},              # Dict[str, Tuple[row, ign, reg, ci, team, alt]]
    "last_refresh": 0.0,
    "refresh_in_progress": False,
}
CACHE_REFRESH_SECONDS = 600  # keep legacy interval

# ---------- Utilities ----------
def ordinal_suffix(n: int) -> str:
    n = int(n)
    if 10 <= (n % 100) <= 20:
        suf = "th"
    else:
        suf = {1:"st",2:"nd",3:"rd"}.get(n % 10, "th")
    return f"{n}{suf}"

async def retry_until_successful(coro_fn, *args, retries: int = 3, delay: float = 1.5, **kwargs):
    """Retry an async callable a few times before giving up."""
    attempt = 0
    while True:
        try:
            res = coro_fn(*args, **kwargs)
            if asyncio.iscoroutine(res):
                return await res
            return res
        except Exception as e:
            attempt += 1
            if attempt > retries:
                raise
            _bl("warning", f"Sheets op failed (attempt {attempt}/{retries}), retrying in {delay}s: {e}")
            await asyncio.sleep(delay)

def _resolve_guild_id(bot=None) -> str:
    """Find the single active guild id for this bot process."""
    gid = os.getenv("GAL_GUILD_ID")
    if gid:
        return str(gid)
    try:
        if bot and getattr(bot, "guilds", None):
            for g in bot.guilds:
                if g is not None:
                    return str(g.id)
    except Exception:
        pass
    return str(getattr(BotConstants, "TEST_GUILD_ID", "1385739351505240074"))

# ---------- Credentials (hard‑code google-creds.json in repo root) ----------

def _get_creds() -> Optional[Credentials]:
    """Load service account credentials directly from google-creds.json (repo root)."""
    try:
        # integrations/ -> project root
        path = os.path.join(os.path.dirname(__file__), "..", "google-creds.json")
        path = os.path.abspath(path)
        if os.path.exists(path):
            return Credentials.from_service_account_file(
                path,
                scopes=[
                    "https://www.googleapis.com/auth/spreadsheets",
                    "https://www.googleapis.com/auth/drive",
                ],
            )
        _bl("error", f"Google creds file not found at {path}")
    except Exception as e:
        _bl("error", f"Failed to load Google credentials: {e}")
    return None

# ---------- Client lifecycle with loop awareness ----------

async def _authorize_client() -> Optional[Any]:
    """(Re)authorize a gspread client bound to the current running loop."""
    global _client, _client_loop
    if not SHEETS_AVAILABLE:
        return None
    creds = _get_creds()
    if not creds:
        _bl("error", "No Google credentials found; expected google-creds.json in project root")
        return None
    try:
        agcm = gspread_asyncio.AsyncioGspreadClientManager(lambda: creds)
        client = await agcm.authorize()
        _bl("info", "✅ Google Sheets client authorized")
        _client = client
        try:
            _client_loop = asyncio.get_running_loop()
        except RuntimeError:
            _client_loop = None
        return _client
    except Exception as e:
        _bl("error", f"❌ Failed to authorize Google Sheets client: {e}")
        _client = None
        _client_loop = None
        return None

async def get_client() -> Optional[Any]:
    """Return a client tied to the *current* running loop. Re‑authorize if needed."""
    global _client, _client_loop
    if not SHEETS_AVAILABLE:
        _bl("warning", "Sheets not available - returning None client")
        return None

    # If no client yet, or previous loop is closed/different, re‑authorize
    need_new = False
    if _client is None:
        need_new = True
    else:
        try:
            current_loop = asyncio.get_running_loop()
        except RuntimeError:
            current_loop = None
        if _client_loop is None or current_loop is None:
            need_new = True
        elif _client_loop is not current_loop or _client_loop.is_closed():
            need_new = True

    if need_new:
        return await _authorize_client()
    return _client

# ---------- Sheet helpers ----------

async def _open_spreadsheet_for_guild(guild_id: str) -> Optional[Any]:
    """Open the spreadsheet for the guild's current mode with test/prod selection by guild id."""
    c = await get_client()
    if not c:
        return None
    mode = get_event_mode_for_guild(guild_id) or "normal"
    settings = get_sheet_settings(mode, guild_id)
    sheet_url = settings.get("sheet_url") or settings.get("prod_sheet_url") or settings.get("test_sheet_url")
    if not sheet_url:
        _bl("error", f"No sheet_url configured for mode={mode}, guild={guild_id}")
        return None
    try:
        ss = await c.open_by_url(sheet_url)
        return ss
    except Exception as e:
        # If loop mismatch surfaced late, try one re‑authorize + retry
        _bl("warning", f"open_by_url failed: {e}. Re‑authorizing client once and retrying…")
        c2 = await _authorize_client()
        if not c2:
            _bl("error", f"Failed to re‑authorize client after error: {e}")
            return None
        try:
            ss = await c2.open_by_url(sheet_url)
            return ss
        except Exception as e2:
            _bl("error", f"Failed to open spreadsheet for guild {guild_id}: {e2}")
            return None

async def get_sheet_for_guild(guild_id: str, worksheet_name: str = "GAL Database"):
    """Return a gspread Worksheet or None."""
    ss = await _open_spreadsheet_for_guild(guild_id)
    if not ss:
        return None
    try:
        try:
            ws = await ss.worksheet(worksheet_name)
        except Exception:
            ws_list = await ss.worksheets()
            ws = ws_list[0] if ws_list else None
        return ws
    except Exception as e:
        _bl("error", f"Failed to get worksheet for guild {guild_id}: {e}")
        return None

def _get_col_indices(settings: Dict[str, Any]) -> Dict[str, int]:
    """Resolve 1‑based column indexes from settings (Excel‑style letters)."""
    mapping = {}
    for k in ("discord_col", "pronouns_col", "ign_col", "alt_ign_col", "team_col", "registered_col", "checkin_col"):
        v = settings.get(k)
        if v:
            try:
                mapping[k] = col_to_index(v)
            except Exception as e:
                _bl("warning", f"Invalid column '{k}={v}': {e}")
    return mapping

def _row_to_tuple(row_vals: List[str], cols: Dict[str, int], mode: str) -> Optional[Tuple[int, str, str, str, str, str]]:
    """Convert a row into cache tuple: (rownum, ign, reg, ci, team, alt)."""
    def get(col_key: str, default: str = "") -> str:
        idx = cols.get(col_key)
        if not idx:
            return default
        return row_vals[idx - 1] if idx - 1 < len(row_vals) else default

    ign = get("ign_col", "")
    alt = get("alt_ign_col", "")
    reg = str(get("registered_col", "")).upper()
    ci  = str(get("checkin_col", "")).upper()
    team = get("team_col", "") if mode == "doubleup" else ""

    if not any([ign, alt, reg, ci, team]):
        return None

    return (0, ign, reg, ci, team, alt)

# ---------- Main API (legacy shape preserved) ----------

async def refresh_sheet_cache(bot=None) -> Tuple[int, int]:
    """Legacy cache refresh that autodetects the single active guild."""
    if not SHEETS_AVAILABLE:
        _bl("debug", "Sheets not available - using empty cache")
        async with cache_lock:
            sheet_cache["users"] = {}
            sheet_cache["last_refresh"] = time.time()
            sheet_cache["refresh_in_progress"] = False
        return 0, 0

    guild_id = _resolve_guild_id(bot)
    mode = get_event_mode_for_guild(guild_id) or "normal"
    settings = get_sheet_settings(mode, guild_id)
    header_row = int(settings.get("header_line_num", 2))
    cols = _get_col_indices(settings)

    async with cache_lock:
        if sheet_cache["refresh_in_progress"]:
            _bl("debug", "Cache refresh already in progress")
            reg_ct = sum(1 for v in sheet_cache["users"].values() if len(v) > 2 and v[2] == "TRUE")
            ci_ct  = sum(1 for v in sheet_cache["users"].values() if len(v) > 3 and v[2] == "TRUE" and v[3] == "TRUE")
            return reg_ct, ci_ct
        sheet_cache["refresh_in_progress"] = True

    try:
        ws = await get_sheet_for_guild(guild_id)
        if not ws:
            _bl("warning", f"Cannot refresh cache - worksheet unavailable for guild {guild_id}")
            return 0, 0

        values = await retry_until_successful(ws.get_all_values)
        if not values:
            _bl("warning", "Sheet has no values")
            return 0, 0

        start_idx = max(header_row, 1)  # 1‑based header
        users: Dict[str, Tuple[int, str, str, str, str, str]] = {}

        for r_index_1based in range(start_idx + 1, len(values) + 1):
            row_vals = values[r_index_1based - 1]
            discord_tag = ""
            d_idx = cols.get("discord_col")
            if d_idx and d_idx - 1 < len(row_vals):
                discord_tag = (row_vals[d_idx - 1] or "").strip()

            if not discord_tag:
                continue

            tpl = _row_to_tuple(row_vals, cols, mode)
            if tpl is None:
                continue

            tpl = (r_index_1based, tpl[1], tpl[2], tpl[3], tpl[4], tpl[5])
            users[discord_tag] = tpl

        async with cache_lock:
            sheet_cache["users"] = users
            sheet_cache["last_refresh"] = time.time()
            sheet_cache["refresh_in_progress"] = False

        reg_ct = sum(1 for v in users.values() if len(v) > 2 and v[2] == "TRUE")
        ci_ct  = sum(1 for v in users.values() if len(v) > 3 and v[2] == "TRUE" and v[3] == "TRUE")
        _bl("info", f"[SHEET_OPS] Retrieved {reg_ct} registered users")
        return reg_ct, ci_ct

    except Exception as e:
        async with cache_lock:
            sheet_cache["refresh_in_progress"] = False
        _bl("error", f"Failed to refresh sheet cache: {e}")
        return 0, 0

# --------- Minimal ops to keep legacy imports working ----------

async def find_or_register_user(
    guild_id: str,
    discord_tag: str,
    ign: str,
    pronouns: str = "",
    alt_igns: str = "",
    team_name: str = ""
) -> bool:
    try:
        await refresh_sheet_cache()  # ensure cache exists
        async with cache_lock:
            row = sheet_cache["users"].get(discord_tag, (0, ign, "TRUE", "FALSE", team_name, alt_igns))
            sheet_cache["users"][discord_tag] = row
        return True
    except Exception as e:
        _bl("error", f"find_or_register_user failed for {discord_tag}: {e}")
        return False

# --------- Health & config ----------

async def health_check() -> Dict[str, Any]:
    status = {
        "client_initialized": False,
        "credentials_valid": False,
        "status": False,
    }
    if not SHEETS_AVAILABLE:
        status["error"] = "Google Sheets dependencies not installed"
        return status
    try:
        c = await get_client()
        if c:
            status["client_initialized"] = True
            status["credentials_valid"] = True
            status["status"] = True
    except Exception as e:
        status["error"] = str(e)
    return status

def validate_sheet_config(mode: str) -> Dict[str, Any]:
    out = {"valid": True, "errors": []}
    try:
        settings = get_sheet_settings(mode)
        for k in ("discord_col", "ign_col", "registered_col", "checkin_col"):
            v = settings.get(k)
            if not v:
                out["valid"] = False
                out["errors"].append(f"Missing column: {k}")
    except Exception as e:
        out["valid"] = False
        out["errors"].append(str(e))
    return out

async def initialize_sheets():
    if not SHEETS_AVAILABLE:
        _bl("warning", "📊 Google Sheets integration not available")
        return
    try:
        # Defer full client auth to first use on current loop to avoid loop mismatch
        creds = _get_creds()
        if creds:
            _bl("info", "Google credentials located; client will authorize on first use")
        else:
            _bl("error", "No Google credentials found during init")
    except Exception as e:
        _bl("error", f"Failed to initialize Google Sheets: {e}")

# ---------- Exports ----------
__all__ = [
    "refresh_sheet_cache",
    "sheet_cache",
    "cache_lock",
    "get_sheet_for_guild",
    "retry_until_successful",
    "ordinal_suffix",
    "find_or_register_user",
    "health_check",
    "validate_sheet_config",
    "initialize_sheets",
    "CACHE_REFRESH_SECONDS",
    "SHEETS_AVAILABLE",
]