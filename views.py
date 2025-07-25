# gal_discord_bot/views.py
from __future__ import annotations

import time
from datetime import datetime
from itertools import groupby

import discord
from rapidfuzz import process, fuzz

from config import (
    embed_from_cfg, CHECK_IN_CHANNEL, REGISTRATION_CHANNEL,
    REGISTERED_ROLE, CHECKED_IN_ROLE, ANGEL_ROLE, get_sheet_settings, LOG_CHANNEL_NAME
)
from logging_utils import log_error
from persistence import (
    get_persisted_msg, set_persisted_msg,
    get_event_mode_for_guild, get_schedule,
)
from sheets import (
    find_or_register_user, get_sheet_for_guild, retry_until_successful, mark_checked_in_async, unmark_checked_in_async,
    unregister_user, refresh_sheet_cache, reset_checked_in_roles_and_sheet, cache_lock, sheet_cache,
    reset_registered_roles_and_sheet
)
from utils import (
    has_allowed_role,
    has_allowed_role_from_interaction,
    toggle_persisted_channel, send_reminder_dms, toggle_checkin_for_member, hyperlink_lolchess_profile, )


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


async def complete_registration(
    interaction: discord.Interaction,
    ign: str,
    pronouns: str,
    team_name: str | None,
    alt_igns: str,
    reg_modal: "RegistrationModal"
):
    # 1) Defer once
    if not interaction.response.is_done():
        await interaction.response.defer(ephemeral=True)

    # 2) Resolve context
    guild       = getattr(reg_modal, "guild", None) or interaction.guild
    member      = getattr(reg_modal, "member", None) or interaction.user
    discord_tag = str(member)
    gid         = str(guild.id)

    # 3) Prepare sheet
    mode     = get_event_mode_for_guild(gid)
    settings = get_sheet_settings(mode)
    sheet    = get_sheet_for_guild(gid, "GAL Database")

    # 4) Find log channel
    log_channel = discord.utils.get(
        guild.text_channels,
        name=LOG_CHANNEL_NAME
    )

    try:
        # 5) Register/update user in sheet & cache
        if mode == "doubleup":
            row = await find_or_register_user(
                discord_tag, ign, guild_id=gid, team_name=team_name
            )
        else:
            row = await find_or_register_user(discord_tag, ign, guild_id=gid)

        # 6) Write pronouns
        pron_col = settings["pronouns_col"]
        await retry_until_successful(
            sheet.update_acell,
            f"{pron_col}{row}",
            pronouns
        )

        # 7) Write alt IGNs
        if alt_igns:
            alt_col = settings["alt_ign_col"]
            await retry_until_successful(
                sheet.update_acell,
                f"{alt_col}{row}",
                alt_igns
            )

        # 8) Write team (doubleup)
        if mode == "doubleup" and team_name:
            team_col = settings["team_col"]
            await retry_until_successful(
                sheet.update_acell,
                f"{team_col}{row}",
                team_name
            )

        # 9) Assign Registered role
        reg_role = discord.utils.get(
            guild.roles,
            name=settings.get("registered_role", REGISTERED_ROLE)
        )
        if reg_role and reg_role not in member.roles:
            await member.add_roles(reg_role)

        # 10) Refresh both embeds
        from views import update_registration_embed, update_checkin_embed
        chan_id, msg_id = get_persisted_msg(guild.id, "registration")
        if chan_id:
            ch = guild.get_channel(chan_id)
            await update_registration_embed(ch, msg_id, guild)
        ci_chan, ci_msg = get_persisted_msg(guild.id, "checkin")
        if ci_chan:
            ci_ch = guild.get_channel(ci_chan)
            await update_checkin_embed(ci_ch, ci_msg, guild)

        # 11) Send success confirmation
        embed_key = (
            "register_success_doubleup"
            if mode == "doubleup"
            else "register_success_normal"
        )
        success_embed = embed_from_cfg(
            embed_key,
            ign=ign,
            pronouns=pronouns,
            team_name=team_name or "N/A"
        )
        await interaction.followup.send(embed=success_embed, ephemeral=True)

        # 12) Log success
        if log_channel:
            await log_channel.send(
                f"✅ **REGISTER** — Guild: **{guild.name}** (`{guild.id}`) "
                f"— User: **{discord_tag}**"
            )

    except Exception as e:
        # a) Log the error
        err_msg = (
            f"❌ **REGISTER FAILED** — Guild: **{guild.name}** (`{guild.id}`) "
            f"— User: **{discord_tag}** — Error: {e}"
        )
        if log_channel:
            await log_channel.send(err_msg)
        else:
            # fallback to global logger
            await log_error(interaction.client, guild, f"[REGISTER-FAIL] {discord_tag} — {e}")

        # b) Inform the user
        fail_embed = embed_from_cfg("register_fail")
        await interaction.followup.send(embed=fail_embed, ephemeral=True)

class ChannelCheckInButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="Check In",
            style=discord.ButtonStyle.success,
            custom_id="channel_checkin_btn"
        )

    async def callback(self, interaction: discord.Interaction):
        member = interaction.user
        guild  = interaction.guild

        # 1) Must be registered
        reg_role = discord.utils.get(guild.roles, name=REGISTERED_ROLE)
        if reg_role not in member.roles:
            return await interaction.response.send_message(
                embed=embed_from_cfg("checkin_requires_registration"),
                ephemeral=True
            )

        # 2) Must not already be checked in
        ci_role = discord.utils.get(guild.roles, name=CHECKED_IN_ROLE)
        if ci_role in member.roles:
            return await interaction.response.send_message(
                embed=embed_from_cfg("already_checked_in"),
                ephemeral=True
            )

        # 3) Perform check-in, assign role, refresh embed
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
        member = interaction.user
        guild  = interaction.guild

        # 1) Must be registered
        reg_role = discord.utils.get(guild.roles, name=REGISTERED_ROLE)
        if reg_role not in member.roles:
            return await interaction.response.send_message(
                embed=embed_from_cfg("checkin_requires_registration"),
                ephemeral=True
            )

        # 2) Must currently be checked in
        ci_role = discord.utils.get(guild.roles, name=CHECKED_IN_ROLE)
        if ci_role not in member.roles:
            return await interaction.response.send_message(
                embed=embed_from_cfg("already_checked_out"),
                ephemeral=True
            )

        # 3) Perform check-out, remove role, refresh embed
        await toggle_checkin_for_member(
            interaction,
            unmark_checked_in_async,
            "checked_out"
        )

# ─── DM REGISTER/UNREGISTER TOGGLE ──────────────────────────────

class DMRegisterToggleButton(discord.ui.Button):
    def __init__(self, guild: discord.Guild, member: discord.Member):
        # Label/style flips automatically based on registration state
        is_reg = discord.utils.get(guild.roles, name=REGISTERED_ROLE) in member.roles
        super().__init__(
            label="Unregister" if is_reg else "Register",
            style=discord.ButtonStyle.danger if is_reg else discord.ButtonStyle.success,
            custom_id=f"dm_regmodal_{guild.id}_{member.id}"
        )
        self.guild = guild
        self.member = member

    async def callback(self, interaction: discord.Interaction):
        guild_id    = str(self.guild.id)
        mode        = get_event_mode_for_guild(guild_id)
        discord_tag = str(self.member)

        # ─── Prefill from cache ────────────────────────────────────
        ign = pronouns = team_name = alt_igns = ""
        async with cache_lock:
            tup = sheet_cache["users"].get(discord_tag)
        if tup:
            ign        = tup[1]
            team_name  = tup[4] if len(tup) > 4 else ""
            alt_igns   = tup[5] if len(tup) > 5 else ""
            # Pronouns come from column C
            sheet = get_sheet_for_guild(guild_id, "GAL Database")
            try:
                cell = await retry_until_successful(sheet.acell, f"C{tup[0]}")
                pronouns = cell.value or ""
            except:
                pronouns = ""

        # ─── Build & show the modal ────────────────────────────────
        if mode == "doubleup":
            modal = RegistrationModal(
                team_field       = True,
                default_ign      = ign,
                default_alt_igns = alt_igns,
                default_team     = team_name,
                default_pronouns = pronouns
            )
        else:
            modal = RegistrationModal(
                team_field       = False,
                default_ign      = ign,
                default_alt_igns = alt_igns,
                default_pronouns = pronouns
            )

        # Attach context and pop the modal
        modal.guild  = self.guild
        modal.member = self.member
        await interaction.response.send_modal(modal)

# ─── DM CHECK-IN/OUT TOGGLE ──────────────────────────────────────

