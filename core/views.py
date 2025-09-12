# core/views.py

from __future__ import annotations

import discord
from rapidfuzz import process, fuzz

from config import (
    embed_from_cfg, get_registered_role, get_checked_in_role, get_sheet_settings
)
from core.components_traditional import update_unified_channel
from core.persistence import (
    get_event_mode_for_guild, )
from helpers import (
    RoleManager, SheetOperations, Validators,
    ErrorHandler, sheet_helpers, ValidationError
)
from helpers.embed_helpers import log_error
from integrations.sheets import (
    find_or_register_user, get_sheet_for_guild, retry_until_successful, mark_checked_in_async, unmark_checked_in_async,
    unregister_user, cache_lock, sheet_cache
)




async def complete_registration_get_result(
        interaction: discord.Interaction,
        ign: str,
        pronouns: str,
        team_name: str | None,
        alt_igns: str,
        reg_modal: "RegistrationModal"
):
    """
    Complete user registration and return result dictionary instead of handling response.
    Returns: {'success': bool, 'embed': discord.Embed, 'view': discord.ui.View|None, 'ign': str, 'team_name': str|None}
    """
    # Import here to avoid circular import
    from utils.utils import hyperlink_lolchess_profile
    from helpers.waitlist_helpers import WaitlistManager

    # Note: Response should already be deferred by modal

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

    # 4) Get mode for context
    mode = get_event_mode_for_guild(gid)

    # 5) Check if user is already in waitlist (for updating their info)
    existing_waitlist_position = await WaitlistManager.get_waitlist_position(gid, discord_tag)

    # 6) Validate capacity using helper
    capacity_error = await Validators.validate_registration_capacity(
        gid, team_name, exclude_discord_tag=discord_tag
    )

    if capacity_error:
        # Check if it's a max teams error with available teams
        if capacity_error.embed_key == "max_teams_reached":
            teams_with_space = capacity_error.kwargs.get("teams_with_space", [])

            if teams_with_space:
                # Show dropdown for team selection
                embed = embed_from_cfg(
                    "max_teams_reached",
                    max_teams=capacity_error.kwargs.get("max_teams"),
                    teams_count=len(teams_with_space)
                )

                view = TeamSelectionView(
                    reg_modal, ign, pronouns, teams_with_space, alt_igns, team_name  # Pass team_name
                )

                return {
                    'success': False,
                    'embed': embed,
                    'view': view,
                    'ign': ign,
                    'team_name': team_name
                }
            else:
                # No teams with space, treat as full
                capacity_error = ValidationError("registration_full",
                                                 max_players=capacity_error.kwargs.get("max_players", 0))

        # Handle other capacity errors (registration_full, team_full)
        if capacity_error.embed_key == "registration_full":
            # Check for team similarity when adding to waitlist
            if mode == "doubleup" and team_name:
                similar_team = await WaitlistManager._find_similar_team(team_name, gid)
                if similar_team and similar_team.lower() != team_name.lower():
                    # Show similarity prompt for waitlist
                    similarity_embed = discord.Embed(
                        title="Similar Team Found",
                        description=f"The tournament is full, and you'll be added to the waitlist.\n\n"
                                    f"Did you mean team **{similar_team}**?\n\n"
                                    f"Click **Use Suggested** to join the waitlist with the existing team name, "
                                    f"or **Keep Mine** to use your entered team name.",
                        color=discord.Color.blurple()
                    )

                    # Create a special view for waitlist team choice
                    view = WaitlistTeamChoiceView(
                        guild, member, ign, pronouns, similar_team, team_name, alt_igns,
                        existing_waitlist_position,
                        from_management=hasattr(reg_modal, 'update_management_interface') and reg_modal.update_management_interface
                    )

                    return {
                        'success': False,
                        'embed': similarity_embed,
                        'view': view,
                        'ign': ign,
                        'team_name': team_name
                    }

            # Add or update waitlist entry
            if existing_waitlist_position:
                # Update their waitlist entry
                await WaitlistManager.update_waitlist_entry(
                    gid, discord_tag, ign, pronouns, team_name, alt_igns
                )

                # Update unified channel to reflect waitlist changes
                await update_unified_channel(guild)

                # Get max players for the embed
                cfg = get_sheet_settings(mode)
                max_players = cfg.get("max_players", 0)

                waitlist_embed = discord.Embed(
                    title="📋 Waitlist Updated",
                    description=f"Your waitlist information has been updated.\n\n"
                                f"You remain at position **#{existing_waitlist_position}** in the waitlist.",
                    color=discord.Color.blue()
                )
                return {
                    'success': False,
                    'embed': waitlist_embed,
                    'view': None,
                    'ign': ign,
                    'team_name': team_name
                }
            else:
                # Add to waitlist
                position = await WaitlistManager.add_to_waitlist(
                    guild, member, ign, pronouns, team_name, alt_igns
                )

                # Update unified channel to reflect waitlist changes
                await update_unified_channel(guild)

                # Get max players for the embed
                cfg = get_sheet_settings(mode)
                max_players = cfg.get("max_players", 0)

                waitlist_embed = embed_from_cfg(
                    "waitlist_added",
                    position=position,
                    max_players=max_players
                )
                return {
                    'success': False,
                    'embed': waitlist_embed,
                    'view': None,
                    'ign': ign,
                    'team_name': team_name
                }

        elif capacity_error.embed_key == "team_full":
            # Team is full - check if user should be added to waitlist
            # First check total capacity
            from helpers.sheet_helpers import SheetOperations
            total_registered = await SheetOperations.count_by_criteria(
                gid, registered=True
            )

            cfg = get_sheet_settings(mode)
            max_players = cfg.get("max_players", 0)

            # If we're at max capacity, add to waitlist
            if total_registered >= max_players:
                # Check for team similarity when adding to waitlist
                if mode == "doubleup" and team_name:
                    similar_team = await WaitlistManager._find_similar_team(team_name, gid)
                    if similar_team and similar_team.lower() != team_name.lower():
                        # Show similarity prompt for waitlist with team full context
                        similarity_embed = discord.Embed(
                            title="Team Full - Similar Team Found",
                            description=f"Team **{team_name}** is full, and the tournament is at capacity.\n"
                                        f"You'll be added to the waitlist.\n\n"
                                        f"Did you mean team **{similar_team}**?\n\n"
                                        f"Click **Use Suggested** to join the waitlist with the existing team name, "
                                        f"or **Keep Mine** to use your entered team name.",
                            color=discord.Color.blurple()
                        )

                        view = WaitlistTeamChoiceView(
                            guild, member, ign, pronouns, similar_team, team_name, alt_igns,
                            existing_waitlist_position,
                            from_management=hasattr(reg_modal, 'update_management_interface') and reg_modal.update_management_interface
                        )

                        return {
                            'success': False,
                            'embed': similarity_embed,
                            'view': view,
                            'ign': ign,
                            'team_name': team_name
                        }

                if existing_waitlist_position:
                    # Update waitlist
                    await WaitlistManager.update_waitlist_entry(
                        gid, discord_tag, ign, pronouns, team_name, alt_igns
                    )
                    
                    # Update unified channel to reflect waitlist changes
                    await update_unified_channel(guild)
                    
                    waitlist_embed = discord.Embed(
                        title="📋 Waitlist Updated",
                        description=f"Team **{team_name}** is full, and the tournament is at capacity.\n\n"
                                    f"Your waitlist information has been updated.\n"
                                    f"You remain at position **#{existing_waitlist_position}** in the waitlist.",
                        color=discord.Color.blue()
                    )
                else:
                    # Add to waitlist
                    position = await WaitlistManager.add_to_waitlist(
                        guild, member, ign, pronouns, team_name, alt_igns
                    )
                    
                    # Update unified channel to reflect waitlist changes
                    await update_unified_channel(guild)
                    
                    waitlist_embed = embed_from_cfg(
                        "waitlist_added",
                        position=position,
                        max_players=max_players
                    )

                return {
                    'success': False,
                    'embed': waitlist_embed,
                    'view': None,
                    'ign': ign,
                    'team_name': team_name
                }
            else:
                # Tournament not full but team is - show team full error
                return {
                    'success': False,
                    'embed': capacity_error.to_embed(),
                    'view': None,
                    'ign': ign,
                    'team_name': team_name
                }
        else:
            # Other capacity error
            return {
                'success': False,
                'embed': capacity_error.to_embed(),
                'view': None,
                'ign': ign,
                'team_name': team_name
            }

    try:
        # Remove from waitlist if they were on it (they're being registered now)
        await WaitlistManager.remove_from_waitlist(gid, discord_tag)

        # 7) Upsert user row in sheet
        row = await find_or_register_user(
            discord_tag,
            ign,
            guild_id=gid,
            team_name=(team_name if mode == "doubleup" else None),
            alt_igns=alt_igns,
            pronouns=pronouns
        )

        # Note: Alt IGNs, pronouns, and team are now handled by find_or_register_user
        # No need for separate sheet updates - they're already done and cached properly

        # 9) Assign role using RoleManager
        await RoleManager.add_role(member, get_registered_role())

        # 10) Hyperlink IGN
        await hyperlink_lolchess_profile(discord_tag, gid)

        # 11) Refresh embeds using helper - ALWAYS update main embed for registration
        await update_unified_channel(guild)

        # 12) Process waitlist to see if more people can be registered
        # This is important for team scenarios where one person registering
        # might open up a spot for their teammate on the waitlist
        await WaitlistManager.process_waitlist(guild)

        # 13) Send success embed
        ok_key = f"register_success_{mode}"
        success_embed = embed_from_cfg(
            ok_key,
            ign=ign,
            team_name=(team_name or "—")
        )

        print(f"[REGISTER SUCCESS] {discord_tag} in guild {guild.name}")

        # Return success result
        return {
            'success': True,
            'embed': success_embed,
            'view': None,
            'ign': ign,
            'team_name': team_name
        }

    except Exception as e:
        # Use error handler
        await ErrorHandler.handle_interaction_error(
            interaction, e, "Registration",
            f"Failed to complete registration. Please try again."
        )
        return {
            'success': False,
            'embed': embed_from_cfg("error"),
            'view': None,
            'ign': ign,
            'team_name': team_name
        }


