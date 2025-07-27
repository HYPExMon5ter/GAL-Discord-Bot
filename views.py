# gal_discord_bot/views.py
from __future__ import annotations

import itertools
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
    # 1) Defer if not already
    if not interaction.response.is_done():
        await interaction.response.defer(ephemeral=True)

    # 2) Resolve context
    guild       = getattr(reg_modal, "guild", None) or interaction.guild
    member      = getattr(reg_modal, "member", None) or interaction.user
    discord_tag = str(member)
    gid         = str(guild.id)

    # 3) Console log inputs
    print(f"[REGISTER] Guild={guild.name}({gid}) "
          f"User={discord_tag} IGN={ign!r} Team={team_name!r} Alts={alt_igns!r}")

    # 4) Mode & sheet settings
    mode         = get_event_mode_for_guild(gid)
    sheet_cfg    = get_sheet_settings(mode)
    max_players  = sheet_cfg.get("max_players", 0)
    max_per_team = sheet_cfg.get("max_per_team", 2)

    # 5) Guard total registrations
    async with cache_lock:
        total_registered = sum(
            1 for tpl in sheet_cache["users"].values()
            if str(tpl[2]).upper() == "TRUE"
        )
    if total_registered >= max_players:
        err = embed_from_cfg("registration_full", max_players=max_players)
        return await interaction.followup.send(embed=err, ephemeral=True)

    # 6) Guard per-team capacity
    if mode == "doubleup" and team_name:
        async with cache_lock:
            count_on_team = sum(
                1 for tpl in sheet_cache["users"].values()
                if str(tpl[2]).upper() == "TRUE" and tpl[4] == team_name
            )
        if count_on_team >= max_per_team:
            err = embed_from_cfg(
                "team_full",
                team_name=team_name,
                max_per_team=max_per_team
            )
            return await interaction.followup.send(embed=err, ephemeral=True)

    try:
        # 7) Upsert user row
        row = await find_or_register_user(
            discord_tag,
            ign,
            guild_id=gid,
            team_name=(team_name if mode == "doubleup" else None)
        )

        # 8) Update sheet cells
        sheet = get_sheet_for_guild(gid, "GAL Database")
        await retry_until_successful(
            sheet.update_acell,
            f"{sheet_cfg['pronouns_col']}{row}",
            pronouns
        )
        if alt_igns:
            await retry_until_successful(
                sheet.update_acell,
                f"{sheet_cfg['alt_ign_col']}{row}",
                alt_igns
            )
        if mode == "doubleup" and team_name:
            await retry_until_successful(
                sheet.update_acell,
                f"{sheet_cfg['team_col']}{row}",
                team_name
            )

        # 9) Assign Registered role
        reg_role = discord.utils.get(guild.roles, name=REGISTERED_ROLE)
        if reg_role and reg_role not in member.roles:
            await member.add_roles(reg_role)

        # 10) Refresh embeds
        for key, updater in (
            ("registration", update_registration_embed),
            ("checkin",      update_checkin_embed),
        ):
            chan_id, msg_id = get_persisted_msg(gid, key)
            if chan_id:
                ch = guild.get_channel(chan_id)
                await updater(ch, msg_id, guild)

        # 11) Send success embed
        ok_key = f"register_success_{mode}"
        success_embed = embed_from_cfg(
            ok_key,
            ign=ign,
            team_name=(team_name or "–")
        )
        await interaction.followup.send(embed=success_embed, ephemeral=True)

        # 12) Hyperlink only the main IGN
        await hyperlink_lolchess_profile(discord_tag, gid)

        print(f"[REGISTER SUCCESS] {discord_tag} in guild {guild.name}")

    except Exception as e:
        # 13) Silent fail + log details
        await log_error(
            interaction.client,
            guild,
            f"[REGISTER ERROR] {e} — "
            f"IGN={ign!r}, Team={team_name!r}, Alts={alt_igns!r}"
        )

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

        print(f"[CHECK-IN] Guild={guild.name}({guild.id}) User={member}")

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

        print(f"[CHECK-OUT] Guild={guild.name}({guild.id}) User={member}")

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
        is_reg = discord.utils.get(guild.roles, name=REGISTERED_ROLE) in member.roles
        label = "Unregister" if is_reg else "Register"
        style = discord.ButtonStyle.danger if is_reg else discord.ButtonStyle.success
        super().__init__(
            label=label,
            style=style,
            custom_id=f"dm_regtoggle_{guild.id}_{member.id}"
        )
        self.guild = guild
        self.member = member

    async def callback(self, interaction: discord.Interaction):
        # ─── Unregister flow ──────────────────────────────────────────
        if self.label == "Unregister":
            discord_tag = str(self.member)
            ok = await unregister_user(discord_tag, guild_id=str(self.guild.id))
            if ok:
                # remove any roles
                reg_role = discord.utils.get(self.guild.roles, name=REGISTERED_ROLE)
                ci_role  = discord.utils.get(self.guild.roles, name=CHECKED_IN_ROLE)
                to_remove = [r for r in (reg_role, ci_role) if r and r in self.member.roles]
                if to_remove:
                    await self.member.remove_roles(*to_remove)
                # edit the DM to show success and refresh buttons
                await interaction.response.edit_message(
                    embed=embed_from_cfg("unregister_success"),
                    view=DMActionView(self.guild, self.member)
                )
            else:
                await interaction.response.send_message(
                    embed=embed_from_cfg("unregister_fail"),
                    ephemeral=True
                )
            return

        # ─── Register flow (pop the registration modal) ───────────────
        guild_id   = str(self.guild.id)
        mode       = get_event_mode_for_guild(guild_id)
        discord_tag= str(self.member)

        # Prefill from cache
        ign = pronouns = team_name = alt_igns = ""
        async with cache_lock:
            tup = sheet_cache["users"].get(discord_tag)
        if tup:
            row, saved_ign, _, _, saved_team, saved_alt = tup + ["", ""]  # unpack safely
            ign       = saved_ign
            team_name = saved_team
            alt_igns  = saved_alt
            # fetch pronouns from sheet
            settings = get_sheet_settings(mode)
            sheet    = get_sheet_for_guild(guild_id, "GAL Database")
            try:
                cell = await retry_until_successful(
                    sheet.acell,
                    f"{settings['pronouns_col']}{row}"
                )
                pronouns = cell.value or ""
            except:
                pronouns = ""

        # Build and show the modal
        common = {
            "default_ign": ign,
            "default_alt_igns": alt_igns,
            "default_pronouns": pronouns
        }
        if mode == "doubleup":
            modal = RegistrationModal(
                team_field=True,
                default_team=team_name,
                **common
            )
        else:
            modal = RegistrationModal(
                team_field=False,
                **common
            )

        # Attach context for completion handler
        modal.guild  = self.guild
        modal.member = self.member

        await interaction.response.send_modal(modal)