class DMCheckToggleButton(discord.ui.Button):
    def __init__(self, guild: discord.Guild, member: discord.Member):
        self.guild = guild
        self.member = member

        reg_role = discord.utils.get(guild.roles, name=REGISTERED_ROLE)
        ci_role  = discord.utils.get(guild.roles, name=CHECKED_IN_ROLE)
        ci_ch    = discord.utils.get(guild.text_channels, name=CHECK_IN_CHANNEL)
        is_open  = bool(ci_ch and ci_ch.overwrites_for(reg_role).view_channel)
        is_reg   = reg_role in member.roles
        is_ci    = ci_role in member.roles

        label    = "Check Out" if is_ci else "Check In"
        style    = discord.ButtonStyle.danger if is_ci else discord.ButtonStyle.success
        custom_id= f"dm_citoggle_{guild.id}_{member.id}"

        super().__init__(
            label=label,
            style=style,
            custom_id=custom_id,
            disabled=not (is_open and is_reg)
        )

    async def callback(self, interaction: discord.Interaction):
        # 1) Must be registered
        reg_role = discord.utils.get(self.guild.roles, name=REGISTERED_ROLE)
        if reg_role not in self.member.roles:
            return await interaction.response.send_message(
                embed=embed_from_cfg("checkin_requires_registration"), ephemeral=True
            )

        # 2) Determine current state
        ci_role = discord.utils.get(self.guild.roles, name=CHECKED_IN_ROLE)
        is_ci   = ci_role in self.member.roles

        # 3) Guard redundant actions
        if self.label == "Check In" and is_ci:
            return await interaction.response.send_message(
                embed=embed_from_cfg("already_checked_in"), ephemeral=True
            )
        if self.label == "Check Out" and not is_ci:
            return await interaction.response.send_message(
                embed=embed_from_cfg("already_checked_out"), ephemeral=True
            )

        # 4) Perform the toggle
        await toggle_checkin_for_member(
            interaction,
            mark_checked_in_async if self.label == "Check In" else unmark_checked_in_async,
            "checked_in" if self.label == "Check In" else "checked_out",
            guild=self.guild,
            member=self.member
        )

        # 5) Redraw the DM view so buttons re-enable/disable correctly
        from views import DMActionView
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
        guild_id    = str(interaction.guild.id)
        mode        = get_event_mode_for_guild(guild_id)
        member      = interaction.user
        discord_tag = str(member)

        # 1) Prefill from cache (now including alt_igns)
        ign = pronouns = team_name = alt_igns = ""
        async with cache_lock:
            tup = sheet_cache["users"].get(discord_tag)
        if tup:
            ign        = tup[1]
            team_name  = tup[4] if len(tup) > 4 else ""
            alt_igns   = tup[5] if len(tup) > 5 else ""
            # pronouns from sheet col C
            sheet = get_sheet_for_guild(guild_id, "GAL Database")
            try:
                cell = await retry_until_successful(sheet.acell, f"C{tup[0]}")
                pronouns = cell.value or ""
            except:
                pronouns = ""

        # 2) Build the modal with default_alt_igns
        if mode == "doubleup":
            modal = RegistrationModal(
                team_field=True,
                default_ign=ign,
                default_alt_igns=alt_igns,
                default_team=team_name,
                default_pronouns=pronouns
            )
        else:
            modal = RegistrationModal(
                team_field=False,
                default_ign=ign,
                default_alt_igns=alt_igns,
                default_pronouns=pronouns
            )

        # 3) Attach context so complete_registration works in DMs too
        modal.guild  = interaction.guild
        modal.member = interaction.user

        # 4) Show the modal
        await interaction.response.send_modal(modal)

class UnregisterButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="Unregister",
            style=discord.ButtonStyle.danger,
            custom_id="unregister_btn"
        )

    async def callback(self, interaction: discord.Interaction):
        guild       = interaction.guild
        member      = interaction.user
        discord_tag = str(member)
        guild_id    = str(guild.id)

        # Grab from cache
        async with cache_lock:
            tup = sheet_cache["users"].get(discord_tag)

        # If not registered (now bool!) :contentReference[oaicite:6]{index=6}
        if not tup or not tup[2]:
            return await interaction.response.send_message(
                embed=embed_from_cfg("unregister_not_registered"),
                ephemeral=True
            )

        # Attempt to unregister
        ok = await unregister_user(discord_tag, guild_id=guild_id)
        if not ok:
            return await interaction.response.send_message(
                embed=embed_from_cfg("unregister_fail"),
                ephemeral=True
            )

        # Remove roles, confirm, refresh embeds...
        reg_role = discord.utils.get(guild.roles, name=REGISTERED_ROLE)
        ci_role  = discord.utils.get(guild.roles, name=CHECKED_IN_ROLE)
        await member.remove_roles(*(r for r in (reg_role, ci_role) if r in member.roles))

        await interaction.response.send_message(
            embed=embed_from_cfg("unregister_success"),
            ephemeral=True
        )

        # refresh both persisted embeds
        from persistence import get_persisted_msg
        from views import update_registration_embed, update_checkin_embed

        chan_id, msg_id = get_persisted_msg(guild.id, "registration")
        if chan_id:
            ch = guild.get_channel(chan_id)
            await update_registration_embed(ch, msg_id, guild)

        ci_chan, ci_msg = get_persisted_msg(guild.id, "checkin")
        if ci_chan:
            ci_ch = guild.get_channel(ci_chan)
            await update_checkin_embed(ci_ch, ci_msg, guild)

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
    def __init__(
        self,
        *,
        team_field: bool = False,
        default_ign: str | None      = None,
        default_alt_igns: str | None = None,
        default_team: str | None     = None,
        default_pronouns: str | None = None,
        bypass_similarity: bool      = False
    ):
        super().__init__(title="Register for the Event")
        self.bypass_similarity = bypass_similarity

        # In-Game Name
        self.ign_input = discord.ui.TextInput(
            label="In-Game Name",
            placeholder="Enter your TFT IGN",
            required=True,
            default=default_ign or ""
        )
        self.add_item(self.ign_input)

        # Alternative IGN(s)
        self.alt_ign_input = discord.ui.TextInput(
            label="Alternative IGN(s)",
            placeholder="Comma-separated alt IGNs (optional)",
            required=False,
            default=default_alt_igns or ""
        )
        self.add_item(self.alt_ign_input)

        # Team Name (doubleup only)
        self.team_input = None
        if team_field:
            self.team_input = discord.ui.TextInput(
                label="Team Name",
                placeholder="Your Team Name",
                required=True,
                default=default_team or ""
            )
            self.add_item(self.team_input)

        # Pronouns
        self.pronouns_input = discord.ui.TextInput(
            label="Pronouns",
            placeholder="e.g. She/Her, He/Him, They/Them",
            required=False,
            default=default_pronouns or ""
        )
        self.add_item(self.pronouns_input)

    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild
        user = interaction.user
        guild_id = str(guild.id)
        discord_tag = str(user)
        mode = get_event_mode_for_guild(guild_id)
        ign = self.ign_input.value
        pronouns = self.pronouns_input.value
        team_value = self.team_input.value if self.team_input else None
        alt_igns = self.alt_ign_input.value.strip() if self.alt_ign_input else None

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
                team_col_raw = await retry_until_successful(sheet.col_values, 9)
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
            await complete_registration(
                interaction,
                ign,
                pronouns,
                team_value,
                alt_igns,  # pass alt_igns here
                self  # reg_modal
            )

        except Exception as e:
            await log_error(interaction.client, interaction.guild, f"[REGISTER-MODAL-ERROR] {e}")