async def complete_registration(
        interaction: discord.Interaction,
        ign: str,
        pronouns: str,
        team_name: str | None,
        alt_igns: str,
        reg_modal: "RegistrationModal"
):
    """
    Complete user registration and ALWAYS show result in management interface.
    """
    result = await complete_registration_get_result(
        interaction, ign, pronouns, team_name, alt_igns, reg_modal
    )
    
    from core.components_traditional import RegistrationManagementView, create_management_embed, get_confirmation_message
    from helpers.waitlist_helpers import WaitlistManager
    
    # Always maintain management interface with confirmation
    if result['success']:
        # Registration successful
        team_text = f" for team **{result['team_name']}**" if result.get('team_name') else ""
        confirmation = get_confirmation_message("registered", ign=result['ign'], team_text=team_text)
        mgmt_embed = create_management_embed(
            user_status="You are currently registered for this tournament",
            status_emoji="✅",
            confirmation_message=confirmation
        )
        mgmt_view = RegistrationManagementView(interaction.user, True, False)
        
    elif result.get('view'):
        # Special case: team selection, waitlist choice, etc. - let those views handle their own responses
        await interaction.edit_original_response(embed=result['embed'], view=result['view'])
        return
        
    else:
        # Registration failed - determine current state and show appropriate management interface
        guild_id = str(interaction.guild.id)
        discord_tag = str(interaction.user)
        
        # Check current user state
        is_registered = RoleManager.is_registered(interaction.user)
        waitlist_pos = await WaitlistManager.get_waitlist_position(guild_id, discord_tag)
        
        if is_registered:
            user_status = "You are currently registered for this tournament"
            status_emoji = "✅"
            mgmt_view = RegistrationManagementView(interaction.user, True, False)
        elif waitlist_pos:
            user_status = f"You are currently on the waitlist (position #{waitlist_pos})"
            status_emoji = "⏳"
            mgmt_view = RegistrationManagementView(interaction.user, False, True)
        else:
            user_status = "You are not registered for this tournament"
            status_emoji = "❌"
            mgmt_view = RegistrationManagementView(interaction.user, False, False)
        
        # Extract error message for confirmation
        if result['embed'].description:
            error_msg = result['embed'].description
        else:
            error_msg = result['embed'].title or "Registration failed"
        
        mgmt_embed = create_management_embed(
            user_status=user_status,
            status_emoji=status_emoji,
            confirmation_message=f"❌ {error_msg}"
        )
    
    # Always update to management interface
    await interaction.edit_original_response(embed=mgmt_embed, view=mgmt_view)


