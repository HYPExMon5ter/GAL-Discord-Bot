# gal_discord_bot/views.py

import discord
import time
from gal_discord_bot.config import (
    embed_from_cfg, EMBEDS_CFG,
    CHECK_IN_CHANNEL, REGISTRATION_CHANNEL,
    REGISTERED_ROLE, CHECKED_IN_ROLE, ANGEL_ROLE,
    ALLOWED_ROLES, get_cmd_id
)
from gal_discord_bot.sheets import (
    sheet_cache, cache_lock,
    mark_checked_in_async, unmark_checked_in_async,
    reset_registered_roles_and_sheet, reset_checked_in_roles_and_sheet,
    retry_until_successful, get_sheet_for_guild, refresh_sheet_cache,
    unregister_user
)
from gal_discord_bot.persistence import (
    get_persisted_msg, set_persisted_msg,
    get_event_mode_for_guild,
)
from gal_discord_bot.logging_utils import log_error

last_registration_open = {}
last_checkin_open = {}

def has_allowed_role(member):
    return any(role.name in ALLOWED_ROLES for role in getattr(member, "roles", []))

def has_allowed_role_from_interaction(interaction: discord.Interaction):
    member = getattr(interaction, "user", getattr(interaction, "author", None))
    return hasattr(member, "roles") and has_allowed_role(member)

async def create_persisted_embed(guild, channel, embed, view, persist_key, pin=True, announce_pin=True):
    """
    Sends an embed in `channel`, persists (channel_id, msg_id) for `persist_key` (e.g. "registration"),
    pins the message, and deletes a confirmation pin message if announce_pin is True.
    """
    msg = await channel.send(embed=embed, view=view)
    set_persisted_msg(guild.id, persist_key, channel.id, msg.id)
    if pin:
        await msg.pin()
        if announce_pin:
            pin_confirm = await channel.send("Embed pinned.")
            try:
                await pin_confirm.delete()
            except Exception:
                pass
    return msg


class CheckInButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="Check in!",
            style=discord.ButtonStyle.green,
            emoji="✅",
            custom_id="checkin_btn"
        )

    async def callback(self, interaction: discord.Interaction):
        check_in_channel = interaction.channel
        registered_role = discord.utils.get(interaction.guild.roles, name=REGISTERED_ROLE)
        if not registered_role:
            embed = embed_from_cfg("error")
            embed.description = f"Role '{REGISTERED_ROLE}' not found."
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        overwrites = check_in_channel.overwrites_for(registered_role)
        if not overwrites.view_channel:
            embed = embed_from_cfg("checkin_disabled")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        member = interaction.user
        discord_tag = str(member)
        async with cache_lock:
            user_tuple = sheet_cache["users"].get(discord_tag)
            checked_in_flag = user_tuple[3] if user_tuple else "FALSE"
        if not user_tuple:
            embed = embed_from_cfg("checkin_requires_registration")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        role = discord.utils.get(interaction.guild.roles, name=CHECKED_IN_ROLE)
        if not role:
            embed = embed_from_cfg("error")
            embed.description = f"Role '{CHECKED_IN_ROLE}' not found."
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        try:
            if str(checked_in_flag).strip().upper() == "TRUE":
                await member.remove_roles(role)
                try:
                    await unmark_checked_in_async(discord_tag, guild_id=str(interaction.guild.id))
                except Exception as e:
                    await log_error(interaction.client, interaction.guild, f"Uncheck-in button error: {e}")
                embed = embed_from_cfg("checked_out")
                await interaction.followup.send(embed=embed, ephemeral=True)
            else:
                await member.add_roles(role)
                try:
                    await mark_checked_in_async(discord_tag, guild_id=str(interaction.guild.id))
                except Exception as e:
                    await log_error(interaction.client, interaction.guild, f"Check-in button error: {e}")
                embed = embed_from_cfg("checked_in")
                await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            await log_error(interaction.client, interaction.guild, f"Check-in button error: {e}")
            if not interaction.response.is_done():
                error_embed = embed_from_cfg("error")
                error_embed.description = f"An error occurred during check-in: {e}"
                await interaction.followup.send(embed=error_embed, ephemeral=True)

class ResetCheckInsButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="Reset",
            style=discord.ButtonStyle.danger,
            emoji="🔄",
            custom_id="reset_checkin_btn"
        )

    async def callback(self, interaction: discord.Interaction):
        if not has_allowed_role(interaction.user):
            embed = embed_from_cfg("permission_denied")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        checked_in_role = discord.utils.get(interaction.guild.roles, name=CHECKED_IN_ROLE)
        cleared_count = 0
        if checked_in_role:
            for member in interaction.guild.members:
                if checked_in_role in member.roles:
                    cleared_count += 1
        embed_start = embed_from_cfg("resetting", count=cleared_count, role="checked-in")
        await interaction.followup.send(embed=embed_start, ephemeral=True)
        start_time = time.perf_counter()
        check_in_channel = discord.utils.get(interaction.guild.text_channels, name=CHECK_IN_CHANNEL)
        actual_cleared = await reset_checked_in_roles_and_sheet(interaction.guild, check_in_channel)
        end_time = time.perf_counter()
        elapsed = end_time - start_time
        embed_done = embed_from_cfg("reset_complete", role="Check-in", count=actual_cleared, elapsed=elapsed)
        await update_live_embeds(interaction.guild)
        await interaction.followup.send(embed=embed_done, ephemeral=True)
        await refresh_sheet_cache(bot=interaction.client)

class ToggleCheckInButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="Toggle Check-In Channel",
            style=discord.ButtonStyle.primary,
            emoji="🔓",
            custom_id="toggle_checkin_btn"
        )

    async def callback(self, interaction: discord.Interaction):
        if not has_allowed_role(interaction.user):
            embed = embed_from_cfg("permission_denied")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        guild = interaction.guild
        channel = interaction.channel
        registered_role = discord.utils.get(guild.roles, name=REGISTERED_ROLE)
        overwrites = channel.overwrites_for(registered_role)
        is_open = bool(overwrites.view_channel)
        overwrites.view_channel = not is_open
        await channel.set_permissions(registered_role, overwrite=overwrites)
        embed = embed_from_cfg("checkin_channel_toggled", visible=not is_open)

        # Fetch (channel_id, msg_id) and update check-in embed by msg_id
        _, checkin_msg_id = get_persisted_msg(guild.id, "checkin")
        if checkin_msg_id:
            await update_checkin_embed(channel, checkin_msg_id, guild)

        await interaction.response.send_message(embed=embed, ephemeral=True)

class UnregisterButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="Unregister",
            style=discord.ButtonStyle.secondary,
            emoji="🚫",
            custom_id="unregister_btn"
        )

    async def callback(self, interaction: discord.Interaction):
        member = interaction.user
        guild = interaction.guild
        discord_tag = str(member)
        guild_id = str(guild.id)
        mode = get_event_mode_for_guild(guild_id)
        async with cache_lock:
            user_tuple = sheet_cache["users"].get(discord_tag)
        reg_channel = discord.utils.get(guild.text_channels, name=REGISTRATION_CHANNEL)
        registered_role = discord.utils.get(guild.roles, name=REGISTERED_ROLE)
        is_registered = False
        if user_tuple:
            reg_val = user_tuple[2]
            is_registered = (
                (isinstance(reg_val, str) and reg_val.upper() == "TRUE") or reg_val is True
            )
        if not is_registered:
            embed = embed_from_cfg("unregister_not_registered")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        if registered_role and registered_role in member.roles:
            await member.remove_roles(registered_role)
        success = await unregister_user(discord_tag, guild_id=guild_id)
        if reg_channel:
            async for msg in reg_channel.history(limit=200):
                if msg.author.id == member.id and not msg.author.bot:
                    try:
                        await msg.delete()
                    except Exception:
                        pass
        embed = embed_from_cfg("unregister_success") if success else embed_from_cfg("error")
        await interaction.response.send_message(embed=embed, ephemeral=True)

class ToggleRegistrationButton(discord.ui.Button):
    def __init__(self, embed_message_id):
        super().__init__(
            label="Toggle Registration Channel",
            style=discord.ButtonStyle.primary,
            emoji="🔓",
            custom_id="toggle_registration_btn"
        )
        self.embed_message_id = embed_message_id

    async def callback(self, interaction: discord.Interaction):
        if not has_allowed_role_from_interaction(interaction):
            embed = embed_from_cfg("permission_denied")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        guild = interaction.guild
        channel = interaction.channel
        angel_role = discord.utils.get(guild.roles, name=ANGEL_ROLE)
        overwrites = channel.overwrites_for(angel_role)
        is_open = bool(overwrites.view_channel)
        overwrites.view_channel = not is_open
        await channel.set_permissions(angel_role, overwrite=overwrites)
        embed = embed_from_cfg("registration_channel_toggled", visible=not is_open)
        await update_registration_embed(channel, self.embed_message_id, guild)
        await interaction.response.send_message(embed=embed, ephemeral=True)

class ResetRegistrationButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="Reset",
            style=discord.ButtonStyle.danger,
            emoji="🔄",
            custom_id="reset_registration_btn"
        )

    async def callback(self, interaction: discord.Interaction):
        if not has_allowed_role_from_interaction(interaction):
            embed = embed_from_cfg("permission_denied")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        guild = interaction.guild
        reg_channel = interaction.channel
        guild_id = str(guild.id)
        mode = get_event_mode_for_guild(guild_id)

        cleared = await reset_registered_roles_and_sheet(guild, reg_channel)

        reg_channel_id, main_embed_msg_id = get_persisted_msg(guild_id, "registration")
        messages = [m async for m in reg_channel.history(limit=50)]
        for msg in messages:
            if msg.id == main_embed_msg_id:
                continue
            if (
                msg.author.bot
                and msg.embeds
                and any(
                    e.title and e.title.lower() == EMBEDS_CFG.get("register_public", {}).get("title", "").lower()
                    for e in msg.embeds
                )
            ):
                try:
                    await msg.delete()
                except Exception:
                    pass

        embed = embed_from_cfg("reset_complete", role="registered", count=cleared, elapsed=0)
        await interaction.response.send_message(embed=embed, ephemeral=True)
        await refresh_sheet_cache(bot=interaction.client)

class CheckInView(discord.ui.View):
    def __init__(self, guild):
        super().__init__(timeout=None)
        self.guild = guild
        checkin_channel = discord.utils.get(guild.text_channels, name=CHECK_IN_CHANNEL)
        registered_role = discord.utils.get(guild.roles, name=REGISTERED_ROLE)
        is_open = False
        if checkin_channel and registered_role:
            overwrites = checkin_channel.overwrites_for(registered_role)
            is_open = bool(overwrites.view_channel)
        if is_open:
            self.add_item(CheckInButton())
            self.add_item(ToggleCheckInButton())
        else:
            self.add_item(ToggleCheckInButton())
            self.add_item(ResetCheckInsButton())

class RegistrationView(discord.ui.View):
    def __init__(self, embed_message_id, guild):
        super().__init__(timeout=None)
        self.embed_message_id = embed_message_id
        self.guild = guild
        reg_channel = discord.utils.get(guild.text_channels, name=REGISTRATION_CHANNEL)
        angel_role = discord.utils.get(guild.roles, name=ANGEL_ROLE)
        is_open = False
        if reg_channel and angel_role:
            overwrites = reg_channel.overwrites_for(angel_role)
            is_open = bool(overwrites.view_channel)
        if is_open:
            self.add_item(UnregisterButton())
            self.add_item(ToggleRegistrationButton(embed_message_id))
        else:
            self.add_item(ToggleRegistrationButton(embed_message_id))
            self.add_item(ResetRegistrationButton())

class PersistentReminderButton(discord.ui.Button):
    def __init__(self, guild_id: int):
        super().__init__(
            label="DM Reminder to All Unchecked",
            style=discord.ButtonStyle.primary,
            emoji="✉️",
            custom_id=f"reminder_dm_all_{guild_id}"  # ensures uniqueness per guild if needed
        )
        self.guild_id = guild_id

    async def callback(self, interaction: discord.Interaction):
        if not has_allowed_role(interaction.user):
            embed = embed_from_cfg("permission_denied")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        reminder_cfg = EMBEDS_CFG.get("reminder_dm", {})
        reminder_msg = reminder_cfg.get("description", "Reminder: Please check in for the tournament!")
        dmmed = []
        guild = interaction.guild

        async with cache_lock:
            for discord_tag, user_tuple in sheet_cache["users"].items():
                registered_flag = user_tuple[2]
                checked_in_flag = user_tuple[3]
                if str(registered_flag).strip().upper() == "TRUE" and str(checked_in_flag).strip().upper() != "TRUE":
                    member = None
                    if "#" in discord_tag:
                        name, discrim = discord_tag.rsplit("#", 1)
                        member = discord.utils.get(guild.members, name=name, discriminator=discrim)
                    if not member:
                        for m in guild.members:
                            if m.display_name == discord_tag or m.name == discord_tag:
                                member = m
                                break
                    if member:
                        try:
                            await member.send(reminder_msg)
                            dmmed.append(f"{member} (`{discord_tag}`)")
                        except Exception:
                            pass

        num_dmmed = len(dmmed)
        users_list = "\n".join(dmmed) if dmmed else "No users could be DM'd (not found or DMs disabled)."
        embed = embed_from_cfg("reminder_public", count=num_dmmed, users=users_list)
        await interaction.response.send_message(embed=embed, ephemeral=True)