class TeamNameChoiceView(discord.ui.View):
    def __init__(self, reg_modal, ign, pronouns, suggested_team, user_team):
        super().__init__(timeout=60)
        self.reg_modal     = reg_modal
        self.ign           = ign
        self.pronouns      = pronouns
        self.suggested_team= suggested_team
        self.user_team     = user_team

    @discord.ui.button(label="Use Suggested", style=discord.ButtonStyle.success)
    async def use_suggested(self, interaction, button):
        # disable buttons…
        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(view=self)

        await complete_registration(
            interaction,
            self.ign,
            self.pronouns,
            self.suggested_team,
            self.reg_modal.alt_ign_input.value.strip(),  # NEW
            self.reg_modal
        )

    @discord.ui.button(label="Keep My Team Name", style=discord.ButtonStyle.secondary)
    async def keep_mine(self, interaction, button):
        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(view=self)

        await complete_registration(
            interaction,
            self.ign,
            self.pronouns,
            self.user_team,
            self.reg_modal.alt_ign_input.value.strip(),  # NEW
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

async def update_registration_embed(
    channel: discord.TextChannel,
    msg_id: int,
    guild: discord.Guild
):
    # Determine open/closed
    reg_ch     = discord.utils.get(guild.text_channels, name=REGISTRATION_CHANNEL)
    angel_role = discord.utils.get(guild.roles,         name=ANGEL_ROLE)
    is_open    = bool(reg_ch and angel_role and reg_ch.overwrites_for(angel_role).view_channel)

    # Base embed
    base_key = "registration" if is_open else "registration_closed"
    base     = embed_from_cfg(base_key)

    # If closed → swap only
    msg = await channel.fetch_message(msg_id)
    if not is_open:
        return await msg.edit(embed=base, view=RegistrationView(msg_id, guild))

    # Fetch cache (registered flag is now a bool!) :contentReference[oaicite:4]{index=4}
    mode = get_event_mode_for_guild(str(guild.id))
    async with cache_lock:
        users = [
            (tag, tpl[1], tpl[4] if len(tpl) > 4 else "")
            for tag, tpl in sheet_cache["users"].items()
            if tpl[2]        # was `str(tpl[2]).upper() == "TRUE"`
        ]

    # Build lines & summary
    if mode == "normal":
        summary = f"**Registered Players:** {len(users)}"
        lines   = [f"• `{tag}` (`{ign}`)" for tag, ign, _ in users]
    else:
        users.sort(key=lambda x: x[2].lower())
        grouped = groupby(users, key=lambda x: x[2] or "No Team")
        lines, teams = [], 0
        for team, grp in grouped:
            grp = list(grp); teams += 1
            lines.append(f"**{team}** ({len(grp)})")
            for tag, ign, _ in grp:
                lines.append(f"    • `{tag}` (`{ign}`)")
            lines.append("")
        if lines and not lines[-1].strip():
            lines.pop()
        summary = f"**Players:** {len(users)}   **Teams:** {teams}"

    # Inject close time
    desc      = (base.description or "") + "\n"
    close_iso = get_schedule(guild.id, "registration_close")
    if close_iso:
        ts = int(datetime.fromisoformat(close_iso).timestamp())
        desc += f"⏰ Registration closes at <t:{ts}:F>\n\n\n"

    # Append list
    desc += summary
    if lines:
        desc += "\n\n" + "\n".join(lines)

    # Edit
    embed = discord.Embed(title=base.title, description=desc, color=base.color)
    await msg.edit(embed=embed, view=RegistrationView(msg_id, guild))



async def update_checkin_embed(
    channel: discord.TextChannel,
    msg_id: int,
    guild: discord.Guild
):
    # Determine open/closed
    ci_ch    = discord.utils.get(guild.text_channels, name=CHECK_IN_CHANNEL)
    reg_role = discord.utils.get(guild.roles,         name=REGISTERED_ROLE)
    is_open  = bool(ci_ch and reg_role and ci_ch.overwrites_for(reg_role).view_channel)

    # Base embed
    base_key = "checkin" if is_open else "checkin_closed"
    base     = embed_from_cfg(base_key)

    # If closed → swap only
    msg = await channel.fetch_message(msg_id)
    if not is_open:
        return await msg.edit(embed=base, view=CheckInView(guild))

    # Inject close time
    desc      = base.description or ""
    close_iso = get_schedule(guild.id, "checkin_close")
    if close_iso:
        ts = int(datetime.fromisoformat(close_iso).timestamp())
        desc += f"\n⏰ Check-in closes at <t:{ts}:t>"

    # Gather from cache :contentReference[oaicite:5]{index=5}
    mode = get_event_mode_for_guild(str(guild.id))
    async with cache_lock:
        registered = [(tag, tpl[1], tpl[4] if len(tpl)>4 else "")
                      for tag, tpl in sheet_cache["users"].items()
                      if tpl[2]]            # was checking tpl[2].upper()
        checked_in = [(tag, tpl[1], tpl[4] if len(tpl)>4 else "")
                      for tag, tpl in sheet_cache["users"].items()
                      if tpl[2] and tpl[3]]  # was checking both .upper()

    total_reg = len(registered)
    total_ci  = len(checked_in)

    # Build summary & lines
    if mode == "normal":
        summary = f"**Checked In:** {total_ci}/{total_reg}"
        lines   = [f"• `{tag}` (`{ign}`)" for tag, ign, _ in checked_in]
    else:
        checked_in.sort(key=lambda x: x[2].lower())
        grouped = groupby(checked_in, key=lambda x: x[2] or "No Team")
        lines, checked_teams = [], 0
        total_teams = len({tpl[2] or "No Team" for tpl in registered})
        for team, grp in grouped:
            grp = list(grp); checked_teams += 1
            lines.append(f"**{team}** ({len(grp)})")
            for tag, ign, _ in grp:
                lines.append(f"    • `{tag}` (`{ign}`)")
            lines.append("")
        if lines and not lines[-1].strip():
            lines.pop()
        summary = (f"**Checked In:** {total_ci}/{total_reg}  "
                   f"**Teams:** {checked_teams}/{total_teams}")

    # Append to desc
    desc += f"\n\n\n{summary}"
    if lines:
        desc += "\n\n" + "\n".join(lines)

    # Edit
    embed = discord.Embed(title=base.title, description=desc, color=base.color)
    await msg.edit(embed=embed, view=CheckInView(guild))