class SystemControlModal(discord.ui.Modal):
    """Modal for system controls."""

    def __init__(self, guild: discord.Guild):
        super().__init__(title="System Controls")
        self.guild = guild

        from core.persistence import persisted
        guild_data = persisted.get(str(guild.id), {})

        # Registration toggle
        self.reg_toggle = discord.ui.TextInput(
            label="Registration Status",
            placeholder="Type 'OPEN' or 'CLOSED'",
            default="OPEN" if guild_data.get("registration_open", False) else "CLOSED",
            required=True,
            max_length=6
        )
        self.add_item(self.reg_toggle)

        # Check-in toggle
        self.ci_toggle = discord.ui.TextInput(
            label="Check-In Status",
            placeholder="Type 'OPEN' or 'CLOSED'",
            default="OPEN" if guild_data.get("checkin_open", False) else "CLOSED",
            required=True,
            max_length=6
        )
        self.add_item(self.ci_toggle)

    async def on_submit(self, interaction: discord.Interaction):
        from core.persistence import persisted, save_persisted
        
        # Defer immediately since we'll update unified channel
        await interaction.response.defer(ephemeral=True)

        reg_open = self.reg_toggle.value.upper() == "OPEN"
        ci_open = self.ci_toggle.value.upper() == "OPEN"

        guild_id = str(self.guild.id)
        if guild_id not in persisted:
            persisted[guild_id] = {}

        persisted[guild_id]["registration_open"] = reg_open
        persisted[guild_id]["checkin_open"] = ci_open
        save_persisted(persisted)

        # Update the unified channel
        await update_unified_channel(self.guild)

        await interaction.followup.send(
            embed=discord.Embed(
                title="✅ System Updated",
                description=f"**Registration:** {'OPEN' if reg_open else 'CLOSED'}\n"
                            f"**Check-In:** {'OPEN' if ci_open else 'CLOSED'}",
                color=discord.Color.green()
            ),
            ephemeral=True
        )


