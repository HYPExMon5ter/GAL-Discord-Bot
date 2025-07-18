# gal_discord_bot/utils.py
from datetime import datetime
from zoneinfo import ZoneInfo

import discord

from gal_discord_bot.config import ALLOWED_ROLES, embed_from_cfg, REGISTERED_ROLE
from gal_discord_bot.persistence import get_persisted_msg
from gal_discord_bot.sheets import sheet_cache, cache_lock


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
    Defers importing events/views until runtime to avoid circular imports.
    """
    # ─── Lazy imports to break circularity ───────────────────────────
    from gal_discord_bot.events import schedule_channel_open
    from gal_discord_bot.views import (
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
        # schedule the open (this also updates embeds + pings)
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
            # first‐time create the embed
            embed = embed_from_cfg(f"{persist_key}_closed")
            view  = (
                RegistrationView(None, guild)
                if persist_key == "registration"
                else CheckInView(guild)
            )
            await create_persisted_embed(guild, channel, embed, view, persist_key)
        else:
            # update to open view
            if persist_key == "registration":
                await update_registration_embed(channel, msg_id, guild)
            else:
                await update_checkin_embed(channel, msg_id, guild)
    else:
        # update to closed view
        if msg_id:
            if persist_key == "registration":
                await update_registration_embed(channel, msg_id, guild)
            else:
                await update_checkin_embed(channel, msg_id, guild)

    # feedback to user
    feedback = embed_from_cfg(f"{persist_key}_channel_toggled", visible=new_open)
    await interaction.response.send_message(embed=feedback, ephemeral=True)


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
    *,
    guild: discord.Guild = None,
    member: discord.Member = None
):
    """
    Toggle a user’s checked-in state via `checkin_fn`, update cache,
    add/remove the CHECKED_IN_ROLE, send feedback, and refresh the embed.
    """
    from gal_discord_bot.views import update_checkin_embed  # lazy to avoid circular import
    from gal_discord_bot.config import REGISTERED_ROLE, CHECKED_IN_ROLE

    # 1) Defer + resolve context
    await interaction.response.defer(ephemeral=True)
    guild = guild or interaction.guild
    member = member or interaction.user
    if not guild or not member:
        return

    # 2) Must be registered
    reg_role = discord.utils.get(guild.roles, name=REGISTERED_ROLE)
    if reg_role not in member.roles:
        return await interaction.followup.send(
            embed=embed_from_cfg("checkin_requires_registration"),
            ephemeral=True
        )

    # 3) Sheet write & cache update
    discord_tag = str(member)
    ok = await checkin_fn(discord_tag, guild_id=str(guild.id))

    # 4) Assign/unassign the actual Discord role
    ci_role = discord.utils.get(guild.roles, name=CHECKED_IN_ROLE)
    if ok and ci_role:
        if success_key == "checked_in":
            await member.add_roles(ci_role)
        else:  # "checked_out"
            await member.remove_roles(ci_role)

    # 5) Feedback embed
    resp = embed_from_cfg(success_key) if ok else embed_from_cfg("error")
    await interaction.followup.send(embed=resp, ephemeral=True)

    # 6) Refresh the shared check-in embed in the channel
    chan_id, msg_id = get_persisted_msg(guild.id, "checkin")
    if chan_id and msg_id:
        ch = guild.get_channel(chan_id)
        await update_checkin_embed(ch, msg_id, guild)