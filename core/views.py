# core/views.py
from __future__ import annotations

import logging
import time
from datetime import datetime
from itertools import groupby

import discord
from rapidfuzz import process, fuzz

from config import (
    embed_from_cfg, CHECK_IN_CHANNEL, REGISTRATION_CHANNEL,
    REGISTERED_ROLE, CHECKED_IN_ROLE, ANGEL_ROLE, get_sheet_settings
)
from core.persistence import (
    get_persisted_msg, set_persisted_msg,
    get_event_mode_for_guild, get_schedule,
)
from helpers import (
    RoleManager, ChannelManager, SheetOperations, Validators,
    ErrorHandler, EmbedHelper
)
from helpers.embed_helpers import log_error
from integrations.sheets import (
    find_or_register_user, get_sheet_for_guild, retry_until_successful, mark_checked_in_async, unmark_checked_in_async,
    unregister_user, refresh_sheet_cache, reset_checked_in_roles_and_sheet, cache_lock, sheet_cache,
    reset_registered_roles_and_sheet
)

from utils.utils import toggle_checkin_for_member


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
    # Import here to avoid circular import
    from utils.utils import hyperlink_lolchess_profile
    from helpers.waitlist_helpers import WaitlistManager

    # 1) Defer if not already
    if not interaction.response.is_done():
        await interaction.response.defer(ephemeral=True)

    # 2) Resolve context
    guild = getattr(reg_modal, "guild", None) or interaction.guild
    member = getattr(reg_modal, "member", None) or interaction.user
    discord_tag = str(member)
    gid = str(guild.id)

    # 2.5) Auto-capitalize pronouns - split by "/" and capitalize each part
    if pronouns:
        # Split by "/" and capitalize each part, then rejoin
        pronouns_parts = pronouns.split("/")
        pronouns = "/".join(part.strip().capitalize() for part in pronouns_parts)

    # 3) Console log inputs
    print(f"[REGISTER] Guild={guild.name}({gid}) "
          f"User={discord_tag} IGN={ign!r} Team={team_name!r} Alts={alt_igns!r}")

    # 4) Validate capacity using helper
    capacity_error = await Validators.validate_registration_capacity(
        gid, team_name, exclude_discord_tag=discord_tag
    )

    if capacity_error:
        # Check if it's a full registration error
        if capacity_error.embed_key == "registration_full":
            # Check if already in waitlist
            existing_position = await WaitlistManager.get_waitlist_position(gid, discord_tag)

            if existing_position:
                # Update their waitlist entry
                await WaitlistManager.update_waitlist_entry(
                    gid, discord_tag, ign, pronouns, team_name, alt_igns
                )

                # Get max players for the embed
                mode = get_event_mode_for_guild(gid)
                cfg = get_sheet_settings(mode)
                max_players = cfg.get("max_players", 0)

                waitlist_embed = discord.Embed(
                    title="📋 Waitlist Updated",
                    description=f"Your waitlist information has been updated.\n\n"
                                f"You remain at position **#{existing_position}** in the waitlist.",
                    color=discord.Color.blue()
                )
                return await interaction.followup.send(
                    embed=waitlist_embed,
                    ephemeral=True
                )
            else:
                # Add to waitlist
                position = await WaitlistManager.add_to_waitlist(
                    guild, member, ign, pronouns, team_name, alt_igns
                )

                # Get max players for the embed
                mode = get_event_mode_for_guild(gid)
                cfg = get_sheet_settings(mode)
                max_players = cfg.get("max_players", 0)

                waitlist_embed = embed_from_cfg(
                    "waitlist_added",
                    position=position,
                    max_players=max_players
                )
                return await interaction.followup.send(
                    embed=waitlist_embed,
                    ephemeral=True
                )
        else:
            # Other capacity error (like team full)
            return await interaction.followup.send(
                embed=capacity_error.to_embed(),
                ephemeral=True
            )

    try:
        # Remove from waitlist if they were on it
        await WaitlistManager.remove_from_waitlist(gid, discord_tag)

        # 5) Get mode
        mode = get_event_mode_for_guild(gid)

        # 6) Upsert user row
        row = await find_or_register_user(
            discord_tag,
            ign,
            guild_id=gid,
            team_name=(team_name if mode == "doubleup" else None)
        )

        # 7) Update sheet cells using helper
        updates = {
            get_sheet_settings(mode)['pronouns_col']: pronouns
        }
        if alt_igns:
            updates[get_sheet_settings(mode)['alt_ign_col']] = alt_igns
        if mode == "doubleup" and team_name:
            updates[get_sheet_settings(mode)['team_col']] = team_name

        await SheetOperations.batch_update_cells(gid, updates, row)

        # 8) Assign role using RoleManager
        await RoleManager.add_role(member, REGISTERED_ROLE)

        # 9) Refresh embeds using helper
        await EmbedHelper.update_all_guild_embeds(guild)

        # 10) Send success embed
        ok_key = f"register_success_{mode}"
        success_embed = embed_from_cfg(
            ok_key,
            ign=ign,
            team_name=(team_name or "–")
        )
        await interaction.followup.send(embed=success_embed, ephemeral=True)

        # 11) Hyperlink IGN
        await hyperlink_lolchess_profile(discord_tag, gid)

        print(f"[REGISTER SUCCESS] {discord_tag} in guild {guild.name}")

    except Exception as e:
        # Use error handler
        await ErrorHandler.handle_interaction_error(
            interaction, e, "Registration",
            f"Failed to complete registration. Please try again."
        )


class ChannelCheckInButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="Check In",
            style=discord.ButtonStyle.success,
            custom_id="channel_checkin_btn"
        )

    @ErrorHandler.wrap_callback("Check-In")
    async def callback(self, interaction: discord.Interaction):
        member = interaction.user
        guild = interaction.guild

        print(f"[CHECK-IN] Guild={guild.name}({guild.id}) User={member}")

        # Use validators instead of manual checking
        validations = [
            Validators.validate_registration_status(member, require_registered=True),
            Validators.validate_checkin_status(member, require_not_checked_in=True)
        ]

        if not await Validators.validate_and_respond(interaction, *validations):
            return

        # Perform check-in using the existing helper
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

# ─── DM UNREGISTER BUTTON ──────────────────────────────

class DMUnregisterButton(discord.ui.Button):
    """DM button for unregistering only"""

    def __init__(self, guild: discord.Guild, member: discord.Member):
        super().__init__(
            label="Unregister",
            style=discord.ButtonStyle.danger,
            custom_id=f"dm_unreg_{guild.id}_{member.id}"
        )
        self.guild = guild
        self.member = member

    async def callback(self, interaction: discord.Interaction):
        # Check if registration channel is open
        reg_channel = discord.utils.get(self.guild.text_channels, name=REGISTRATION_CHANNEL)
        angel_role = discord.utils.get(self.guild.roles, name=ANGEL_ROLE)

        if reg_channel and angel_role:
            overwrites = reg_channel.overwrites_for(angel_role)
            if not overwrites.view_channel:
                # Channel is closed, can't unregister
                await interaction.response.send_message(
                    embed=embed_from_cfg("registration_closed"),
                    ephemeral=True
                )
                return

        # Defer the response as ephemeral
        await interaction.response.defer(ephemeral=True)

        discord_tag = str(self.member)
        guild_id = str(self.guild.id)

        # Check if user is in waitlist
        from helpers.waitlist_helpers import WaitlistManager
        waitlist_position = await WaitlistManager.get_waitlist_position(guild_id, discord_tag)

        if waitlist_position:
            # User is in waitlist, remove them
            await WaitlistManager.remove_from_waitlist(guild_id, discord_tag)

            # Send ephemeral success message
            await interaction.followup.send(
                embed=discord.Embed(
                    title="✅ Removed from Waitlist",
                    description=f"You have been removed from the waitlist (you were position #{waitlist_position}).",
                    color=discord.Color.green()
                ),
                ephemeral=True
            )

            # Remove the view from the original message
            await interaction.message.edit(view=None)
            return

        ok = await unregister_user(discord_tag, guild_id=guild_id)
        if ok:
            # remove any roles
            await RoleManager.remove_roles(self.member, [REGISTERED_ROLE, CHECKED_IN_ROLE])

            # Update embeds
            await EmbedHelper.update_all_guild_embeds(self.guild)

            # Check waitlist and auto-register if someone is waiting
            await WaitlistManager.process_waitlist(self.guild)

            # Send ephemeral success message
            await interaction.followup.send(
                embed=embed_from_cfg("unregister_success"),
                ephemeral=True
            )

            # Remove the view from the original message (keep the embed)
            await interaction.message.edit(view=None)
        else:
            # Send error as ephemeral
            await interaction.followup.send(
                embed=embed_from_cfg("unregister_not_registered"),
                ephemeral=True
            )

