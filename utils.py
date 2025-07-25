# gal_discord_bot/utils.py
import urllib
from datetime import datetime
from zoneinfo import ZoneInfo

import aiohttp
import discord

from config import ALLOWED_ROLES, embed_from_cfg, get_sheet_settings, REGISTERED_ROLE, CHECKED_IN_ROLE
from persistence import get_persisted_msg, get_event_mode_for_guild
from sheets import sheet_cache, get_sheet_for_guild, retry_until_successful



def has_allowed_role(member: discord.Member) -> bool:
    """Check if a member has any of the staff roles."""
    return any(role.name in ALLOWED_ROLES for role in getattr(member, "roles", []))

def has_allowed_role_from_interaction(interaction: discord.Interaction) -> bool:
    """Check interaction.user’s roles for permission."""
    member = getattr(interaction, "user", getattr(interaction, "author", None))
    return hasattr(member, "roles") and has_allowed_role(member)

async def toggle_persisted_channel(
    interaction: discord.Interaction,
    persist_key: str,
    channel_name: str,
    role_name: str,
    ping_role: bool = True,
):
    """
    Universal “open/close channel + update embed” helper.
    """
    # ─── Lazy imports to break circularity ───────────────────────────
    from events import schedule_channel_open
    from views import (
        create_persisted_embed,
        RegistrationView,
        CheckInView,
        update_registration_embed,
        update_checkin_embed,
    )

    guild = interaction.guild
    channel = discord.utils.get(guild.text_channels, name=channel_name)
    role    = discord.utils.get(guild.roles,        name=role_name)
    if not channel or not role:
        await interaction.response.send_message(
            f"Could not find channel `{channel_name}` or role `{role_name}`.",
            ephemeral=True
        )
        return

    # flip visibility
    overwrites = channel.overwrites_for(role)
    was_open    = bool(overwrites.view_channel)
    new_open    = not was_open

    if new_open:
        await schedule_channel_open(
            interaction.client,
            guild,
            channel_name,
            role_name,
            datetime.now(ZoneInfo("UTC")),
            ping_role=ping_role
        )
    else:
        overwrites.view_channel = False
        await channel.set_permissions(role, overwrite=overwrites)

    # persisted‐embed management
    _, msg_id = get_persisted_msg(guild.id, persist_key)
    if new_open:
        if not msg_id:
            embed = embed_from_cfg(f"{persist_key}_closed")
            view  = (
                RegistrationView(None, guild)
                if persist_key == "registration"
                else CheckInView(guild)
            )
            await create_persisted_embed(guild, channel, embed, view, persist_key)
        else:
            if persist_key == "registration":
                await update_registration_embed(channel, msg_id, guild)
            else:
                await update_checkin_embed(channel, msg_id, guild)
    else:
        if msg_id:
            if persist_key == "registration":
                await update_registration_embed(channel, msg_id, guild)
            else:
                await update_checkin_embed(channel, msg_id, guild)

    # feedback to user
    feedback = embed_from_cfg(f"{persist_key}_channel_toggled", visible=new_open)
    await interaction.response.send_message(embed=feedback, ephemeral=True)

    # ─── Refresh any existing reminder DMs ─────────────────────────
    await update_dm_action_views(interaction.guild)

def resolve_member(guild: discord.Guild, discord_tag: str) -> discord.Member | None:
    """Find a Member in this guild by tag or name/display_name."""
    if "#" in discord_tag:
        name, discrim = discord_tag.rsplit("#", 1)
        m = discord.utils.get(guild.members, name=name, discriminator=discrim)
        if m:
            return m
    for m in guild.members:
        if m.name == discord_tag or m.display_name == discord_tag:
            return m
    return None

