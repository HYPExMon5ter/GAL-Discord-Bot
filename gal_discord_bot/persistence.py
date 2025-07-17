# gal_discord_bot/persistence.py

import json
import os

from gal_discord_bot.config import DATABASE_URL

PERSIST_FILE = os.path.join(os.path.dirname(__file__), "persisted_views.json")

if DATABASE_URL:
    import psycopg2
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    conn = psycopg2.connect(DATABASE_URL, sslmode="require")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS persisted_views (
            key TEXT PRIMARY KEY,
            data JSONB
        );
    """)
    conn.commit()

    def load_persisted():
        cursor.execute("SELECT data FROM persisted_views WHERE key = %s", ("default",))
        row = cursor.fetchone()
        return row[0] if row else {}

    def save_persisted(data):
        cursor.execute(
            "INSERT INTO persisted_views (key, data) VALUES (%s, %s) "
            "ON CONFLICT (key) DO UPDATE SET data = EXCLUDED.data",
            ("default", json.dumps(data))
        )
        conn.commit()
else:
    # Local fallback: JSON file
    def load_persisted():
        try:
            with open(PERSIST_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return {}

    def save_persisted(data):
        with open(PERSIST_FILE, "w") as f:
            json.dump(data, f, indent=2)

persisted = load_persisted()

def set_persisted_msg(guild_id, key, channel_id, msg_id):
    """
    Store [channel_id, msg_id] for the given guild/key.
    """
    gid = str(guild_id)
    if gid not in persisted:
        persisted[gid] = {}
    persisted[gid][key] = [channel_id, msg_id]
    save_persisted(persisted)

def get_persisted_msg(guild_id, key):
    """
    Return (channel_id, msg_id) tuple, or (None, None) if missing.
    Legacy support: if int found, return (None, msg_id)
    """
    value = persisted.get(str(guild_id), {}).get(key)
    if isinstance(value, list) and len(value) == 2:
        return value[0], value[1]
    elif isinstance(value, int):
        return None, value
    return None, None

def get_event_mode_for_guild(guild_id):
    gid = str(guild_id)
    return persisted.get(gid, {}).get("event_mode", "normal")

def set_event_mode_for_guild(guild_id, mode):
    gid = str(guild_id)
    if gid not in persisted:
        persisted[gid] = {}
    persisted[gid]["event_mode"] = mode
    save_persisted(persisted)

def get_schedule(guild_id, key):
    data = persisted.get(str(guild_id), {})
    return data.get(f"{key}_schedule")

def set_schedule(guild_id, key, dtstr):
    gid = str(guild_id)
    if gid not in persisted:
        persisted[gid] = {}
    persisted[gid][f"{key}_schedule"] = dtstr
    save_persisted(persisted)

# --- Migration helper (one-time, optional) ---
def migrate_legacy():
    changed = False
    for gid, data in persisted.items():
        for key in ["registration", "checkin"]:
            val = data.get(key)
            if isinstance(val, int):
                data[key] = [None, val]
                changed = True
    if changed:
        save_persisted(persisted)
        print("Migrated legacy persisted messages to [channel_id, msg_id] format.")