class WaitlistTeamChoiceView(discord.ui.View):
    """View for choosing team name when adding to waitlist"""

    def __init__(self, guild, member, ign, pronouns, suggested_team, user_team, alt_igns, existing_position, from_management=False):
        super().__init__(timeout=60)
        self.guild = guild
        self.member = member
        self.ign = ign
        self.pronouns = pronouns
        self.suggested_team = suggested_team
        self.user_team = user_team
        self.alt_igns = alt_igns
        self.existing_position = existing_position
        self.from_management = from_management

    @discord.ui.button(label="Use Suggested", style=discord.ButtonStyle.success)
    async def use_suggested(self, interaction, button):
        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(view=self)

        # Add/update waitlist with suggested team
        from helpers.waitlist_helpers import WaitlistManager

        gid = str(self.guild.id)
        discord_tag = str(self.member)

        if self.existing_position:
            await WaitlistManager.update_waitlist_entry(
                gid, discord_tag, self.ign, self.pronouns, self.suggested_team, self.alt_igns
            )
            
            # Update unified channel to reflect waitlist changes
            await update_unified_channel(self.guild)
            
            embed = discord.Embed(
                title="📋 Waitlist Updated",
                description=f"Your waitlist information has been updated with team **{self.suggested_team}**.\n\n"
                            f"You remain at position **#{self.existing_position}** in the waitlist.",
                color=discord.Color.blue()
            )
            position = self.existing_position  # For management interface use
        else:
            position = await WaitlistManager.add_to_waitlist(
                self.guild, self.member, self.ign, self.pronouns, self.suggested_team, self.alt_igns
            )
            
            # Update unified channel to reflect waitlist changes
            await update_unified_channel(self.guild)
            
            cfg = get_sheet_settings(get_event_mode_for_guild(gid))
            max_players = cfg.get("max_players", 0)
            embed = embed_from_cfg(
                "waitlist_added",
                position=position,
                max_players=max_players
            )

        if self.from_management:
            # Stay in management interface with confirmation
            from core.components_traditional import create_management_embed, get_confirmation_message, RegistrationManagementView
            
            if self.existing_position:
                team_text = f" for team **{self.suggested_team}**" if self.suggested_team else ""
                confirmation = get_confirmation_message("waitlist_updated", ign=self.ign, team_text=team_text)
                user_status = f"You are currently on the waitlist (position #{self.existing_position})"
            else:
                team_text = f" for team **{self.suggested_team}**" if self.suggested_team else ""
                confirmation = get_confirmation_message("waitlist_added", ign=self.ign, team_text=team_text, position=position)
                user_status = f"You are currently on the waitlist (position #{position})"
                
            mgmt_embed = create_management_embed(
                user_status=user_status,
                status_emoji="⏳",
                confirmation_message=confirmation
            )
            mgmt_view = RegistrationManagementView(self.member, False, True)  # Waitlist view
            await interaction.edit_original_response(embed=mgmt_embed, view=mgmt_view)
        else:
            # Standard flow - create management interface with waitlist confirmation
            from core.components_traditional import create_management_embed, get_confirmation_message, RegistrationManagementView
            
            if self.existing_position:
                team_text = f" for team **{self.suggested_team}**" if self.suggested_team else ""
                confirmation = get_confirmation_message("waitlist_updated", ign=self.ign, team_text=team_text)
                user_status = f"You are currently on the waitlist (position #{self.existing_position})"
            else:
                team_text = f" for team **{self.suggested_team}**" if self.suggested_team else ""
                confirmation = get_confirmation_message("waitlist_added", ign=self.ign, team_text=team_text, position=position)
                user_status = f"You are currently on the waitlist (position #{position})"
                
            mgmt_embed = create_management_embed(
                user_status=user_status,
                status_emoji="⏳",
                confirmation_message=confirmation
            )
            mgmt_view = RegistrationManagementView(self.member, False, True)  # Waitlist view
            await interaction.edit_original_response(embed=mgmt_embed, view=mgmt_view)

    @discord.ui.button(label="Keep My Team Name", style=discord.ButtonStyle.secondary)
    async def keep_mine(self, interaction, button):
        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(view=self)

        # Add/update waitlist with user's team
        from helpers.waitlist_helpers import WaitlistManager

        gid = str(self.guild.id)
        discord_tag = str(self.member)

        if self.existing_position:
            await WaitlistManager.update_waitlist_entry(
                gid, discord_tag, self.ign, self.pronouns, self.user_team, self.alt_igns
            )
            
            # Update unified channel to reflect waitlist changes
            await update_unified_channel(self.guild)
            
            embed = discord.Embed(
                title="📋 Waitlist Updated",
                description=f"Your waitlist information has been updated with team **{self.user_team}**.\n\n"
                            f"You remain at position **#{self.existing_position}** in the waitlist.",
                color=discord.Color.blue()
            )
            position = self.existing_position  # For management interface use
        else:
            position = await WaitlistManager.add_to_waitlist(
                self.guild, self.member, self.ign, self.pronouns, self.user_team, self.alt_igns
            )
            
            # Update unified channel to reflect waitlist changes
            await update_unified_channel(self.guild)
            
            cfg = get_sheet_settings(get_event_mode_for_guild(gid))
            max_players = cfg.get("max_players", 0)
            embed = embed_from_cfg(
                "waitlist_added",
                position=position,
                max_players=max_players
            )

        if self.from_management:
            # Stay in management interface with confirmation
            from core.components_traditional import create_management_embed, get_confirmation_message, RegistrationManagementView
            
            # This is the "keep mine" button, so use user_team
            if self.existing_position:
                team_text = f" for team **{self.user_team}**" if self.user_team else ""
                confirmation = get_confirmation_message("waitlist_updated", ign=self.ign, team_text=team_text)
                user_status = f"You are currently on the waitlist (position #{self.existing_position})"
            else:
                team_text = f" for team **{self.user_team}**" if self.user_team else ""
                confirmation = get_confirmation_message("waitlist_added", ign=self.ign, team_text=team_text, position=position)
                user_status = f"You are currently on the waitlist (position #{position})"
                
            mgmt_embed = create_management_embed(
                user_status=user_status,
                status_emoji="⏳",
                confirmation_message=confirmation
            )
            mgmt_view = RegistrationManagementView(self.member, False, True)  # Waitlist view
            await interaction.edit_original_response(embed=mgmt_embed, view=mgmt_view)
        else:
            # Standard flow - create management interface with waitlist confirmation
            from core.components_traditional import create_management_embed, get_confirmation_message, RegistrationManagementView
            
            if self.existing_position:
                team_text = f" for team **{self.suggested_team}**" if self.suggested_team else ""
                confirmation = get_confirmation_message("waitlist_updated", ign=self.ign, team_text=team_text)
                user_status = f"You are currently on the waitlist (position #{self.existing_position})"
            else:
                team_text = f" for team **{self.suggested_team}**" if self.suggested_team else ""
                confirmation = get_confirmation_message("waitlist_added", ign=self.ign, team_text=team_text, position=position)
                user_status = f"You are currently on the waitlist (position #{position})"
                
            mgmt_embed = create_management_embed(
                user_status=user_status,
                status_emoji="⏳",
                confirmation_message=confirmation
            )
            mgmt_view = RegistrationManagementView(self.member, False, True)  # Waitlist view
            await interaction.edit_original_response(embed=mgmt_embed, view=mgmt_view)


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
        # Check if registration is open
        from core.persistence import persisted
        guild_data = persisted.get(str(self.guild.id), {})
        reg_open = guild_data.get("registration_open", False)

        if not reg_open:
            # Registration is closed, can't unregister
            await interaction.response.send_message(
                embed=embed_from_cfg("registration_closed"),
                ephemeral=True
            )
            return

        # Defer the response as ephemeral
        await interaction.response.defer(ephemeral=True, thinking=True)

        discord_tag = str(self.member)
        guild_id = str(self.guild.id)

        # Check if user is in waitlist
        from helpers.waitlist_helpers import WaitlistManager
        waitlist_position = await WaitlistManager.get_waitlist_position(guild_id, discord_tag)

        if waitlist_position:
            # User is in waitlist, remove them
            await WaitlistManager.remove_from_waitlist(guild_id, discord_tag)

            # Update the unified channel to reflect waitlist changes
            await update_unified_channel(self.guild)

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
            await RoleManager.remove_roles(self.member, [get_registered_role(), get_checked_in_role()])

            # Update embeds
            await update_unified_channel(self.guild)

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
                embed=embed_from_cfg("registration_required"),
                ephemeral=True
            )


