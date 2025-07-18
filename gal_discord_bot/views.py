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
    find_or_register_user, get_sheet_for_guild, retry_until_successful, mark_checked_in_async, unmark_checked_in_async,
    unregister_user, refresh_sheet_cache, reset_checked_in_roles_and_sheet, cache_lock, sheet_cache,
    reset_registered_roles_and_sheet
)
from gal_discord_bot.utils import (
    has_allowed_role,
    has_allowed_role_from_interaction,
    toggle_persisted_channel, send_reminder_dms, toggle_checkin_for_member, delete_previous_registrations,
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
    """
    Handles RegistrationModal submissions from both channel & DM.
    Expects reg_modal.guild and reg_modal.member to be set,
    and that interaction.response.defer(...) was already called.
    """
    # Resolve context
    guild = getattr(reg_modal, "guild", None) or interaction.guild
    user  = getattr(reg_modal, "member", None) or interaction.user
    guild_id    = str(guild.id)
    discord_tag = str(user)
    mode        = get_event_mode_for_guild(guild_id)
    reg_role    = discord.utils.get(guild.roles, name=REGISTERED_ROLE)

    try:
        # 1) Write to sheet & update pronouns
        if mode == "doubleup":
            row_num = await find_or_register_user(
                discord_tag, ign,
                guild_id=guild_id, team_name=team_name
            )
        else:
            row_num = await find_or_register_user(
                discord_tag, ign,
                guild_id=guild_id
            )
        sheet = get_sheet_for_guild(guild_id, "GAL Database")
        await retry_until_successful(sheet.update_acell, f"C{row_num}", pronouns)

        # 2) Assign Registered role
        if reg_role and reg_role not in user.roles:
            await user.add_roles(reg_role)

        # 3) Refresh live embeds
        await update_live_embeds(guild)

        # 4) Delete any prior confirmations in the registration channel
        chan_id, main_msg_id = get_persisted_msg(guild.id, "registration")
        reg_ch = guild.get_channel(chan_id) if chan_id else None
        if not reg_ch:
            reg_ch = discord.utils.get(guild.text_channels, name=REGISTRATION_CHANNEL)

        if reg_ch:
            async for msg in reg_ch.history(limit=100):
                if msg.id == main_msg_id or not (msg.author.bot and msg.embeds):
                    continue
                emb = msg.embeds[0]
                footer = emb.footer.text if emb.footer else ""
                if footer == user.name:
                    try:
                        await msg.delete()
                    except:
                        pass

        # 5) Also clean up old DMs (if any)
        if isinstance(interaction.channel, discord.DMChannel):
            dm = await user.create_dm()
            async for msg in dm.history(limit=50):
                if not (msg.author == interaction.client.user and msg.embeds):
                    continue
                emb = msg.embeds[0]
                footer = emb.footer.text if emb.footer else ""
                if footer == user.name:
                    try:
                        await msg.delete()
                    except:
                        pass

        # 6) Build & send fresh success embed
        key = "register_success_doubleup" if mode == "doubleup" else "register_success_normal"
        embed = embed_from_cfg(
            key,
            ign=ign,
            team_name=team_name or "",
            name=user.mention
        )
        original_title = embed.title or ""
        embed.title = None
        embed.set_author(name=original_title, icon_url=user.display_avatar.url)
        # footer now only the Discord username
        embed.set_footer(text=user.name)

        await interaction.followup.send(embed=embed, ephemeral=False)

        # 7) If in DM, redraw the buttons view
        if isinstance(interaction.channel, discord.DMChannel):
            dm = await user.create_dm()
            async for msg in dm.history(limit=5):
                if msg.author == interaction.client.user and msg.components:
                    await msg.edit(view=DMActionView(guild, user))
                    break

    except Exception as e:
        await log_error(interaction.client, guild, f"[REGISTER-MODAL-ERROR] {e}")

class ChannelCheckInButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="Check In",
            style=discord.ButtonStyle.success,
            custom_id="channel_checkin_btn"
        )

    async def callback(self, interaction: discord.Interaction):
        # Uses your helper to handle the sheet write, cache update, embed send, and view refresh
        await toggle_checkin_for_member(
            interaction,
            mark_checked_in_async,
            "checked_in"
        )

class ChannelCheckOutButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="Check Out",
            style=discord.ButtonStyle.danger,
            custom_id="channel_checkout_btn"
        )

    async def callback(self, interaction: discord.Interaction):
        await toggle_checkin_for_member(
            interaction,
            unmark_checked_in_async,
            "checked_out"
        )

# ─── DM REGISTER/UNREGISTER TOGGLE ──────────────────────────────