# ─── DM CHECK-IN/OUT TOGGLE ──────────────────────────────────────

class DMCheckToggleButton(discord.ui.Button):
    def __init__(self, guild: discord.Guild, member: discord.Member):
        self.guild  = guild
        self.member = member

        reg_role = discord.utils.get(guild.roles, name=REGISTERED_ROLE)
        ci_role  = discord.utils.get(guild.roles, name=CHECKED_IN_ROLE)
        ci_ch    = discord.utils.get(guild.text_channels, name=CHECK_IN_CHANNEL)
        is_open  = bool(ci_ch and ci_ch.overwrites_for(reg_role).view_channel)
        is_reg   = reg_role in member.roles
        is_ci    = ci_role in member.roles

        label     = "Check Out" if is_ci else "Check In"
        style     = discord.ButtonStyle.danger if is_ci else discord.ButtonStyle.success
        super().__init__(
            label=label,
            style=style,
            custom_id=f"dm_citoggle_{guild.id}_{member.id}",
            disabled=not (is_open and is_reg)
        )

    async def callback(self, interaction: discord.Interaction):
        # 1) Must be registered
        reg_role = discord.utils.get(self.guild.roles, name=REGISTERED_ROLE)
        if reg_role not in self.member.roles:
            return await interaction.response.send_message(
                embed=embed_from_cfg("checkin_requires_registration"), ephemeral=True
            )

        # 2) Must not do redundant action
        ci_role = discord.utils.get(self.guild.roles, name=CHECKED_IN_ROLE)
        is_ci   = ci_role in self.member.roles
        if self.label == "Check In" and is_ci:
            return await interaction.response.send_message(
                embed=embed_from_cfg("already_checked_in"), ephemeral=True
            )
        if self.label == "Check Out" and not is_ci:
            return await interaction.response.send_message(
                embed=embed_from_cfg("already_checked_out"), ephemeral=True
            )

        # 3) Perform the sheet + role toggle + channel-embed refresh
        await toggle_checkin_for_member(
            interaction,
            mark_checked_in_async if self.label == "Check In" else unmark_checked_in_async,
            "checked_in"  if self.label == "Check In" else "checked_out"
        )

        # 4) Finally, redraw the **DM** view so the two buttons re-enable/disable
        await interaction.message.edit(view=DMActionView(self.guild, self.member))

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
        # 1) Defer once immediately
        await interaction.response.defer(ephemeral=True)

        guild       = interaction.guild
        member      = interaction.user
        discord_tag = str(member)

        # 2) Attempt to wipe from sheet + cache
        try:
            ok = await unregister_user(discord_tag, guild_id=str(guild.id))
        except Exception as e:
            # unexpected error—log silently
            await log_error(
                interaction.client,
                guild,
                f"[UNREGISTER-ERROR] Guild={guild.id} User={discord_tag} Error={e}"
            )
            return await interaction.followup.send(
                embed=embed_from_cfg("unregister_fail"),
                ephemeral=True
            )

        if not ok:
            # wasn’t registered
            return await interaction.followup.send(
                embed=embed_from_cfg("unregister_not_registered"),
                ephemeral=True
            )

        # 3) Remove roles
        reg_role = discord.utils.get(guild.roles, name=REGISTERED_ROLE)
        ci_role  = discord.utils.get(guild.roles, name=CHECKED_IN_ROLE)
        to_remove = [r for r in (reg_role, ci_role) if r and r in member.roles]
        if to_remove:
            await member.remove_roles(*to_remove)

        # 4) Send confirmation
        await interaction.followup.send(
            embed=embed_from_cfg("unregister_success"),
            ephemeral=True
        )
        print(f"[UNREGISTER SUCCESS] Guild={guild.name}({guild.id}) User={discord_tag}")

        # 5) Refresh the public embeds
        chan_id, msg_id = get_persisted_msg(guild.id, "registration")
        if chan_id and msg_id:
            ch = guild.get_channel(chan_id)
            await update_registration_embed(ch, msg_id, guild)

        ci_chan, ci_msg = get_persisted_msg(guild.id, "checkin")
        if ci_chan and ci_msg:
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
        # permission guard
        if not has_allowed_role_from_interaction(interaction):
            embed = embed_from_cfg("permission_denied")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        guild       = interaction.guild
        reg_channel = interaction.channel
        guild_id    = str(guild.id)
        role        = "registered"

        # 1) show “resetting…” to the invoker
        resetting = embed_from_cfg("resetting", role=role, count="...", elapsed=0)
        await interaction.response.send_message(embed=resetting, ephemeral=True)

        # 2) actually clear the sheet & cache
        t0      = time.perf_counter()
        cleared = await reset_registered_roles_and_sheet(guild, reg_channel)
        elapsed = time.perf_counter() - t0

        # 3) delete all extra bot‐sent embeds (leave the pinned “live” one)
        main_chan_id, main_msg_id = get_persisted_msg(guild_id, "registration")
        async for msg in reg_channel.history(limit=100):
            if msg.author.bot and msg.id != main_msg_id and msg.embeds:
                try:
                    await msg.delete()
                except:
                    pass

        # 4) redraw the pinned registration embed
        from views import update_live_embeds
        await update_live_embeds(guild)

        # 5) send the “reset complete” confirmation
        complete = embed_from_cfg(
            "reset_complete",
            role=role.title(),
            count=cleared,
            elapsed=elapsed
        )
        await interaction.followup.send(embed=complete, ephemeral=True)

        # 6) refresh our in-memory cache to match
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

        # send a DM **with** the DMActionView
        dmmed = await send_reminder_dms(
            client=interaction.client,
            guild=guild,
            dm_embed=dm_embed,
            view_cls=DMActionView
        )

        # report back in-channel
        count = len(dmmed)
        users_list = "\n".join(dmmed) or "No users could be DM'd."
        public = embed_from_cfg("reminder_public", count=count, users=users_list)
        await interaction.followup.send(embed=public, ephemeral=True)

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
    def __init__(self, guild: discord.Guild):
        super().__init__(timeout=None)
        self.guild = guild

        # open?
        ci_ch    = discord.utils.get(guild.text_channels, name=CHECK_IN_CHANNEL)
        reg_role = discord.utils.get(guild.roles,        name=REGISTERED_ROLE)
        is_open  = bool(ci_ch and reg_role and ci_ch.overwrites_for(reg_role).view_channel)

        if is_open:
            self.add_item(ChannelCheckInButton())
            self.add_item(ChannelCheckOutButton())
            self.add_item(ToggleRegistrationButton())  # or a ToggleCheckInButton if you have one
        else:
            self.add_item(ResetRegistrationButton())
            self.add_item(ToggleRegistrationButton())