# ─── DM CHECK-IN/OUT TOGGLE ──────────────────────────────────────

class DMCheckToggleButton(discord.ui.Button):
    def __init__(self, guild: discord.Guild, member: discord.Member):
        self.guild = guild
        self.member = member

        reg_role = discord.utils.get(guild.roles, name=get_registered_role())
        ci_role = discord.utils.get(guild.roles, name=get_checked_in_role())

        # Check if check-in is open
        from core.persistence import persisted
        guild_data = persisted.get(str(guild.id), {})
        ci_open = guild_data.get("checkin_open", False)

        is_reg = reg_role in member.roles
        is_ci = ci_role in member.roles

        label = "Check Out" if is_ci else "Check In"
        style = discord.ButtonStyle.danger if is_ci else discord.ButtonStyle.success
        super().__init__(
            label=label,
            style=style,
            custom_id=f"dm_citoggle_{guild.id}_{member.id}",
            disabled=not (ci_open and is_reg)
        )

    async def callback(self, interaction: discord.Interaction):
        # Check if check-in is open
        from core.persistence import persisted
        guild_data = persisted.get(str(self.guild.id), {})
        ci_open = guild_data.get("checkin_open", False)

        if not ci_open:
            # Check-in is closed
            await interaction.response.send_message(
                embed=embed_from_cfg("checkin_closed"),
                ephemeral=True
            )
            return

        # 1) Must be registered
        reg_role = discord.utils.get(self.guild.roles, name=get_registered_role())
        if reg_role not in self.member.roles:
            return await interaction.response.send_message(
                embed=embed_from_cfg("registration_required"), ephemeral=True
            )

        # 2) Must not do redundant action
        ci_role = discord.utils.get(self.guild.roles, name=get_checked_in_role())
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
        await interaction.response.defer(ephemeral=True, thinking=True)

        # 4) Perform the sheet update
        discord_tag = str(self.member)
        if self.label == "Check In":
            ok = await mark_checked_in_async(discord_tag, guild_id=str(self.guild.id))
            if ok:
                await RoleManager.add_role(self.member, get_checked_in_role())
                await interaction.followup.send(embed=embed_from_cfg("checked_in"), ephemeral=True)
            else:
                # Check if user is actually in the cache/sheet
                from integrations.sheets import sheet_cache, cache_lock
                async with cache_lock:
                    user_in_cache = discord_tag in sheet_cache.get("users", {})
                
                if not user_in_cache:
                    # User has registered role but isn't in cache/sheet - remove role and show error
                    await RoleManager.remove_roles(self.member, [get_registered_role(), get_checked_in_role()])
                    
                    error_embed = discord.Embed(
                        title="❌ Registration Data Not Found",
                        description="It looks like your registration data was not found in our system, but you had the registered role.\n\n"
                                   "**Your roles have been reset.** Please re-register for the tournament using the main channel.",
                        color=discord.Color.red()
                    )
                    error_embed.add_field(
                        name="What to do next",
                        value="1. Go back to the tournament channel\n"
                              "2. Click **Manage Registration**\n"
                              "3. Register again with your information",
                        inline=False
                    )
                    await interaction.followup.send(embed=error_embed, ephemeral=True)
                else:
                    await interaction.followup.send(embed=embed_from_cfg("error"), ephemeral=True)
        else:
            ok = await unmark_checked_in_async(discord_tag, guild_id=str(self.guild.id))
            if ok:
                await RoleManager.remove_role(self.member, get_checked_in_role())
                await interaction.followup.send(embed=embed_from_cfg("checked_out"), ephemeral=True)
            else:
                await interaction.followup.send(embed=embed_from_cfg("error"), ephemeral=True)

        # 5) Update the unified channel embed
        await update_unified_channel(self.guild)

        # 6) Update the DM view to refresh button states
        await interaction.message.edit(view=DMActionView(self.guild, self.member))


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

        # Check if this is from a management interface
        is_management_interface = hasattr(self, 'management_view')

        # Build the modal with prefilled data
        if user_data:
            # User is registered, use their sheet data
            modal = RegistrationModal(
                team_field=(mode == "doubleup"),
                default_ign=user_data["ign"],
                default_alt_igns=user_data["alt_ign"],
                default_team=user_data.get("team", ""),
                default_pronouns=user_data["pronouns"],
                update_management_interface=is_management_interface
            )
        elif waitlist_data:
            # User is in waitlist, use their waitlist data
            modal = RegistrationModal(
                team_field=(mode == "doubleup"),
                default_ign=waitlist_data["ign"],
                default_alt_igns=waitlist_data.get("alt_igns", ""),
                default_team=waitlist_data.get("team_name", ""),
                default_pronouns=waitlist_data.get("pronouns", ""),
                update_management_interface=is_management_interface
            )
        else:
            # New registration
            modal = RegistrationModal(
                team_field=(mode == "doubleup"),
                update_management_interface=is_management_interface
            )

        # Attach context
        modal.guild = interaction.guild
        modal.member = interaction.user
        
        # Store reference to the management view for updating the message
        if is_management_interface:
            modal.management_view = self.management_view

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
        await interaction.response.defer(ephemeral=True, thinking=True)

        guild = interaction.guild
        member = interaction.user
        discord_tag = str(member)
        guild_id = str(guild.id)

        from core.components_traditional import RegistrationManagementView, create_management_embed, get_confirmation_message
        from helpers.waitlist_helpers import WaitlistManager

        # Check if user is in waitlist
        waitlist_position = await WaitlistManager.get_waitlist_position(guild_id, discord_tag)

        if waitlist_position:
            # User is in waitlist, remove them
            await WaitlistManager.remove_from_waitlist(guild_id, discord_tag)
            
            # Update main embed after waitlist removal
            await update_unified_channel(guild)
            
            # Show confirmation in management interface
            confirmation = get_confirmation_message("waitlist_removed")
            mgmt_embed = create_management_embed(
                user_status="You are not registered for this tournament",
                status_emoji="❌",
                confirmation_message=confirmation
            )
            mgmt_view = RegistrationManagementView(interaction.user, False, False)
            await interaction.edit_original_response(embed=mgmt_embed, view=mgmt_view)
            return

        # Attempt to unregister from sheet
        ok = await unregister_user(discord_tag, guild_id=guild_id)

        if not ok:
            # Show error in management interface format
            mgmt_embed = create_management_embed(
                user_status="You are not registered for this tournament",
                status_emoji="❌",
                confirmation_message="❌ You are not currently registered for the tournament."
            )
            mgmt_view = RegistrationManagementView(interaction.user, False, False)
            await interaction.edit_original_response(embed=mgmt_embed, view=mgmt_view)
            return

        # Use RoleManager to remove roles
        await RoleManager.remove_roles(member, [get_registered_role(), get_checked_in_role()])

        # Use the embed helper to update all embeds
        await update_unified_channel(guild)

        # Process waitlist in case someone can be registered
        await WaitlistManager.process_waitlist(guild)

        # Show success confirmation in management interface
        confirmation = get_confirmation_message("unregistered")
        mgmt_embed = create_management_embed(
            user_status="You are not registered for this tournament",
            status_emoji="❌",
            confirmation_message=confirmation
        )
        mgmt_view = RegistrationManagementView(interaction.user, False, False)
        await interaction.edit_original_response(embed=mgmt_embed, view=mgmt_view)
        
        print(f"[UNREGISTER SUCCESS] Guild={guild.name}({guild.id}) User={discord_tag}")


