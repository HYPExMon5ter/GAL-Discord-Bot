# gal_discord_bot/views.py

import time

import discord
from rapidfuzz import process, fuzz

from gal_discord_bot.config import (
    embed_from_cfg, CHECK_IN_CHANNEL, REGISTRATION_CHANNEL,
    REGISTERED_ROLE, CHECKED_IN_ROLE, ANGEL_ROLE,
    get_cmd_id
)
from gal_discord_bot.logging_utils import log_error
from gal_discord_bot.persistence import (
    get_persisted_msg, set_persisted_msg,
    get_event_mode_for_guild,
)
from gal_discord_bot.sheets import (
    sheet_cache, cache_lock,
    mark_checked_in_async, unmark_checked_in_async,
    reset_registered_roles_and_sheet, reset_checked_in_roles_and_sheet,
    retry_until_successful, get_sheet_for_guild, refresh_sheet_cache,
    find_or_register_user
)
from gal_discord_bot.utils import (
    has_allowed_role,
    has_allowed_role_from_interaction,
    toggle_persisted_channel,
)


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

async def complete_registration(interaction, ign, pronouns, team_name, reg_modal):
    guild = interaction.guild
    user = interaction.user
    guild_id = str(guild.id)
    discord_tag = str(user)
    mode = get_event_mode_for_guild(guild_id)
    reg_channel = discord.utils.get(guild.text_channels, name=REGISTRATION_CHANNEL)
    reg_role = discord.utils.get(guild.roles, name=REGISTERED_ROLE)

    try:
        if mode == "doubleup":
            row_num = await find_or_register_user(discord_tag, ign, guild_id=guild_id, team_name=team_name)
            sheet = get_sheet_for_guild(guild_id, "GAL Database")
            await retry_until_successful(sheet.update_acell, f"C{row_num}", pronouns)
        else:
            row_num = await find_or_register_user(discord_tag, ign, guild_id=guild_id)
            sheet = get_sheet_for_guild(guild_id, "GAL Database")
            await retry_until_successful(sheet.update_acell, f"C{row_num}", pronouns)

        # Add role
        if reg_role and reg_role not in user.roles:
            await user.add_roles(reg_role)
        await update_live_embeds(guild)

        # Delete previous "New Registration" embeds for this user (except main view)
        reg_channel_id, main_embed_msg_id = get_persisted_msg(guild.id, "registration")
        if reg_channel:
            async for msg in reg_channel.history(limit=100):
                if msg.id == main_embed_msg_id:
                    continue
                if (
                    msg.author.bot
                    and msg.embeds
                    and any(
                        e.title and "New Registration" in e.title
                        and (user.mention in e.description or user.display_name in e.description)
                        for e in msg.embeds
                    )
                ):
                    try:
                        await msg.delete()
                    except Exception:
                        pass

        embed = embed_from_cfg(
            "register_success_doubleup" if mode == "doubleup" else "register_success_normal",
            ign=ign,
            team_name=team_name or "",
            name=user.mention
        )
        await interaction.followup.send(embed=embed, ephemeral=False)

    except Exception as e:
        await log_error(interaction.client, interaction.guild, f"[REGISTER-MODAL-ERROR] {e}")

class CheckInButton(discord.ui.Button):
    def __init__(self, *, guild_id: int = None):
        """
        If guild_id is provided, this button is meant for a DM context;
        otherwise it will pull guild from interaction.guild.
        """
        self._guild_id = guild_id

        # Build a stable custom_id
        cid = f"check_in_btn:{guild_id}" if guild_id is not None else "check_in_btn"
        super().__init__(
            label="Check In / Out",
            style=discord.ButtonStyle.success,
            custom_id=cid
        )

    async def callback(self, interaction: discord.Interaction):
        try:
            await interaction.response.defer(ephemeral=True)

            # ── 1) Resolve guild & member ──────────────────────────────
            if interaction.guild:
                guild  = interaction.guild
                member = interaction.user
            else:
                # DM case: pull guild by ID, then fetch the member
                guild = interaction.client.get_guild(self._guild_id)
                if guild is None:
                    return await interaction.followup.send(
                        "❌ Could not find the server for this reminder.",
                        ephemeral=True
                    )
                member = await guild.fetch_member(interaction.user.id)

            discord_tag = str(member)
            gid         = str(guild.id)

            # ── 2) Permission check: must have REGISTERED_ROLE ─────────
            reg_role = discord.utils.get(guild.roles, name=REGISTERED_ROLE)
            if reg_role not in member.roles:
                embed = embed_from_cfg("checkin_requires_registration")
                return await interaction.followup.send(embed=embed, ephemeral=True)

            # ── 3) Read your sheet cache for current status ─────────────
            async with cache_lock:
                user_tuple = sheet_cache["users"].get(discord_tag, ())
            is_checked_in = False
            if len(user_tuple) > 3:
                val = user_tuple[3]
                is_checked_in = (isinstance(val, str) and val.upper()=="TRUE") or (val is True)

            # ── 4) Toggle check-in state ────────────────────────────────
            if is_checked_in:
                ok = await unmark_checked_in_async(discord_tag, guild_id=gid)
                resp = embed_from_cfg("checked_out") if ok else embed_from_cfg("error")
            else:
                ok = await mark_checked_in_async(discord_tag, guild_id=gid)
                resp = embed_from_cfg("checked_in") if ok else embed_from_cfg("error")

            await interaction.followup.send(embed=resp, ephemeral=True)

        except Exception as e:
            # log_error is your own helper
            await log_error(
                interaction.client,
                interaction.guild or interaction.client.get_guild(self._guild_id),
                f"[CHECKIN-BUTTON-ERROR] {e}"
            )

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
        if not has_allowed_role_from_interaction(interaction):
            embed = embed_from_cfg("permission_denied")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        await toggle_persisted_channel(
            interaction,
            persist_key="checkin",
            channel_name=CHECK_IN_CHANNEL,
            role_name=REGISTERED_ROLE,
            ping_role=True,
        )