class RegistrationView(discord.ui.View):
    def __init__(self, embed_message_id: int | None, guild: discord.Guild):
        super().__init__(timeout=None)
        self.guild = guild

        # is open?
        reg_ch     = discord.utils.get(guild.text_channels, name=REGISTRATION_CHANNEL)
        angel_role = discord.utils.get(guild.roles,         name=ANGEL_ROLE)
        is_open    = bool(reg_ch and angel_role and reg_ch.overwrites_for(angel_role).view_channel)

        if is_open:
            self.add_item(RegisterButton())
            self.add_item(UnregisterButton())
            self.add_item(ToggleRegistrationButton())
        else:
            self.add_item(ResetRegistrationButton())
            self.add_item(ToggleRegistrationButton())

class DMActionView(discord.ui.View):
    """
    DM view for /gal actions: Register/Unregister & Check In/Out
    Always re-reads the latest sheet cache and channel permissions.
    """
    def __init__(self, guild: discord.Guild, member: discord.Member):
        super().__init__(timeout=None)
        self.guild  = guild
        self.member = member

        # ─── Is registration open? ────────────────────────────────────
        reg_ch     = discord.utils.get(guild.text_channels, name=REGISTRATION_CHANNEL)
        angel_role = discord.utils.get(guild.roles,         name=ANGEL_ROLE)
        reg_open   = bool(reg_ch and angel_role and reg_ch.overwrites_for(angel_role).view_channel)

        # ─── Is check-in open? ─────────────────────────────────────────
        ci_ch      = discord.utils.get(guild.text_channels, name=CHECK_IN_CHANNEL)
        reg_role   = discord.utils.get(guild.roles,         name=REGISTERED_ROLE)
        ci_open    = bool(ci_ch and reg_role and ci_ch.overwrites_for(reg_role).view_channel)

        # ─── Is the user currently registered? ────────────────────────
        is_registered = reg_role in member.roles

        # ─── Register / Unregister toggle ─────────────────────────────
        reg_btn = DMRegisterToggleButton(guild, member)
        reg_btn.disabled = not reg_open
        self.add_item(reg_btn)

        # ─── Check In / Check Out toggle ─────────────────────────────
        # always add the button but disable when not allowed
        ci_btn = DMCheckToggleButton(guild, member)
        ci_btn.disabled = not (ci_open and is_registered)
        self.add_item(ci_btn)

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
    # 1) Determine open vs. closed
    reg_ch     = discord.utils.get(guild.text_channels, name=REGISTRATION_CHANNEL)
    angel_role = discord.utils.get(guild.roles,         name=ANGEL_ROLE)
    is_open    = bool(reg_ch and angel_role and reg_ch.overwrites_for(angel_role).view_channel)

    # 2) Base embed
    key  = "registration" if is_open else "registration_closed"
    base = embed_from_cfg(key)
    msg  = await channel.fetch_message(msg_id)

    if not is_open:
        return await msg.edit(embed=base, view=RegistrationView(msg_id, guild))

    # 3) Gather registered users
    mode = get_event_mode_for_guild(str(guild.id))
    async with cache_lock:
        users = [
            (tag, tpl[1], tpl[4] if len(tpl) > 4 else "")
            for tag, tpl in sheet_cache["users"].items()
            if tpl[2]
        ]

    total_players = len(users)
    total_teams   = len({t or "No Team" for _, _, t in users}) if mode == "doubleup" else 0

    # 4) Build description header + close time + spacing
    desc = base.description or ""
    close_iso = get_schedule(guild.id, "registration_close")
    if close_iso:
        ts = int(datetime.fromisoformat(close_iso).timestamp())
        desc += f"\n⏰ Registration closes at <t:{ts}:F>"
    # always ensure three blank lines before the listing
    desc += "\n\n\n"

    # 5) Build listing lines
    lines: list[str] = []
    if mode == "doubleup":
        users.sort(key=lambda x: x[2].lower())
        for team, grp in groupby(users, key=lambda x: x[2] or "No Team"):
            members = list(grp)
            lines.append(f"👥 **{team}** ({len(members)})")
            for tag, ign, _ in members:
                lines.append(f"> 👤 {tag}  |  {ign}")
            lines.append("")  # blank line between teams
        if lines and not lines[-1].strip():
            lines.pop()
    else:
        for tag, ign, _ in users:
            lines.append(f"👤 {tag}  |  {ign}")

    # 6) Create the new embed
    embed = discord.Embed(
        title=base.title,
        description=desc + ("\n".join(lines) if lines else ""),
        color=base.color
    )

    # 7) Only set footer if at least one player has registered
    if total_players > 0:
        footer = f"👤 Players: {total_players}"
        if mode == "doubleup":
            footer += f" 👥 Teams: {total_teams}"
        embed.set_footer(text=footer)

    # 8) Render with the fresh view
    await msg.edit(embed=embed, view=RegistrationView(msg_id, guild))


