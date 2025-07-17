# gal_discord_bot/utils.py

from datetime import datetime
from zoneinfo import ZoneInfo

import discord

from gal_discord_bot.config import ALLOWED_ROLES, embed_from_cfg
from gal_discord_bot.persistence import get_persisted_msg


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