class DMRegisterToggleButton(discord.ui.Button):
    def __init__(self, guild: discord.Guild, member: discord.Member):
        self.guild, self.member = guild, member
        # Toggle label/style based on current registration state
        reg_role = discord.utils.get(guild.roles, name=REGISTERED_ROLE)
        is_reg   = reg_role in member.roles
        label    = "Unregister" if is_reg else "Register"
        style    = discord.ButtonStyle.danger if is_reg else discord.ButtonStyle.success
        cid      = f"dm_regmodal_{guild.id}_{member.id}"

        super().__init__(label=label, style=style, custom_id=cid)

    async def callback(self, interaction: discord.Interaction):
        # 1) Prefill exactly as in RegisterButton
        guild_id = str(self.guild.id)
        mode     = get_event_mode_for_guild(guild_id)
        discord_tag = str(self.member)

        # Try to prefill from cache
        ign = pronouns = team_name = ""
        async with cache_lock:
            tup = sheet_cache["users"].get(discord_tag)
            if tup:
                ign       = tup[1]
                team_name = tup[4] if len(tup) > 4 else ""
                sheet     = get_sheet_for_guild(guild_id, "GAL Database")
                try:
                    cell = await retry_until_successful(sheet.acell, f"C{tup[0]}")
                    pronouns = cell.value or ""
                except:
                    pronouns = ""

        # 2) Build the modal
        if mode == "doubleup":
            modal = RegistrationModal(
                team_field=True,
                default_ign=ign,
                default_team=team_name,
                default_pronouns=pronouns
            )
        else:
            modal = RegistrationModal(
                team_field=False,
                default_ign=ign,
                default_pronouns=pronouns
            )

        # 3) Attach context for complete_registration
        modal.guild  = self.guild
        modal.member = self.member

        # 4) Show the modal in DM
        await interaction.response.send_modal(modal)

# ─── DM CHECK-IN/OUT TOGGLE ──────────────────────────────────────

class DMCheckToggleButton(discord.ui.Button):
    def __init__(self, guild: discord.Guild, member: discord.Member):
        self.guild, self.member = guild, member
        # determine state & availability
        reg_role = discord.utils.get(guild.roles, name=REGISTERED_ROLE)
        ci_role  = discord.utils.get(guild.roles, name=CHECKED_IN_ROLE)
        ci_ch    = discord.utils.get(guild.text_channels, name=CHECK_IN_CHANNEL)
        is_open  = bool(ci_ch and ci_ch.overwrites_for(reg_role).view_channel)
        is_reg   = reg_role in member.roles
        is_ci    = ci_role in member.roles

        label = "Check Out" if is_ci else "Check In"
        style = discord.ButtonStyle.danger if is_ci else discord.ButtonStyle.success
        cid   = f"dm_citoggle_{guild.id}_{member.id}"
        super().__init__(
            label=label,
            style=style,
            custom_id=cid,
            disabled=not (is_open and is_reg)
        )

    async def callback(self, interaction: discord.Interaction):
        # pass our stored guild & member so toggle_checkin_for_member can assign roles correctly
        await toggle_checkin_for_member(
            interaction,
            mark_checked_in_async if self.label == "Check In" else unmark_checked_in_async,
            "checked_in" if self.label == "Check In" else "checked_out",
            guild=self.guild,
            member=self.member
        )

        # redraw your per-user DM view
        await interaction.edit_original_response(view=DMActionView(self.guild, self.member))

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
        # 1) Gather context & prefill values
        guild_id = str(interaction.guild.id)
        mode     = get_event_mode_for_guild(guild_id)
        user     = interaction.user
        discord_tag = str(user)

        # Try to prefill from the cache if available
        ign = pronouns = team_name = ""
        async with cache_lock:
            tup = sheet_cache["users"].get(discord_tag)
            if tup:
                ign       = tup[1]
                team_name = tup[4] if len(tup) > 4 else ""
                # pronouns from sheet col C
                sheet = get_sheet_for_guild(guild_id, "GAL Database")
                try:
                    cell = await retry_until_successful(sheet.acell, f"C{tup[0]}")
                    pronouns = cell.value or ""
                except:
                    pronouns = ""

        # 2) Build the modal
        if mode == "doubleup":
            modal = RegistrationModal(
                team_field=True,
                default_ign=ign,
                default_team=team_name,
                default_pronouns=pronouns
            )
        else:
            modal = RegistrationModal(
                team_field=False,
                default_ign=ign,
                default_pronouns=pronouns
            )

        # 3) Attach context so complete_registration works in DMs too
        modal.guild  = interaction.guild
        modal.member = interaction.user

        # 4) Send the modal
        await interaction.response.send_modal(modal)

class UnregisterButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="Unregister",
            style=discord.ButtonStyle.danger,
            custom_id="unregister_btn"
        )

    async def callback(self, interaction: discord.Interaction):
        guild  = interaction.guild
        member = interaction.user
        discord_tag = str(member)
        guild_id    = str(guild.id)

        try:
            # 1) Check registration state
            async with cache_lock:
                tup = sheet_cache["users"].get(discord_tag)
            is_registered = bool(tup and str(tup[2]).upper() == "TRUE")
            if not is_registered:
                embed = embed_from_cfg("unregister_not_registered")
                return await interaction.response.send_message(embed=embed, ephemeral=True)

            # 2) Unregister in sheet + cache
            ok = await unregister_user(discord_tag, guild_id=guild_id)
            if not ok:
                # silent fail: log and return
                await log_error(interaction.client, guild, f"[UNREGISTER-FAIL] Could not unregister {discord_tag}")
                return

            # 3) Remove roles
            reg_role = discord.utils.get(guild.roles, name=REGISTERED_ROLE)
            ci_role  = discord.utils.get(guild.roles, name=CHECKED_IN_ROLE)
            to_remove = [r for r in (reg_role, ci_role) if r and r in member.roles]
            if to_remove:
                await member.remove_roles(*to_remove)

            # 4) Delete old confirmations (channel + DM)
            await delete_previous_registrations(guild, member)

            # 5) Send success confirmation
            embed = embed_from_cfg("unregister_success")
            await interaction.response.send_message(embed=embed, ephemeral=True)

            # 6) Refresh the persisted registration embed
            chan_id, msg_id = get_persisted_msg(guild.id, "registration")
            if chan_id and msg_id:
                ch = guild.get_channel(chan_id)
                await update_registration_embed(ch, msg_id, guild)

        except Exception as e:
            # silent fail on unexpected errors
            await log_error(interaction.client, guild, f"[UNREGISTER-BUTTON-ERROR] {e}")

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
            label="✉️ DM Reminder to Unchecked",
            style=discord.ButtonStyle.primary,
            custom_id=f"reminder_dm_all_{guild_id}"
        )
        self.guild_id = guild_id

    async def callback(self, interaction: discord.Interaction):
        if not has_allowed_role_from_interaction(interaction):
            return await interaction.response.send_message(
                embed=embed_from_cfg("permission_denied"),
                ephemeral=True
            )

        await interaction.response.defer()

        guild = interaction.client.get_guild(self.guild_id)
        dm_embed = embed_from_cfg("reminder_dm")

        # <-- NEW: send all DMs via helper -->
        dmmed = await send_reminder_dms(
            client=interaction.client,
            guild=guild,
            dm_embed=dm_embed,
            view_cls=DMActionView
        )

        # Report back
        count = len(dmmed)
        users_list = "\n".join(dmmed) or "No users could be DM'd."
        public = embed_from_cfg("reminder_public", count=count, users=users_list)
        await interaction.followup.send(embed=public)

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

        await interaction.response.defer(ephemeral=True)  # Show "thinking..."

        if reg_channel and angel_role:
            overwrites = reg_channel.overwrites_for(angel_role)
            if not overwrites.view_channel:
                embed = embed_from_cfg("registration_closed")
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

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
        checkin_ch = discord.utils.get(guild.text_channels, name=CHECK_IN_CHANNEL)
        reg_role   = discord.utils.get(guild.roles, name=REGISTERED_ROLE)
        is_open = bool(checkin_ch and reg_role and checkin_ch.overwrites_for(reg_role).view_channel)

        if is_open:
            # show both separate buttons + toggle
            self.add_item(ChannelCheckInButton())
            self.add_item(ChannelCheckOutButton())
            self.add_item(ToggleCheckInButton())
        else:
            # when closed, just toggle/reset
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

class DMActionView(discord.ui.View):
    def __init__(self, guild: discord.Guild, member: discord.Member):
        super().__init__(timeout=None)
        self.guild, self.member = guild, member

        # ─── Determine channel‐open status ─────────────────────────
        reg_ch = discord.utils.get(guild.text_channels, name=REGISTRATION_CHANNEL)
        angel_role = discord.utils.get(guild.roles, name=ANGEL_ROLE)
        # registration open if ANGEL_ROLE can view that channel
        reg_open = bool(reg_ch and angel_role and reg_ch.overwrites_for(angel_role).view_channel)

        ci_ch = discord.utils.get(guild.text_channels, name=CHECK_IN_CHANNEL)
        reg_role = discord.utils.get(guild.roles, name=REGISTERED_ROLE)
        # check-in open if REGISTERED_ROLE can view that channel
        ci_open = bool(ci_ch and reg_role and ci_ch.overwrites_for(reg_role).view_channel)

        is_reg = reg_role in member.roles

        # ─── Register / Unregister toggle (always shown) ──────────
        reg_btn = DMRegisterToggleButton(guild, member)
        # only enable if reg channel is open
        reg_btn.disabled = not reg_open
        self.add_item(reg_btn)

        # ─── Check In / Check Out toggle ──────────────────────────
        if ci_open and is_reg:
            self.add_item(DMCheckToggleButton(guild, member))

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