class PersistentRegisteredListView(discord.ui.View):
    def __init__(self, guild):
        super().__init__(timeout=None)
        self.add_item(PersistentReminderButton(guild.id))

async def update_live_embeds(guild):
    # Registration Embed
    reg_channel_id, reg_msg_id = get_persisted_msg(guild.id, "registration")
    reg_channel = guild.get_channel(reg_channel_id) if reg_channel_id else None
    if reg_channel and reg_msg_id:
        try:
            await update_registration_embed(reg_channel, reg_msg_id, guild)
        except Exception as e:
            await log_error(None, guild, f"Failed to update registration embed: {e}")

    # Check-in Embed
    checkin_channel_id, checkin_msg_id = get_persisted_msg(guild.id, "checkin")
    checkin_channel = guild.get_channel(checkin_channel_id) if checkin_channel_id else None
    if checkin_channel and checkin_msg_id:
        try:
            await update_checkin_embed(checkin_channel, checkin_msg_id, guild)
        except Exception as e:
            await log_error(None, guild, f"Failed to update check-in embed: {e}")

async def update_registration_embed(channel, msg_id, guild):
    reg_channel = discord.utils.get(guild.text_channels, name=REGISTRATION_CHANNEL)
    angel_role = discord.utils.get(guild.roles, name=ANGEL_ROLE)
    is_open = False
    if reg_channel and angel_role:
        overwrites = reg_channel.overwrites_for(angel_role)
        is_open = bool(overwrites.view_channel)

    mode = get_event_mode_for_guild(str(guild.id))
    register_cmd_id = get_cmd_id("register")
    if is_open:
        team_required = " and your team name!" if mode == "doubleup" else "!"
        embed = embed_from_cfg(
            "registration",
            register_cmd_id=register_cmd_id,
            team_required=team_required
        )
    else:
        embed = embed_from_cfg("registration_closed")

    reg_msg = await channel.fetch_message(msg_id)
    from gal_discord_bot.views import RegistrationView
    await reg_msg.edit(embed=embed, view=RegistrationView(msg_id, guild))

    # Optionally: ping role on opening
    from gal_discord_bot.views import last_registration_open
    prev_state = last_registration_open.get(guild.id)
    if prev_state is not None and not prev_state and is_open:
        if angel_role:
            ping_msg = await channel.send(content=angel_role.mention)
            try:
                await ping_msg.delete()
            except Exception:
                pass
    last_registration_open[guild.id] = is_open

async def update_checkin_embed(channel, msg_id, guild):
    checkin_channel = discord.utils.get(guild.text_channels, name=CHECK_IN_CHANNEL)
    registered_role = discord.utils.get(guild.roles, name=REGISTERED_ROLE)
    is_open = False
    if checkin_channel and registered_role:
        overwrites = checkin_channel.overwrites_for(registered_role)
        is_open = bool(overwrites.view_channel)
    if is_open:
        embed = embed_from_cfg("checkin")
    else:
        embed = embed_from_cfg("checkin_closed")
    checkin_msg = await channel.fetch_message(msg_id)
    await checkin_msg.edit(embed=embed, view=CheckInView(guild))
    prev_state = last_checkin_open.get(guild.id)
    if prev_state is not None and not prev_state and is_open:
        reg_role = discord.utils.get(guild.roles, name=REGISTERED_ROLE)
        if reg_role:
            ping_msg = await channel.send(content=reg_role.mention)
            try:
                await ping_msg.delete()
            except Exception:
                pass
    last_checkin_open[guild.id] = is_open