class RegisterButton(discord.ui.Button):
    def __init__(self, label="Register", custom_id="register_btn", style=discord.ButtonStyle.success):
        super().__init__(label=label, style=style, custom_id=custom_id)

    async def callback(self, interaction: discord.Interaction):
        guild_id = str(interaction.guild.id)
        mode = get_event_mode_for_guild(guild_id)
        user = interaction.user
        discord_tag = str(user)
        # Try to prefill from the cache (if available)
        pronouns = ""
        team_name = ""
        ign = ""
        async with cache_lock:
            user_tuple = sheet_cache["users"].get(discord_tag)
            if user_tuple:
                ign = user_tuple[1]
                team_name = user_tuple[4] if len(user_tuple) > 4 else ""
                # Fetch pronouns from sheet (Col C)
                sheet = get_sheet_for_guild(guild_id, "GAL Database")
                try:
                    pronouns_cell = await retry_until_successful(sheet.acell, f"C{user_tuple[0]}")
                    pronouns = pronouns_cell.value if pronouns_cell and pronouns_cell.value else ""
                except Exception:
                    pronouns = ""

        if mode == "doubleup":
            modal = RegistrationModal(team_field=True, default_ign=ign, default_team=team_name, default_pronouns=pronouns)
        else:
            modal = RegistrationModal(team_field=False, default_ign=ign, default_pronouns=pronouns)
        await interaction.response.send_modal(modal)

class UnregisterButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="Unregister",
            style=discord.ButtonStyle.danger,
            custom_id="unregister_btn"
        )

    async def callback(self, interaction: discord.Interaction):
        try:
            await interaction.response.defer(ephemeral=True)  # "thinking"
            member = interaction.user
            guild = interaction.guild
            discord_tag = str(member)
            guild_id = str(guild.id)
            mode = get_event_mode_for_guild(guild_id)
            async with cache_lock:
                user_tuple = sheet_cache["users"].get(discord_tag)
            reg_channel = discord.utils.get(guild.text_channels, name=REGISTRATION_CHANNEL)
            registered_role = discord.utils.get(guild.roles, name=REGISTERED_ROLE)
            checked_in_role = discord.utils.get(guild.roles, name="Checked In")  # Make sure your checked-in role name matches
            is_registered = False
            is_checked_in = False
            if user_tuple:
                reg_val = user_tuple[2]
                checkin_val = user_tuple[3]
                is_registered = (
                    (isinstance(reg_val, str) and reg_val.upper() == "TRUE") or reg_val is True
                )
                is_checked_in = (
                    (isinstance(checkin_val, str) and checkin_val.upper() == "TRUE") or checkin_val is True
                )
            if not is_registered:
                embed = embed_from_cfg("unregister_not_registered")
                await interaction.followup.send(embed=embed, ephemeral=True)
                return

            # Remove roles
            roles_to_remove = []
            if registered_role and registered_role in member.roles:
                roles_to_remove.append(registered_role)
            if checked_in_role and checked_in_role in member.roles:
                roles_to_remove.append(checked_in_role)
            if roles_to_remove:
                await member.remove_roles(*roles_to_remove)

            # Update both columns in sheet to FALSE
            row_num = user_tuple[0]
            if mode == "doubleup":
                reg_col = "G"
                checkin_col = "H"
            else:
                reg_col = "F"
                checkin_col = "G"
            sheet = get_sheet_for_guild(guild_id, "GAL Database")
            await retry_until_successful(sheet.update_acell, f"{reg_col}{row_num}", "FALSE")
            await retry_until_successful(sheet.update_acell, f"{checkin_col}{row_num}", "FALSE")

            # Update cache directly
            user_tuple = list(user_tuple)
            user_tuple[2] = "FALSE"
            user_tuple[3] = "FALSE"
            sheet_cache["users"][discord_tag] = tuple(user_tuple)

            # Delete all previous "New Registration" embeds for this user
            reg_channel_id, main_embed_msg_id = get_persisted_msg(guild.id, "registration")
            if reg_channel:
                async for msg in reg_channel.history(limit=100):
                    if msg.id == main_embed_msg_id:
                        continue
                    if (
                        msg.author.bot
                        and msg.embeds
                        and any(
                            e.title and "New Registration" in e.title
                            and (member.mention in e.description or member.display_name in e.description)
                            for e in msg.embeds
                        )
                    ):
                        try:
                            await msg.delete()
                        except Exception as e:
                            await log_error(interaction.client, guild, f"Error deleting unregister msg: {e}")

            embed = embed_from_cfg("unregister_success")
            await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            await log_error(interaction.client, interaction.guild, f"[UNREGISTER-BUTTON-ERROR] {e}")

class ToggleRegistrationButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="Toggle Registration Channel",
            style=discord.ButtonStyle.primary,
            emoji="🔓",
            custom_id="toggle_registration_btn"
        )

    async def callback(self, interaction: discord.Interaction):
        if not has_allowed_role_from_interaction(interaction):
            embed = embed_from_cfg("permission_denied")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        await toggle_persisted_channel(
            interaction,
            persist_key="registration",
            channel_name=REGISTRATION_CHANNEL,
            role_name=ANGEL_ROLE,
            ping_role=True,
        )

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
        role = "registered"

        # Show 'resetting' embed (ephemeral)
        resetting_embed = embed_from_cfg(
            "resetting",
            role=role,
            count="...",
            elapsed=0
        )
        await interaction.response.send_message(embed=resetting_embed, ephemeral=True)

        # Actually clear registrations
        t0 = time.time()
        cleared = await reset_registered_roles_and_sheet(guild, reg_channel)
        elapsed = time.time() - t0

        # Delete all bot embed messages in channel except the main registration embed
        reg_channel_id, main_embed_msg_id = get_persisted_msg(guild_id, "registration")
        messages = [m async for m in reg_channel.history(limit=100)]
        for msg in messages:
            if msg.id == main_embed_msg_id:
                continue
            if (
                msg.author.bot
                and msg.embeds
                and any(e.title for e in msg.embeds)
            ):
                try:
                    await msg.delete()
                except Exception:
                    pass

        # Send confirmation embed as a follow-up (ephemeral)
        complete_embed = embed_from_cfg(
            "reset_complete",
            role=role,
            count=cleared,
            elapsed=elapsed
        )
        await interaction.followup.send(embed=complete_embed, ephemeral=True)

        await refresh_sheet_cache(bot=interaction.client)

class PersistentReminderButton(discord.ui.Button):
    def __init__(self, guild_id: int):
        super().__init__(
            label="DM Reminder to Unchecked",
            style=discord.ButtonStyle.primary,
            emoji="✉️",
            custom_id=f"reminder_dm_all_{guild_id}"
        )
        self.guild_id = guild_id

    async def callback(self, interaction: discord.Interaction):
        # Permission guard
        if not interaction.user.guild_permissions.manage_guild:
            embed = embed_from_cfg("permission_denied")
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        # Load the embed once
        dm_embed = embed_from_cfg("reminder_dm")
        dm_view  = discord.ui.View()  # We'll attach the CheckInButton below

        # Send DMs
        dmmed = []
        guild = interaction.client.get_guild(self.guild_id)
        async with cache_lock:
            for discord_tag, user_tuple in sheet_cache["users"].items():
                registered = str(user_tuple[2]).strip().upper() == "TRUE"
                checked_in  = str(user_tuple[3]).strip().upper() == "TRUE"
                if registered and not checked_in:
                    # find the Member object
                    member = None
                    if "#" in discord_tag:
                        name, discrim = discord_tag.rsplit("#", 1)
                        member = discord.utils.get(guild.members, name=name, discriminator=discrim)
                    if not member:
                        for m in guild.members:
                            if m.name == discord_tag or m.display_name == discord_tag:
                                member = m; break

                    if member:
                        try:
                            # attach a CheckInButton that works in DMs
                            view = discord.ui.View(timeout=None)
                            view.add_item(
                                # reuse your existing CheckInButton, passing guild_id so it knows context
                                CheckInButton(guild_id=guild.id)
                            )
                            await member.send(embed=dm_embed, view=view)
                            dmmed.append(f"{member} (`{discord_tag}`)")
                        except:
                            pass

        # Report back in the guild
        count = len(dmmed)
        users_list = "\n".join(dmmed) or "No users could be DM'd."
        public = embed_from_cfg("reminder_public", count=count, users=users_list)
        await interaction.response.send_message(embed=public, ephemeral=False)