class RegistrationModal(discord.ui.Modal):
    def __init__(
            self,
            *,
            team_field: bool = False,
            default_ign: str | None = None,
            default_alt_igns: str | None = None,
            default_team: str | None = None,
            default_pronouns: str | None = None,
            bypass_similarity: bool = False,
            update_management_interface: bool = False
    ):
        super().__init__(title="Register for the Event")
        self.bypass_similarity = bypass_similarity
        self.update_management_interface = update_management_interface

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
                max_length=20
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

        await interaction.response.defer(ephemeral=True)

        # Check if registration is open
        from core.persistence import persisted
        guild_data = persisted.get(guild_id, {})
        reg_open = guild_data.get("registration_open", False)

        if not reg_open:
            embed = embed_from_cfg("registration_closed")
            await interaction.edit_original_response(embed=embed, view=None)
            return

        try:
            if mode == "doubleup" and team_value and not getattr(self, "bypass_similarity", False):
                # Check for exact case-insensitive match first
                exact_match = None
                async with cache_lock:
                    for tag, tpl in sheet_cache["users"].items():
                        if str(tpl[2]).upper() == "TRUE" and len(tpl) > 4 and tpl[4]:
                            if tpl[4].lower() == team_value.lower() and tpl[4] != team_value:
                                exact_match = tpl[4]
                                break

                # If exact case-insensitive match found, use it without prompting
                if exact_match:
                    team_value = exact_match
                else:
                    # Otherwise check for fuzzy similarity
                    sheet = await get_sheet_for_guild(guild_id, "GAL Database")
                    team_col_raw = await retry_until_successful(sheet.col_values, 9)
                    user_team_value = team_value.strip().lower()

                    # Make the normalization case-insensitive
                    norm_to_original = {}
                    team_col = []
                    for t in team_col_raw[2:]:
                        if t and t.strip():
                            normalized = t.strip().lower()
                            if normalized != user_team_value:
                                team_col.append(normalized)
                                norm_to_original[normalized] = t.strip()

                    if team_col:  # Only check similarity if there are existing teams
                        result = process.extractOne(
                            user_team_value, team_col, scorer=fuzz.ratio, score_cutoff=80
                        )
                        suggested_team = norm_to_original[result[0]] if result else None

                        if suggested_team:
                            # Check if this is from management interface
                            if hasattr(self, 'update_management_interface') and self.update_management_interface:
                                # Use the modal's response to show team choice
                                await interaction.edit_original_response(
                                    embed=discord.Embed(
                                        title="Similar Team Found",
                                        description=f"Did you mean **{suggested_team}**?\n\n"
                                                    f"Click **Use Suggested** to use the located team name, or **Keep Mine** to register your entered team name.",
                                        color=discord.Color.blurple()
                                    ),
                                    view=TeamNameChoiceView(self, ign, pronouns, suggested_team, team_value)
                                )
                            else:
                                # Standard flow
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

            # Use the simplified complete_registration function which now always handles management interface
            await complete_registration(
                interaction,
                ign,
                pronouns,
                team_value,
                alt_igns,
                self
            )

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
    async def use_suggested(self, interaction, button):
        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(view=self)

        await complete_registration(
            interaction,
            self.ign,
            self.pronouns,
            self.suggested_team,
            self.reg_modal.alt_ign_input.value.strip(),
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
            self.reg_modal.alt_ign_input.value.strip(),
            self.reg_modal
        )


