# GAL Discord Bot Commands Guide

This guide provides comprehensive documentation for all Guardian Angel League Discord bot commands and their usage.

## Command Prefix

All commands use the `/` prefix followed by `gal` and the command name:
```
/gal <command>
```

## Available Commands

### 🔧 Tournament Management

#### `/gal toggle`
Toggles between registration and check-in channels.

**Usage**: `/gal toggle`

**Permissions**: Admin, Moderator, GAL Helper

**Effects**:
- If registration is open → Opens check-in channel
- If check-in is open → Opens registration channel
- Updates event mode accordingly
- Sends notification messages

**Example**:
```
/gal toggle
```

#### `/gal event`
View or set the current event mode for the tournament.

**Usage**:
```
/gal event                     # View current mode
/gal event mode:normal        # Set to normal mode
/gal event mode:doubleup    # Set to doubleup mode
```

**Permissions**: Admin, Moderator, GAL Helper

**Modes**:
- `normal`: Standard tournament (solo queue)
- `doubleup`: Double-up tournament (team queue)

**Example**:
```
/gal event mode:normal
```

#### `/gal config`
Manage bot configuration including editing, downloading, uploading, and reloading settings.

**Usage**:
```
/gal config action:edit           # Edit configuration
/gal config action:download       # Download current config
/gal config action:upload          # Upload configuration file
/gal config action:reload         # Reload configuration
```

**Permissions**: Admin only

**Actions**:
- `edit`: Open configuration editor dialog
- `download`: Get current configuration file
- `upload`: Upload new configuration file
- `reload`: Reload configuration from disk

### 📊 Registration & Data

#### `/gal registeredlist`
Display the current registration list with all registered users.

**Usage**: `/gal registeredlist`

**Permissions**: Admin, Moderator, GAL Helper

**Information Displayed**:
- Player names and IGNs
- Registration timestamps
- Team information (if doubleup mode)
- Total registration count

#### `/gal cache`
Force refresh of cached data from Google Sheets.

**Usage**: `/gal cache`

**Permissions**: Admin, Moderator, GAL Helper

**Effects**:
- Updates user data from Google Sheets
- Clears expired cache entries
- Reports update statistics
- Improves data accuracy

#### `/gal reminder`
Send reminder DMs to all users who are registered but not checked in.

**Usage**: `/gal reminder`

**Permissions**: Admin, Moderator, GAL Helper

**Effects**:
- Sends DM reminder to unchecked-in users
- Includes direct link to tournament channel
- Reports how many users received reminders
- Encourages timely check-ins

### 🆘 Help & Information

#### `/gal help`
Display comprehensive help information for all bot commands.

**Usage**: `/gal help`

**Permissions**: Available to all users

**Displays**:
- List of all available commands
- Brief description of each command
- Usage examples
- Permission requirements

### 👥 Onboarding System

#### `/gal onboard`
Manage the onboarding system for new server members.

**Usage**:
```
/gal onboard action:setup        # Set up onboarding system
/gal onboard action:stats        # View onboarding statistics
/gal onboard action:refresh      # Refresh onboarding data
```

**Permissions**: Admin only

**Actions**:
- `setup`: Configure onboarding channels and roles
- `stats`: Display onboarding statistics
- `refresh`: Update onboarding data and status

## User-Facing Features

### 🎫 Tournament Registration

#### Registration Process
1. **Open Registration**: Admin uses `/gal toggle` or `/gal event`
2. **User Registration**: Users click "Manage Registration" button
3. **Information Required**:
   - **IGN** (In-Game Name): For tournament identification
   - **Team Name** (doubleup mode only): Team tag/name

#### Registration Interface
- **Interactive Buttons**: Register, Waitlist, Cancel
- **Validation**: Ensures IGN is valid
- **Feedback**: Immediate confirmation of registration
- **Error Handling**: Clear error messages for issues

#### Waitlist System
- **Automatic Registration**: When spots open, first waitlisted user gets registered
- **Position Tracking**: Shows your position in waitlist
- **Notifications**: DM notification when moved to registered list
- **Team Support**: Supports team registration in doubleup mode

### 🔒 Tournament Check-In

#### Check-In Process
1. **Open Check-In**: Admin uses `/gal toggle` to open check-in
2. **User Check-In**: Users click "Manage Check-In" button
3. **Confirmation**: Immediate confirmation of check-in status
4. **Ability to Cancel**: Users can check out if plans change