class RegistrationModal(discord.ui.Modal):
    def __init__(self, *, team_field=False, default_ign=None, default_team=None, default_pronouns=None, bypass_similarity=False):
        title = "Register for the Event"
        super().__init__(title=title)
        self.bypass_similarity = bypass_similarity
        ign_input = discord.ui.TextInput(
            label="In-Game Name",
            placeholder="Enter your TFT IGN",
            required=True,
            default=default_ign or ""
        )
        self.add_item(ign_input)
        self.ign_input = ign_input

        self.team_input = None
        if team_field:
            team_input = discord.ui.TextInput(
                label="Team Name",
                placeholder="Your Team Name",
                required=True,
                default=default_team or ""
            )
            self.add_item(team_input)
            self.team_input = team_input

        pronouns_input = discord.ui.TextInput(
            label="Pronouns",
            placeholder="e.g. She/Her, He/Him, They/Them",
            required=False,
            default=default_pronouns or ""
        )
        self.add_item(pronouns_input)
        self.pronouns_input = pronouns_input

    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild
        user = interaction.user
        guild_id = str(guild.id)
        discord_tag = str(user)
        mode = get_event_mode_for_guild(guild_id)
        ign = self.ign_input.value
        pronouns = self.pronouns_input.value
        team_value = self.team_input.value if self.team_input else None

        reg_channel = discord.utils.get(guild.text_channels, name=REGISTRATION_CHANNEL)
        angel_role = discord.utils.get(guild.roles, name=ANGEL_ROLE)
        reg_role = discord.utils.get(guild.roles, name=REGISTERED_ROLE)

        if reg_channel and angel_role:
            overwrites = reg_channel.overwrites_for(angel_role)
            if not overwrites.view_channel:
                embed = embed_from_cfg("registration_closed")
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

        await interaction.response.defer(ephemeral=True)  # Show "thinking..."

        try:
            if mode == "doubleup" and not getattr(self, "bypass_similarity", False):
                sheet = get_sheet_for_guild(guild_id, "GAL Database")
                team_col_raw = await retry_until_successful(sheet.col_values, 5)
                user_team_value = team_value.strip().lower()
                team_col = [
                    t.strip().lower() for t in team_col_raw[2:]
                    if t and t.strip() and t.strip().lower() != user_team_value
                ]
                norm_to_original = {t.strip().lower(): t.strip() for t in team_col_raw[2:] if
                                    t and t.strip() and t.strip().lower() != user_team_value}

                result = process.extractOne(
                    user_team_value, team_col, scorer=fuzz.ratio, score_cutoff=75
                )
                suggested_team = norm_to_original[result[0]] if result else None

                if suggested_team:
                    await interaction.followup.send(
                        embed=discord.Embed(
                            title="Similar Team Found",
                            description=f"Did you mean **{suggested_team}**?\n\n"
                                        f"Click **Use Suggested** to use the located team name, or **Keep Mine** to register your entered team name.",
                            color=discord.Color.blurple()
                        ),
                        view=TeamNameChoiceView(self, ign, pronouns, suggested_team, team_value),
                        ephemeral=True
                    )
                    return

            # -- If not similar (or similarity already bypassed), immediately complete registration --
            await complete_registration(interaction, ign, pronouns, team_value, self)

        except Exception as e:
            await log_error(interaction.client, interaction.guild, f"[REGISTER-MODAL-ERROR] {e}")

class TeamNameChoiceView(discord.ui.View):
    def __init__(self, reg_modal, ign, pronouns, suggested_team, user_team):
        super().__init__(timeout=60)
        self.reg_modal = reg_modal
        self.ign = ign
        self.pronouns = pronouns
        self.suggested_team = suggested_team
        self.user_team = user_team

    @discord.ui.button(label="Use Suggested", style=discord.ButtonStyle.success)
    async def use_suggested(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Disable buttons to prevent double clicks
        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(view=self)
        await complete_registration(
            interaction,
            self.ign,
            self.pronouns,
            self.suggested_team,
            self.reg_modal
        )

    @discord.ui.button(label="Keep My Team Name", style=discord.ButtonStyle.secondary)
    async def keep_mine(self, interaction: discord.Interaction, button: discord.ui.Button):
        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(view=self)
        await complete_registration(
            interaction,
            self.ign,
            self.pronouns,
            self.user_team,
            self.reg_modal
        )

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
            self.add_item(RegisterButton())
            self.add_item(UnregisterButton())
            self.add_item(ToggleRegistrationButton())
        else:
            self.add_item(ToggleRegistrationButton())
            self.add_item(ResetRegistrationButton())

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
    await reg_msg.edit(embed=embed, view=RegistrationView(msg_id, guild))

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