async def update_checkin_embed(
    channel: discord.TextChannel,
    msg_id: int,
    guild: discord.Guild
):
    # 1) Is check-in open?
    ci_ch    = discord.utils.get(guild.text_channels, name=CHECK_IN_CHANNEL)
    reg_role = discord.utils.get(guild.roles,        name=REGISTERED_ROLE)
    is_open  = bool(ci_ch and reg_role and ci_ch.overwrites_for(reg_role).view_channel)

    # 2) Base embed
    key  = "checkin" if is_open else "checkin_closed"
    base = embed_from_cfg(key)

    # 3) Description header + optional close time + spacing
    desc = base.description or ""
    if is_open:
        close_iso = get_schedule(guild.id, "checkin_close")
        if close_iso:
            ts = int(datetime.fromisoformat(close_iso).timestamp())
            desc += f"\n⏰ Check-in closes at <t:{ts}:t>"
    desc += "\n\n\n"  # three blank lines

    # 4) Grab (discord_tag, tpl) pairs from cache
    async with cache_lock:
        entries = list(sheet_cache["users"].items())
        # entries: List[ (discord_tag, (row, ign, reg, ci, team, alt)) ]

    # 5) Filter registered & checked-in
    def is_true(v): return str(v).upper() == "TRUE"

    registered = [
        (tag, tpl) for tag, tpl in entries
        if is_true(tpl[2])
    ]
    checked_in = [
        (tag, tpl) for tag, tpl in entries
        if is_true(tpl[2]) and is_true(tpl[3])
    ]

    total_reg = len(registered)
    total_ci  = len(checked_in)

    mode      = get_event_mode_for_guild(str(guild.id))
    max_teams = len({tpl[4] or "<No Team>" for _, tpl in registered}) if mode == "doubleup" else 0
    ci_teams  = len({tpl[4] or "<No Team>" for _, tpl in checked_in})  if mode == "doubleup" else 0

    # 6) Footer only if at least one checked-in
    if total_ci > 0:
        footer = f"👤 Checked-In: {total_ci}/{total_reg}"
        if mode == "doubleup":
            footer += f" 👥 Teams: {ci_teams}/{max_teams}"
        base.set_footer(text=footer)

    # 7) Build listing lines
    lines: list[str] = []
    if mode == "doubleup" and checked_in:
        # Group by team name
        # Each entry is (tag, tpl)
        checked_in.sort(key=lambda item: (item[1][4] or "").lower())
        for team, grp in groupby(checked_in, key=lambda item: item[1][4] or "<No Team>"):
            members = list(grp)
            # Team header with bold name and checked-in count
            lines.append(f"👥 **{team}** ({len(members)})")
            # Each player line indented and formatted
            for tag, tpl in members:
                ign = tpl[1]
                lines.append(f"> 👤 {tag}  |  {ign}")
            lines.append("")  # blank line between teams
        if lines and not lines[-1].strip():
            lines.pop()
    elif checked_in:
        # Normal mode flat list
        for tag, tpl in checked_in:
            ign = tpl[1]
            lines.append(f"👤 {tag}  |  {ign}")

    # 8) Edit the embed message
    msg = await channel.fetch_message(msg_id)
    new_desc = desc + ("\n".join(lines) if lines else "")
    embed = discord.Embed(
        title=base.title,
        description=new_desc,
        color=base.color
    )
    # Preserve footer if set
    if base.footer.text:
        embed.set_footer(text=base.footer.text)
    await msg.edit(embed=embed, view=CheckInView(guild))