#### Check-In Features
- **Time-Sensitive**: Check-in closes at specified time
- **Live Counting**: Shows how many players are checked in
- **Management**: Easy check-out if needed
- **Reminders**: Automatic reminders to checked-in users

## Tournament Workflow

### Normal Tournament Flow

1. **Setup Phase**
   ```
   /gal event mode:normal    # Set to normal mode
   /gal toggle               # Open registration
   ```

2. **Registration Phase**
   - Users register with IGN
   - Waitlist enabled after capacity reached
   - Registration closes at specified time

3. **Check-In Phase**
   ```
   /gal toggle               # Close registration, open check-in
   /gal reminder              # Send reminders to unchecked-in users
   ```

4. **Tournament Phase**
   - Check-in closes
   - Players join lobby when called
   - Tournament proceeds with registered players

### Doubleup Tournament Flow

1. **Setup Phase**
   ```
   /gal event mode:doubleup    # Set to doubleup mode
   /gal toggle                 # Open registration
   ```

2. **Registration Phase**
   - Users register with IGN and team name
   - Teams of 2 players maximum
   - Team management integrated

3. **Remaining Flow**: Same as normal tournament

## Error Handling

### Common Error Messages

#### Permission Errors
```
"🚫 You don't have permission to use this command."
```
**Solution**: Ensure you have required roles (Admin, Moderator, GAL Helper)

#### Configuration Errors
```
"❌ Configuration error: [details]"
```
**Solution**: Check config.yaml file and ensure it's properly formatted

#### Registration Errors
```
"⚠️ Tournament is full. You've been added to waitlist."
```
**Solution**: Wait for a spot to open or check your waitlist position

#### IGN Validation Errors
```
"❌ Invalid IGN. Please enter a valid League of Legends IGN."
```
**Solution**: Enter a proper League of Legends summoner name

## Advanced Features

### Event Scheduling
- **Automatic Timing**: Registration/check-in can be scheduled
- **Time-based Control**: Automatic opening/closing at specified times
- **Time Zone Support**: Handles different time zones correctly

### Data Synchronization
- **Google Sheets Integration**: Real-time sync with tournament sheets
- **Cache Management**: Optimized data fetching and caching
- **Error Recovery**: Automatic retry on sync failures

### Notifications
- **Role Pings**: Configurable pings when events open
- **DM Reminders**: Personalized reminders to users
- **Public Updates**: Channel notifications for status changes

## Configuration Guide

### Required Roles
- **Admin**: Full access to all commands
- **Moderator**: Access to most commands
- **GAL Helper**: Limited access to essential commands

### Channel Setup
- **Registration Channel**: Where users register for tournaments
- **Log Channel**: Where bot logs important events
- **Welcome Channel**: For new member onboarding
- **Onboarding Review**: Staff review of onboarding applications

### Tournament Configuration
- **Player Limits**: Configurable maximum players
- **Team Settings**: Team size and management
- **Timing Controls**: Open/close times for registration/check-in
- **Event Names**: Custom tournament names

## Troubleshooting

### Commands Not Working
1. **Check Permissions**: Verify you have required roles
2. **Check Bot Status**: Ensure bot is online and responding
3. **Check Channel**: Commands may be restricted to certain channels

### Registration Issues
1. **Invalid IGN**: Enter a valid League of Legends summoner name
2. **Tournament Full**: Add yourself to waitlist
3. **Already Registered**: Check your current registration status

### Data Sync Issues
1. **Google Sheets**: Verify sheet URLs and permissions
2. **Network Issues**: Check internet connectivity
3. **API Limits**: Monitor Riot API usage limits

### General Issues
1. **Restart Bot**: Use `/gal config action:reload`
2. **Check Logs**: Review bot logs for errors
3. **Contact Support**: Ask in designated support channel

## Bot Status Commands

### Bot Health
- **Activity Status**: Shows current bot activity
- **Connected Servers**: Lists Discord servers bot is in
- **Response Time**: Bot response latency

### System Information
- **Version**: Current bot version
- **Uptime**: How long bot has been running
- **Memory Usage**: Current resource consumption

## Integration with Dashboard

The bot integrates with the GAL Live Graphics Dashboard:

### Data Sharing
- **Registration Data**: Synced to dashboard database
- **Tournament State**: Real-time status updates
- **User Information**: Consistent across systems

### Command Synchronization
- **Tournament Commands**: Reflect in dashboard interface
- **User Management**: Coordinated between bot and dashboard
- **Status Updates**: Real-time synchronization

---

**Last Updated**: 2025-01-26  
**Maintained by**: Guardian Angel League Development Team