# ─── DM CHECK-IN/OUT TOGGLE ──────────────────────────────────────

class DMCheckToggleButton(discord.ui.Button):
    def __init__(self, guild: discord.Guild, member: discord.Member):
        self.guild = guild
        self.member = member

        reg_role = discord.utils.get(guild.roles, name=REGISTERED_ROLE)
        ci_role = discord.utils.get(guild.roles, name=CHECKED_IN_ROLE)
        ci_ch = discord.utils.get(guild.text_channels, name=CHECK_IN_CHANNEL)
        is_open = bool(ci_ch and ci_ch.overwrites_for(reg_role).view_channel)
        is_reg = reg_role in member.roles
        is_ci = ci_role in member.roles

        label = "Check Out" if is_ci else "Check In"
        style = discord.ButtonStyle.danger if is_ci else discord.ButtonStyle.success
        super().__init__(
            label=label,
            style=style,
            custom_id=f"dm_citoggle_{guild.id}_{member.id}",
            disabled=not (is_open and is_reg)
        )

    async def callback(self, interaction: discord.Interaction):
        # Check if check-in channel is open
        ci_ch = discord.utils.get(self.guild.text_channels, name=CHECK_IN_CHANNEL)
        reg_role = discord.utils.get(self.guild.roles, name=REGISTERED_ROLE)

        if ci_ch and reg_role:
            overwrites = ci_ch.overwrites_for(reg_role)
            if not overwrites.view_channel:
                # Channel is closed
                await interaction.response.send_message(
                    embed=embed_from_cfg("checkin_closed"),
                    ephemeral=True
                )
                return

        # 1) Must be registered
        if reg_role not in self.member.roles:
            return await interaction.response.send_message(
                embed=embed_from_cfg("checkin_requires_registration"), ephemeral=True
            )

        # 2) Must not do redundant action
        ci_role = discord.utils.get(self.guild.roles, name=CHECKED_IN_ROLE)
        is_ci = ci_role in self.member.roles
        if self.label == "Check In" and is_ci:
            return await interaction.response.send_message(
                embed=embed_from_cfg("already_checked_in"), ephemeral=True
            )
        if self.label == "Check Out" and not is_ci:
            return await interaction.response.send_message(
                embed=embed_from_cfg("already_checked_out"), ephemeral=True
            )

        # 3) Defer the response before doing async operations
        await interaction.response.defer(ephemeral=True)

        # 4) Perform the sheet update
        discord_tag = str(self.member)
        if self.label == "Check In":
            ok = await mark_checked_in_async(discord_tag, guild_id=str(self.guild.id))
            if ok:
                await RoleManager.add_role(self.member, CHECKED_IN_ROLE)
                await interaction.followup.send(embed=embed_from_cfg("checked_in"), ephemeral=True)
            else:
                await interaction.followup.send(embed=embed_from_cfg("error"), ephemeral=True)
        else:
            ok = await unmark_checked_in_async(discord_tag, guild_id=str(self.guild.id))
            if ok:
                await RoleManager.remove_role(self.member, CHECKED_IN_ROLE)
                await interaction.followup.send(embed=embed_from_cfg("checked_out"), ephemeral=True)
            else:
                await interaction.followup.send(embed=embed_from_cfg("error"), ephemeral=True)

        # 5) Update the channel embed
        await EmbedHelper.update_persisted_embed(
            self.guild,
            "checkin",
            lambda ch, mid, g: update_checkin_embed(ch, mid, g),
            "checkin update"
        )

        # 6) Update the DM view to refresh button states (but don't replace the whole message)
        # Just update the view without changing the embed
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
        if not RoleManager.has_allowed_role_from_interaction(interaction):
            embed = embed_from_cfg("permission_denied")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        # Count how many will be cleared
        checked_in_role = discord.utils.get(interaction.guild.roles, name=CHECKED_IN_ROLE)
        cleared_count = len(checked_in_role.members) if checked_in_role else 0

        # Show resetting message
        embed_start = embed_from_cfg("resetting", count=cleared_count, role="checked-in")
        await interaction.followup.send(embed=embed_start, ephemeral=True)

        start_time = time.perf_counter()

        # Clear the sheet and roles
        check_in_channel = discord.utils.get(interaction.guild.text_channels, name=CHECK_IN_CHANNEL)
        actual_cleared = await reset_checked_in_roles_and_sheet(interaction.guild, check_in_channel)

        # Remove checked-in role from all members
        if checked_in_role:
            for member in checked_in_role.members:
                await member.remove_roles(checked_in_role)

        end_time = time.perf_counter()
        elapsed = end_time - start_time

        # Send completion message
        embed_done = embed_from_cfg("reset_complete", role="Check-in", count=actual_cleared, elapsed=elapsed)
        await interaction.followup.send(embed=embed_done, ephemeral=True)

        # Update embeds and refresh cache
        await update_live_embeds(interaction.guild)
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
        if not RoleManager.has_allowed_role_from_interaction(interaction):
            embed = embed_from_cfg("permission_denied")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        from utils.utils import toggle_persisted_channel
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

    @ErrorHandler.wrap_callback("Registration")
    async def callback(self, interaction: discord.Interaction):
        guild_id = str(interaction.guild.id)
        mode = get_event_mode_for_guild(guild_id)
        member = interaction.user
        discord_tag = str(member)

        # Check if user is in waitlist
        from helpers.waitlist_helpers import WaitlistManager
        waitlist_data = await WaitlistManager.get_waitlist_entry(guild_id, discord_tag)

        # Get user data using the helper (prioritize sheet data over waitlist)
        user_data = await SheetOperations.get_user_data(discord_tag, guild_id)

        # Build the modal with prefilled data
        if user_data:
            # User is registered, use their sheet data
            modal = RegistrationModal(
                team_field=(mode == "doubleup"),
                default_ign=user_data["ign"],
                default_alt_igns=user_data["alt_ign"],
                default_team=user_data.get("team", ""),
                default_pronouns=user_data["pronouns"]
            )
        elif waitlist_data:
            # User is in waitlist, use their waitlist data
            modal = RegistrationModal(
                team_field=(mode == "doubleup"),
                default_ign=waitlist_data["ign"],
                default_alt_igns=waitlist_data.get("alt_igns", ""),
                default_team=waitlist_data.get("team_name", ""),
                default_pronouns=waitlist_data.get("pronouns", "")
            )
        else:
            # New registration
            modal = RegistrationModal(team_field=(mode == "doubleup"))

        # Attach context
        modal.guild = interaction.guild
        modal.member = interaction.user

        # Show the modal
        await interaction.response.send_modal(modal)


class UnregisterButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="Unregister",
            style=discord.ButtonStyle.danger,
            custom_id="unregister_btn"
        )

    @ErrorHandler.wrap_callback("Unregister")
    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        guild = interaction.guild
        member = interaction.user
        discord_tag = str(member)
        guild_id = str(guild.id)

        # Check if user is in waitlist
        from helpers.waitlist_helpers import WaitlistManager
        waitlist_position = await WaitlistManager.get_waitlist_position(guild_id, discord_tag)

        if waitlist_position:
            # User is in waitlist, remove them
            await WaitlistManager.remove_from_waitlist(guild_id, discord_tag)
            await interaction.followup.send(
                embed=discord.Embed(
                    title="✅ Removed from Waitlist",
                    description=f"You have been removed from the waitlist (you were position #{waitlist_position}).",
                    color=discord.Color.green()
                ),
                ephemeral=True
            )
            return

        # Attempt to unregister from sheet
        ok = await unregister_user(discord_tag, guild_id=guild_id)

        if not ok:
            return await interaction.followup.send(
                embed=embed_from_cfg("unregister_not_registered"),
                ephemeral=True
            )

        # Use RoleManager to remove roles
        await RoleManager.remove_roles(member, [REGISTERED_ROLE, CHECKED_IN_ROLE])

        # Send confirmation
        await interaction.followup.send(
            embed=embed_from_cfg("unregister_success"),
            ephemeral=True
        )
        print(f"[UNREGISTER SUCCESS] Guild={guild.name}({guild.id}) User={discord_tag}")

        # Use the embed helper to update all embeds
        await EmbedHelper.update_all_guild_embeds(guild)

        # Process waitlist in case someone can be registered
        await WaitlistManager.process_waitlist(guild)


class ToggleRegistrationButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="Toggle Registration Channel",
            style=discord.ButtonStyle.primary,
            emoji="🔓",
            custom_id="toggle_registration_btn"
        )

    async def callback(self, interaction: discord.Interaction):
        if not RoleManager.has_allowed_role_from_interaction(interaction):
            embed = embed_from_cfg("permission_denied")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        from utils.utils import toggle_persisted_channel
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
        if not RoleManager.has_allowed_role_from_interaction(interaction):
            embed = embed_from_cfg("permission_denied")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        guild = interaction.guild
        reg_channel = interaction.channel
        guild_id = str(guild.id)
        role = "registered"

        # 1) show "resetting…" to the invoker
        registered_role = discord.utils.get(guild.roles, name=REGISTERED_ROLE)
        checked_in_role = discord.utils.get(guild.roles, name=CHECKED_IN_ROLE)

        # Count registered members
        cleared_count = len(registered_role.members) if registered_role else 0

        resetting = embed_from_cfg("resetting", role=role, count=cleared_count)
        await interaction.response.send_message(embed=resetting, ephemeral=True)

        # 2) actually clear the sheet & cache
        t0 = time.perf_counter()
        cleared = await reset_registered_roles_and_sheet(guild, reg_channel)

        # 3) Remove roles from all members
        if registered_role:
            for member in registered_role.members:
                roles_to_remove = [registered_role]
                if checked_in_role and checked_in_role in member.roles:
                    roles_to_remove.append(checked_in_role)
                await member.remove_roles(*roles_to_remove)

        # 4) Clear the waitlist for this guild
        from helpers.waitlist_helpers import WaitlistManager
        all_data = WaitlistManager._load_waitlist_data()
        if guild_id in all_data:
            all_data[guild_id]["waitlist"] = []
            WaitlistManager._save_waitlist_data(all_data)

        elapsed = time.perf_counter() - t0

        # 5) delete all extra bot‐sent embeds (leave the pinned "live" one)
        main_chan_id, main_msg_id = get_persisted_msg(guild_id, "registration")
        async for msg in reg_channel.history(limit=100):
            if msg.author.bot and msg.id != main_msg_id and msg.embeds:
                try:
                    await msg.delete()
                except:
                    pass

        # 6) redraw the pinned registration embed
        await update_live_embeds(guild)

        # 7) send the "reset complete" confirmation
        complete = embed_from_cfg(
            "reset_complete",
            role=role.title(),
            count=cleared,
            elapsed=elapsed
        )
        await interaction.followup.send(embed=complete, ephemeral=True)

        # 8) refresh our in-memory cache to match
        await refresh_sheet_cache(bot=interaction.client)


class ReminderButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="Send Reminders",
            style=discord.ButtonStyle.primary,
            emoji="📨",
            custom_id="reminder_btn"
        )

    async def callback(self, interaction: discord.Interaction):
        # Check permissions
        if not RoleManager.has_allowed_role_from_interaction(interaction):
            return await interaction.response.send_message(
                embed=embed_from_cfg("permission_denied"),
                ephemeral=True
            )

        await interaction.response.defer(ephemeral=True)

        # Send reminders to unchecked-in users
        dm_embed = embed_from_cfg("reminder_dm")
        guild = interaction.guild

        from utils.utils import send_reminder_dms
        dmmed = await send_reminder_dms(
            client=interaction.client,
            guild=guild,
            dm_embed=dm_embed,
            view_cls=DMActionView
        )

        # Report results
        count = len(dmmed)
        users_list = "\n".join(dmmed) if dmmed else "No users could be DM'd."
        result_embed = embed_from_cfg("reminder_public", count=count, users=users_list)
        await interaction.followup.send(embed=result_embed, ephemeral=True)


class RegistrationModal(discord.ui.Modal):
    def __init__(
            self,
            *,
            team_field: bool = False,
            default_ign: str | None = None,
            default_alt_igns: str | None = None,
            default_team: str | None = None,
            default_pronouns: str | None = None,
            bypass_similarity: bool = False
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

        # Team Name (doubleup only) - WITH 20 CHARACTER LIMIT
        self.team_input = None
        if team_field:
            self.team_input = discord.ui.TextInput(
                label="Team Name",
                placeholder="Your Team Name (max 20 characters)",
                required=True,
                default=default_team or "",
                max_length=20  # ADD THIS LINE
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

        # AUTO-CAPITALIZE PRONOUNS - split by "/" and capitalize each part
        if self.pronouns_input.value:
            pronouns_parts = self.pronouns_input.value.split("/")
            pronouns = "/".join(part.strip().capitalize() for part in pronouns_parts)
        else:
            pronouns = ""

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

        # Check if open
        ci_ch = discord.utils.get(guild.text_channels, name=CHECK_IN_CHANNEL)
        reg_role = discord.utils.get(guild.roles, name=REGISTERED_ROLE)
        is_open = bool(ci_ch and reg_role and ci_ch.overwrites_for(reg_role).view_channel)

        # Add buttons based on state
        if is_open:
            self.add_item(ChannelCheckInButton())
            self.add_item(ChannelCheckOutButton())
            self.add_item(ReminderButton())
            self.add_item(ToggleCheckInButton())
        else:
            self.add_item(ResetCheckInsButton())
            self.add_item(ToggleCheckInButton())

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
    DM view for /gal actions: Unregister & Check In/Out only
    """
    def __init__(self, guild: discord.Guild, member: discord.Member):
        super().__init__(timeout=None)
        self.guild  = guild
        self.member = member

        # ─── Is check-in open? ─────────────────────────────────────────
        ci_ch      = discord.utils.get(guild.text_channels, name=CHECK_IN_CHANNEL)
        reg_role   = discord.utils.get(guild.roles, name=REGISTERED_ROLE)
        ci_open    = bool(ci_ch and reg_role and ci_ch.overwrites_for(reg_role).view_channel)

        # ─── Is the user currently registered? ────────────────────────
        is_registered = reg_role in member.roles

        # Only show buttons if user is registered
        if is_registered:
            # ─── Unregister button ─────────────────────────────
            unreg_btn = DMUnregisterButton(guild, member)
            self.add_item(unreg_btn)

            # ─── Check In / Check Out toggle ─────────────────────────────
            ci_btn = DMCheckToggleButton(guild, member)
            ci_btn.disabled = not ci_open
            self.add_item(ci_btn)

class PersistentRegisteredListView(discord.ui.View):
    def __init__(self, guild):
        super().__init__(timeout=None)
        self.add_item(ReminderButton())

async def update_live_embeds(guild):
    """Update all live embeds for a guild."""
    await EmbedHelper.update_all_guild_embeds(guild)


async def update_registration_embed(
        channel: discord.TextChannel,
        msg_id: int,
        guild: discord.Guild
):
    # 1) Determine open vs. closed using ChannelManager
    is_open = ChannelManager.get_channel_state(guild)['registration_open']

    # 2) Base embed
    key = "registration" if is_open else "registration_closed"
    base = embed_from_cfg(key)

    try:
        msg = await channel.fetch_message(msg_id)
    except:
        logging.error(f"Could not fetch registration message {msg_id}")
        return

    if not is_open:
        # When closed, just show the closed embed without user list
        return await msg.edit(embed=base, view=RegistrationView(msg_id, guild))

    # 3) Get users and build lines using helpers
    mode = get_event_mode_for_guild(str(guild.id))
    users = await SheetOperations.get_all_registered_users(str(guild.id))

    total_players = len(users)
    total_teams = len({t for _, _, t in users if t}) if mode == "doubleup" else 0

    # 4) Build description
    desc = base.description or ""
    close_iso = get_schedule(guild.id, "registration_close")
    if close_iso:
        ts = int(datetime.fromisoformat(close_iso).timestamp())
        desc += f"\n⏰ Registration closes at <t:{ts}:F>"
    desc += "\n\n\n"

    # 5) Use EmbedHelper to build lines
    lines = EmbedHelper.build_registration_list_lines(users, mode)

    # 6) Create the new embed
    embed = discord.Embed(
        title=base.title,
        description=desc + ("\n".join(lines) if lines else ""),
        color=base.color
    )

    # 7) Set footer
    if total_players > 0:
        footer = f"👤 Players: {total_players}"
        if mode == "doubleup":
            footer += f" 👥 Teams: {total_teams}"
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

    try:
        msg = await channel.fetch_message(msg_id)
    except:
        logging.error(f"Could not fetch check-in message {msg_id}")
        return

    # 3) If closed, don't show the player list
    if not is_open:
        # Just show the closed message without any player list
        embed = discord.Embed(
            title=base.title,
            description=base.description or "",
            color=base.color
        )
        return await msg.edit(embed=embed, view=CheckInView(guild))

    # 4) When open, show the player list
    desc = base.description or ""
    close_iso = get_schedule(guild.id, "checkin_close")
    if close_iso:
        ts = int(datetime.fromisoformat(close_iso).timestamp())
        desc += f"\n⏰ Check-in closes at <t:{ts}:t>"
    desc += "\n\n\n"  # three blank lines

    # 5) Grab checked-in users
    async with cache_lock:
        entries = list(sheet_cache["users"].items())

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

    # 6) Build listing lines
    lines = EmbedHelper.build_checkin_list_lines(checked_in, mode)

    # 7) Create the embed
    new_desc = desc + ("\n".join(lines) if lines else "")
    embed = discord.Embed(
        title=base.title,
        description=new_desc,
        color=base.color
    )

    # 8) Footer only if at least one checked-in
    if total_ci > 0:
        footer = f"👤 Checked-In: {total_ci}/{total_reg}"
        if mode == "doubleup":
            footer += f" 👥 Teams: {ci_teams}/{max_teams}"
        embed.set_footer(text=footer)

    # Create view
    view = CheckInView(guild)

    # Remove reminder button if everyone is checked in
    if total_reg > 0 and total_ci == total_reg:
        new_view = discord.ui.View(timeout=None)
        for item in view.children:
            if not isinstance(item, ReminderButton):
                new_view.add_item(item)
        view = new_view

    await msg.edit(embed=embed, view=view)