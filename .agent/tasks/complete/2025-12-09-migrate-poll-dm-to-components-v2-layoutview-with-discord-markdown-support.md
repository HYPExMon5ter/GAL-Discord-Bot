# Migration Plan: Poll DM to Components V2 LayoutView

## Problems Identified

### 1. Using Old Embed System
**Current Issue**: Poll DMs use traditional `discord.Embed` which doesn't support Discord's markdown formatting:
- `#` for headers doesn't work in embeds
- `###` for subheaders doesn't work in embeds  
- `-#` for subtext doesn't work in embeds
- Formatting shows as literal text instead of styled text

**From Screenshot**:
- Title shows: `"# 🌟 Hello Angel!"` (literal # visible)
- Headers show: `"### 🔗 How to vote:"` (literal ### visible)
- Footer shows: `"-# 💙 Thank..."` (literal -# visible)

### 2. Progress Message Changed
**Issue**: Progress message formatting was altered and user wants original back
- Need to restore the original simple progress display
- Keep it functional without cosmetic changes

## Solution: Migrate to Components V2

### Why Components V2 (LayoutView)?
Components V2 uses `discord.ui.Text` which **natively supports Discord markdown**:
- `# Header` renders as large header
- `### Subheader` renders as medium header
- `-# Subtext` renders as smaller subtext
- Full Discord markdown support (bold, italic, links, etc.)

### Architecture Overview

**Current (Embed-based)**:
```python
embed = discord.Embed(title="...", description="...")
embed.add_field(name="...", value="...")
view = PollDMView(poll_link)  # Simple button view
await member.send(embed=embed, view=view)
```

**New (LayoutView-based)**:
```python
view = PollDMLayoutView(poll_link, config)  # LayoutView with text + button
await member.send(view=view)  # No embed needed!
```

## Implementation Plan

### Step 1: Create PollDMLayoutView

**File**: `helpers/poll_helpers.py`

Add new LayoutView class that uses Components V2:

```python
class PollDMLayoutView(discord.ui.LayoutView):
    """LayoutView for poll DM using Components V2 with markdown support."""
    
    def __init__(self, poll_link: str, config: dict):
        super().__init__(timeout=None)
        self.poll_link = poll_link
        self.config = config
    
    def build_container(self) -> discord.ui.Container:
        """Build the poll DM container with Discord markdown support."""
        dm_config = self.config.get("dm_embed", {})
        
        # Extract config values
        title = dm_config.get("title", "# 🌟 Hello Angel!")
        header = dm_config.get("header", "### We need your input! 🗳️")
        body = dm_config.get("body", "")
        how_to_vote = dm_config.get("how_to_vote", {})
        how_to_vote_title = how_to_vote.get("title", "### 🔗 How to vote:")
        how_to_vote_content = how_to_vote.get("content", "Click the **\"Go to Poll\"** button...")
        footer = dm_config.get("footer", "-# 💙 Thank you for helping make GAL tournaments even better!")
        button_config = dm_config.get("button", {})
        button_label = button_config.get("label", "🗳️ Go to Poll")
        
        # Build text content with proper spacing
        text_content = f"{title}\n\n"
        text_content += f"{header}\n\n"
        text_content += f"📋 **Poll Details**\n{body}\n\n"
        text_content += f"{how_to_vote_title}\n{how_to_vote_content}\n\n"
        text_content += footer
        
        # Create container
        container = discord.ui.Container()
        
        # Add text component (supports Discord markdown!)
        container.add_item(discord.ui.Text(
            content=text_content,
            color=discord.Color.from_str(dm_config.get("color", "#f8c8dc"))
        ))
        
        # Add separator
        container.add_item(discord.ui.Separator(
            visible=True,
            spacing=discord.SeparatorSpacing.small
        ))
        
        # Add poll button
        container.add_item(discord.ui.Button(
            label=button_label,
            url=self.poll_link,
            style=discord.ButtonStyle.link
        ))
        
        return container
```

### Step 2: Update PollNotifier to Use LayoutView

**File**: `helpers/poll_helpers.py`

Update `send_dm_to_user` method:

```python
async def send_dm_to_user(self, member: discord.Member, view: discord.ui.LayoutView) -> bool:
    """Send DM to a single user using LayoutView. Returns True if successful."""
    try:
        await member.send(view=view)  # No embed parameter!
        return True
    except discord.Forbidden:
        logger.warning(f"Could not DM {member} (DMs disabled or bot blocked)")
        self.failed_users.append((member, "DMs disabled"))
        return False
    except discord.HTTPException as e:
        logger.warning(f"HTTP error sending DM to {member}: {e}")
        self.failed_users.append((member, f"HTTP error: {str(e)[:50]}"))
        return False
    except Exception as e:
        logger.error(f"Unexpected error sending DM to {member}: {e}")
        self.failed_users.append((member, f"Unexpected error"))
        return False
```

Update `send_to_all_angels` to create LayoutView instead of embed:

```python
async def send_to_all_angels(self, progress_callback: Callable) -> Tuple[int, int, List]:
    """Send DMs to all Angels with progress tracking."""
    self.start_time = time.time()
    
    # Get all Angels members
    members = self.get_angels_members()
    self.total_count = len(members)
    
    if self.total_count == 0:
        logger.warning("No members found with Angels role")
        return 0, 0, []
    
    # Create DM LayoutView (not embed!)
    dm_view = PollDMLayoutView(self.poll_link, self.config)
    
    # Process in batches
    current = 0
    
    try:
        for i in range(0, len(members), self.batch_size):
            batch = members[i:i + self.batch_size]
            
            # Send DMs concurrently within batch
            tasks = []
            for member in batch:
                task = asyncio.create_task(self.send_dm_to_user(member, dm_view))
                tasks.append(task)
            
            # Wait for batch to complete
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Count results and update progress...
            # (rest of implementation stays the same)
```

### Step 3: Restore Original Progress Message Format

**File**: `helpers/poll_helpers.py`

Keep the progress message simple and functional:

```python
def create_progress_embed(self, current: int, total: int, elapsed: float) -> discord.Embed:
    """Create simple progress tracking embed."""
    percentage = (current / total * 100) if total > 0 else 0
    
    embed = discord.Embed(
        title="📨 Sending Poll Notifications",
        color=discord.Color.blue()
    )
    
    # Simple progress bar
    bar_length = 20
    filled = int(bar_length * percentage / 100)
    bar = "█" * filled + "░" * (bar_length - filled)
    
    # Calculate time remaining
    if current > 0:
        avg_time = elapsed / current
        remaining = avg_time * (total - current)
        time_str = f"{remaining:.0f}s"
    else:
        time_str = "Calculating..."
    
    embed.add_field(
        name="⏳ Progress",
        value=f"{current}/{total} ({percentage:.0f}%)\n[{bar}] {percentage:.0f}%",
        inline=False
    )
    
    embed.add_field(
        name="📊 Status",
        value=f"✅ Successful: {self.success_count}\n❌ Failed: {self.failed_count}",
        inline=True
    )
    
    embed.add_field(
        name="⏱️ Time",
        value=f"Elapsed: {elapsed:.0f}s\nRemaining: {time_str}",
        inline=True
    )
    
    return embed
```

### Step 4: Update Config.yaml

**File**: `config.yaml`

Keep markdown formatting (now it will work with LayoutView):

```yaml
poll:
  dm_embed:
    title: "# 🌟 Hello Angel!"  # ✅ Keep # for header
    color: "#f8c8dc"
    
    header: "### We need your input! 🗳️"  # ✅ Keep ### for subheader
    
    body: |
      Please take a moment to vote on when you'd like our next **Guardian Angel League** tournament to be held. Your schedule matters, and we want to pick the best time for everyone! 🏆
    
    how_to_vote:
      title: "### 🔗 How to vote:"  # ✅ Keep ### for subheader
      content: "Click the **\"Go to Poll\"** button below to access the voting form. It only takes a few seconds! 😊"
    
    footer: "-# 💙 Thank you for helping make GAL tournaments even better!"  # ✅ Keep -# for subtext
    
    button:
      label: "🗳️ Go to Poll"
```

## Expected Results

### DM Appearance After Migration:
```
# 🌟 Hello Angel!          ← Large header (Discord markdown)

### We need your input! 🗳️  ← Medium header (Discord markdown)

📋 Poll Details            ← Bold text
Please take a moment...    ← Normal text

### 🔗 How to vote:         ← Medium header (Discord markdown)
Click the "Go to Poll"...  ← Normal text

-# 💙 Thank you for...     ← Small subtext (Discord markdown)

[🗳️ Go to Poll]            ← Button
```

### Progress Message:
```
📨 Sending Poll Notifications

⏳ Progress
1/1 (100.0%)
[████████████████████] 100.0%

📊 Status             ⏱️ Time
✅ Successful: 1      Elapsed: 0s
❌ Failed: 0          Remaining: 0s
```

## Benefits of Components V2

1. **Native Markdown Support**: `#`, `###`, `-#`, `**bold**`, `*italic*` all work
2. **Modern Discord UI**: Matches latest Discord design patterns
3. **Better Spacing**: Automatic spacing between components
4. **Consistent with Tournament Channel**: Uses same system as main bot embeds
5. **Future-Proof**: Components V2 is the modern Discord standard

## Files to Modify

1. `helpers/poll_helpers.py`:
   - Add `PollDMLayoutView` class
   - Update `send_dm_to_user()` to use LayoutView
   - Update `send_to_all_angels()` to create LayoutView
   - Simplify `create_progress_embed()`

2. `config.yaml`:
   - Restore markdown formatting (it will now work!)

## Testing Checklist

- [ ] DM shows proper header formatting (# renders as large text)
- [ ] DM shows proper subheaders (### renders as medium text)
- [ ] DM shows proper footer (- # renders as small subtext)
- [ ] Button works and links to poll
- [ ] Progress tracking displays correctly
- [ ] Final summary displays correctly
- [ ] No errors during sending