async def send_reminder_dms(
    client: discord.Client,
    guild: discord.Guild,
    dm_embed: discord.Embed,
    view_cls: type[discord.ui.View]
) -> list[str]:
    """
    DM every registered-but-not-checked-in user in `guild` with `dm_embed` and a view from `view_cls`,
    returning a list of f"{member} (`{tag}`)" for each DM successfully sent.
    """
    from sheets import sheet_cache, cache_lock
    dmmed: list[str] = []
    async with cache_lock:
        for discord_tag, user_tuple in sheet_cache["users"].items():
            is_reg   = str(user_tuple[2]).upper() == "TRUE"
            is_ci    = str(user_tuple[3]).upper() == "TRUE"
            if not (is_reg and not is_ci):
                continue

            member = resolve_member(guild, discord_tag)
            if not member:
                continue

            try:
                view = view_cls(guild, member)
                await member.send(embed=dm_embed, view=view)
                dmmed.append(f"{member} (`{discord_tag}`)")
            except:
                pass

    return dmmed

async def toggle_checkin_for_member(
    interaction: discord.Interaction,
    checkin_fn,
    success_key: str,
):
    print(f"[toggle_checkin] start: fn={checkin_fn.__name__} user={interaction.user} guild={interaction.guild.id}")
    await interaction.response.defer(ephemeral=True)

    guild  = interaction.guild
    member = interaction.user

    # 1) Registered?
    reg_role = discord.utils.get(guild.roles, name=REGISTERED_ROLE)
    if reg_role not in member.roles:
        print("[toggle_checkin] user not registered")
        return await interaction.followup.send(
            embed=embed_from_cfg("checkin_requires_registration"),
            ephemeral=True
        )

    # 2) Sheet + cache
    discord_tag = str(member)
    ok = await checkin_fn(discord_tag, guild_id=str(guild.id))
    print(f"[toggle_checkin] sheet fn returned ok={ok}")

    # 3) Role assign/unassign
    ci_role = discord.utils.get(guild.roles, name=CHECKED_IN_ROLE)
    if ok and ci_role:
        if success_key == "checked_in":
            await member.add_roles(ci_role)
            print("[toggle_checkin] added check-in role")
        else:
            await member.remove_roles(ci_role)
            print("[toggle_checkin] removed check-in role")

    # 4) Feedback
    resp = embed_from_cfg(success_key if ok else "error")
    await interaction.followup.send(embed=resp, ephemeral=True)

    # 5) Refresh embed
    chan_id, msg_id = get_persisted_msg(guild.id, "checkin")
    print(f"[toggle_checkin] persisted checkin msg: chan_id={chan_id} msg_id={msg_id}")
    if chan_id and msg_id:
        ch = guild.get_channel(chan_id)
        print("[toggle_checkin] calling update_checkin_embed")
        from views import update_checkin_embed
        await update_checkin_embed(ch, msg_id, guild)

async def update_dm_action_views(guild: discord.Guild):
    """
    Iterate all users in the cache, find any reminder DM,
    and re-edit it with a fresh DMActionView so buttons reflect current open/closed state.
    """
    # local import breaks circularity
    from sheets import sheet_cache, cache_lock
    from views import DMActionView
    rem_embed = embed_from_cfg("reminder_dm")
    rem_title = rem_embed.title

    async with cache_lock:
        tags = list(sheet_cache["users"].keys())

    for discord_tag in tags:
        member = resolve_member(guild, discord_tag)
        if not member:
            continue
        try:
            dm = await member.create_dm()
            async for msg in dm.history(limit=50):
                if msg.author == guild.client.user and msg.embeds:
                    e = msg.embeds[0]
                    if e.title == rem_title:
                        await msg.edit(view=DMActionView(guild, member))
        except Exception:
            # ignore messages we can’t access
            pass

# Rank utils

import re
from typing import List

# Ordered lowest → highest
CANONICAL_RANKS: List[str] = [
    "Bronze 4", "Bronze 3", "Bronze 2", "Bronze 1",
    "Silver 4", "Silver 3", "Silver 2", "Silver 1",
    "Gold 4", "Gold 3", "Gold 2", "Gold 1",
    "Platinum 4", "Platinum 3", "Platinum 2", "Platinum 1",
    "Emerald 4", "Emerald 3", "Emerald 2", "Emerald 1",
    "Diamond 4", "Diamond 3", "Diamond 2", "Diamond 1",
    "Masters", "Masters 100", "Masters 200",
    "Grandmaster", "Grandmaster 500", "Grandmaster 600", "Grandmaster 700",
    "Challenger 800", "Challenger 900", "Challenger 1000",
]