class TeamSelectionView(discord.ui.View):
    """View with dropdown for selecting existing teams with space."""

    def __init__(self, reg_modal, ign, pronouns, teams_with_space, alt_igns, team_name):
        super().__init__(timeout=60)
        self.reg_modal = reg_modal
        self.ign = ign
        self.pronouns = pronouns
        self.alt_igns = alt_igns
        self.team_name = team_name  # Store original team name
        self.selected_team = None

        # Add dropdown with available teams
        self.team_select = discord.ui.Select(
            placeholder="Choose a team to join...",
            options=[
                discord.SelectOption(label=team, value=team)
                for team in teams_with_space[:25]  # Discord limit is 25 options
            ]
        )
        self.team_select.callback = self.team_selected
        self.add_item(self.team_select)

        # Add waitlist button (green)
        self.waitlist_btn = discord.ui.Button(
            label="Add to Waitlist",
            style=discord.ButtonStyle.success
        )
        self.waitlist_btn.callback = self.waitlist_clicked
        self.add_item(self.waitlist_btn)

        # Add cancel button (red)
        self.cancel_btn = discord.ui.Button(
            label="Cancel",
            style=discord.ButtonStyle.danger
        )
        self.cancel_btn.callback = self.cancel_clicked
        self.add_item(self.cancel_btn)

    async def team_selected(self, interaction: discord.Interaction):
        """Handle team selection from dropdown."""
        self.selected_team = self.team_select.values[0]

        # Disable all items
        for item in self.children:
            item.disabled = True

        await interaction.response.edit_message(view=self)

        # Complete registration with selected team
        await complete_registration(
            interaction,
            self.ign,
            self.pronouns,
            self.selected_team,
            self.alt_igns,
            self.reg_modal
        )

    async def waitlist_clicked(self, interaction: discord.Interaction):
        """Handle waitlist button click."""
        from helpers.waitlist_helpers import WaitlistManager

        # Disable all items
        for item in self.children:
            item.disabled = True

        await interaction.response.edit_message(view=self)

        guild = self.reg_modal.guild if hasattr(self.reg_modal, 'guild') else interaction.guild
        member = self.reg_modal.member if hasattr(self.reg_modal, 'member') else interaction.user
        guild_id = str(guild.id)
        discord_tag = str(member)

        # Check if already in waitlist
        existing_position = await WaitlistManager.get_waitlist_position(guild_id, discord_tag)

        if existing_position:
            # Update waitlist entry
            await WaitlistManager.update_waitlist_entry(
                guild_id, discord_tag, self.ign, self.pronouns, self.team_name, self.alt_igns
            )

            # Update unified channel to reflect waitlist changes
            await update_unified_channel(guild)

            waitlist_embed = discord.Embed(
                title="📋 Waitlist Updated",
                description=f"Your waitlist information has been updated.\n\n"
                            f"You remain at position **#{existing_position}** in the waitlist.",
                color=discord.Color.blue()
            )
        else:
            # Add to waitlist
            position = await WaitlistManager.add_to_waitlist(
                guild, member, self.ign, self.pronouns, self.team_name, self.alt_igns
            )

            # Update unified channel to reflect waitlist changes
            await update_unified_channel(guild)

            mode = get_event_mode_for_guild(guild_id)
            cfg = get_sheet_settings(mode)
            max_players = cfg.get("max_players", 0)

            waitlist_embed = embed_from_cfg(
                "waitlist_added",
                position=position,
                max_players=max_players
            )

        # Check if from management interface
        if hasattr(self.reg_modal, 'update_management_interface') and self.reg_modal.update_management_interface:
            # Stay in management interface with confirmation
            from core.components_traditional import create_management_embed, get_confirmation_message, RegistrationManagementView
            
            if existing_position:
                team_text = f" for team **{self.team_name}**" if self.team_name else ""
                confirmation = get_confirmation_message("waitlist_updated", ign=self.ign, team_text=team_text)
                user_status = f"You are currently on the waitlist (position #{existing_position})"
            else:
                team_text = f" for team **{self.team_name}**" if self.team_name else ""
                confirmation = get_confirmation_message("waitlist_added", ign=self.ign, team_text=team_text, position=position)
                user_status = f"You are currently on the waitlist (position #{position})"
                
            mgmt_embed = create_management_embed(
                user_status=user_status,
                status_emoji="⏳",
                confirmation_message=confirmation
            )
            mgmt_view = RegistrationManagementView(interaction.user, False, True)  # Waitlist view
            await interaction.edit_original_response(embed=mgmt_embed, view=mgmt_view)
        else:
            # Standard flow - create management interface with waitlist confirmation
            from core.components_traditional import create_management_embed, get_confirmation_message, RegistrationManagementView
            
            team_text = f" for team **{self.team_name}**" if self.team_name else ""
            confirmation = get_confirmation_message("waitlist_added", ign=self.ign, team_text=team_text, position=position)
            user_status = f"You are currently on the waitlist (position #{position})"
                
            mgmt_embed = create_management_embed(
                user_status=user_status,
                status_emoji="⏳",
                confirmation_message=confirmation
            )
            mgmt_view = RegistrationManagementView(interaction.user, False, True)  # Waitlist view
            await interaction.edit_original_response(embed=mgmt_embed, view=mgmt_view)

    async def cancel_clicked(self, interaction: discord.Interaction):
        """Handle cancel button."""
        for item in self.children:
            item.disabled = True

        await interaction.response.edit_message(
            content="Registration cancelled.",
            embed=None,
            view=self
        )