# Tier name → base index
_TIER_INDEX = {
    "bronze": 0, "silver": 1, "gold": 2, "platinum": 3,
    "emerald": 4, "diamond": 5, "masters": 6,
    "grandmaster": 7, "challenger": 8,
}

# Roman numerals
_ROMAN_MAP = {"I": 1, "II": 2, "III": 3, "IV": 4}

def _roman_to_int(roman: str) -> int:
    return _ROMAN_MAP.get(roman.upper(), 0)


def _parse_rank_value(rank_str: str) -> float:
    """
    Convert rank string to numeric score for comparison.
    """
    s = rank_str.strip()
    m_t = re.match(r"^(Bronze|Silver|Gold|Platinum|Emerald|Diamond|Masters|Grandmaster|Challenger)", s, re.IGNORECASE)
    if not m_t:
        return 0.0
    tier = m_t.group(1).lower()
    tier = "masters" if tier == "master" else tier
    idx = _TIER_INDEX.get(tier, 0)
    m_lp = re.search(r"(\d+)\s*LP", s)
    lp = int(m_lp.group(1)) if m_lp else 0
    if tier in ("bronze","silver","gold","platinum","emerald","diamond"):
        m_div = re.match(rf"^{tier}\s+([IV]+)", s, re.IGNORECASE)
        div = _roman_to_int(m_div.group(1)) if m_div else 4
        div_idx = 4 - div
        return idx * 4 + div_idx + lp/100.0
    return idx * 4 + lp/100.0


def get_closest_rank(rank_str: str) -> str:
    """
    Return the canonical rank closest to `rank_str`.
    """
    score = _parse_rank_value(rank_str)
    scores = [_parse_rank_value(r) for r in CANONICAL_RANKS]
    best = min(range(len(scores)), key=lambda i: abs(scores[i]-score))
    return CANONICAL_RANKS[best]

async def hyperlink_lolchess_profile(discord_tag: str, guild_id: str) -> None:
    """
    Link the main IGN (and alts) to lolchess.gg via =HYPERLINK(...)
    whenever a user registers. Always re-writes the formula.
    """
    # 1) Lookup row & IGNs in cache
    tup = sheet_cache["users"].get(discord_tag)
    if not tup:
        return
    row, ign, _, _, _, alt = tup

    settings = get_sheet_settings(get_event_mode_for_guild(guild_id))
    sheet    = get_sheet_for_guild(guild_id, "GAL Database")

    async with aiohttp.ClientSession() as session:
        # Main IGN
        slug = urllib.parse.quote(ign.replace("#", "-"), safe="-")
        url  = f"https://lolchess.gg/profile/na/{slug}/"
        async with session.get(url, allow_redirects=True) as resp:
            if resp.url.path.startswith("/search"):
                return
        formula = f'=HYPERLINK("{url}","{ign}")'
        await retry_until_successful(
            sheet.update_acell,
            f"{settings['ign_col']}{row}",
            formula
        )

        # Alt IGNs
        if alt:
            parts = [p.strip() for p in re.split(r"[,\\s]+", alt) if p.strip()]
            links = []
            for nm in parts:
                slug = urllib.parse.quote(nm.replace("#", "-"), safe="-")
                url  = f"https://lolchess.gg/profile/na/{slug}/"
                async with session.get(url, allow_redirects=True) as r:
                    if r.url.path.startswith("/search"):
                        continue
                links.append(f'HYPERLINK("{url}","{nm}")')
            if links:
                expr = "=" + ' & ", " & '.join(links)
                await retry_until_successful(
                    sheet.update_acell,
                    f"{settings['alt_ign_col']}{row}",
                    expr
                )