class DMActionView(discord.ui.View):
    def __init__(self, guild: discord.Guild, member: discord.Member):
        super().__init__(timeout=3600)  # 1 hour timeout for DMs
        self.guild = guild
        self.member = member

        # Check if systems are open
        from core.persistence import persisted
        guild_data = persisted.get(str(guild.id), {})
        reg_open = guild_data.get("registration_open", False)
        ci_open = guild_data.get("checkin_open", False)

        reg_role = discord.utils.get(guild.roles, name=get_registered_role())
        is_registered = reg_role in member.roles

        if is_registered:
            unreg_btn = DMUnregisterButton(guild, member)
            unreg_btn.disabled = not reg_open  # Can only unregister when registration is open
            self.add_item(unreg_btn)

            ci_btn = DMCheckToggleButton(guild, member)
            ci_btn.disabled = not ci_open  # Can only check in/out when check-in is open
            self.add_item(ci_btn)

    async def on_timeout(self):
        """Disable buttons when DM view times out."""
        for item in self.children:
            item.disabled = True


class WaitlistRegistrationDMView(discord.ui.View):
    """Simple view for waitlist registration DM with channel link button."""
    
    def __init__(self, guild: discord.Guild):
        super().__init__(timeout=3600)  # 1 hour timeout for DMs
        self.guild = guild
        
        # Add channel button
        from config import get_unified_channel_name
        unified_channel_name = get_unified_channel_name()
        unified_channel = discord.utils.get(guild.text_channels, name=unified_channel_name)
        
        if unified_channel:
            channel_btn = discord.ui.Button(
                label="Go to Tournament Channel",
                style=discord.ButtonStyle.primary,
                emoji="🎫",
                url=f"https://discord.com/channels/{guild.id}/{unified_channel.id}"
            )
            self.add_item(channel_btn)
    
    async def on_timeout(self):
        """Disable buttons when DM view times out."""
        for item in self.children:
            item.disabled = True


class QuickRegisterView(discord.ui.View):
    """View with just a register button for error messages."""

    def __init__(self):
        super().__init__(timeout=60)
        self.add_item(RegisterButton(label="Register Now"))


async def update_live_embeds(guild):
    """Update all live embeds for a guild."""
    await update_unified_channel(guild)
