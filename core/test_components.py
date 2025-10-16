import discord
from discord.ext import commands


class TestComponents(discord.ui.LayoutView):
    __test__ = False
    container1 = discord.ui.Container(
        discord.ui.Section(
            discord.ui.TextDisplay(content="# 🏆 Tournament Hub"),
            discord.ui.TextDisplay(content="Welcome to the Guardian Angel League tournament hub!"),
            discord.ui.TextDisplay(content="Below you will see the options to **Register** and **Check In**."),
            accessory=discord.ui.Thumbnail(
                media="https://media.discordapp.net/attachments/1400529171200999534/1421203430722113607/GA_Logo_Black_Background_-_Smaller.jpg?ex=68d82e56&is=68d6dcd6&hm=36df9a0841570eac40a1ef3922bc25beef773bb4f807f5e98b12fe564d369f2f&=&format=webp",
            ),
        ),
        discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small),
        discord.ui.TextDisplay(content="### 🎮 Tournament format"),
        discord.ui.Separator(visible=False, spacing=discord.SeparatorSpacing.small),
        discord.ui.TextDisplay(
            content="**Event Name**: K.O. GALISEUM\n**Mode**: Individual Players\n**Max Players**: 24"),
        discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.large),
        discord.ui.TextDisplay(content="# 📝 Registration"),
        discord.ui.TextDisplay(content="### 🟢 Registration Open / 🔴 Registration Closed"),
        discord.ui.TextDisplay(content="> Scheduled time here, if present"),
        discord.ui.Separator(visible=False, spacing=discord.SeparatorSpacing.large),
        discord.ui.TextDisplay(content="📊 Capacity: ⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜"),
        discord.ui.TextDisplay(content="-# Player count"),
        discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.large),
        discord.ui.TextDisplay(content="# ✔️ Check In"),
        discord.ui.TextDisplay(content="### 🟢 Check In Open / 🔴 Check In Closed"),
        discord.ui.TextDisplay(content="> Scheduled time here, if present"),
        discord.ui.Separator(visible=False, spacing=discord.SeparatorSpacing.large),
        discord.ui.TextDisplay(content="📊 Capacity: ⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜"),
        discord.ui.TextDisplay(content="-# Player count"),
        discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.large),
        discord.ui.ActionRow(
            discord.ui.Button(
                style=discord.ButtonStyle.primary,
                label="Register",
                emoji="📝",
                custom_id="0a270c8d7c6c42c2e7112305f6acaa77",
            ),
            discord.ui.Button(
                style=discord.ButtonStyle.success,
                label="Check In",
                emoji="✔️",
                custom_id="3db440b86b06409ad2c7e33d9e0d562a",
            ),
        ),
        discord.ui.ActionRow(
            discord.ui.Button(
                style=discord.ButtonStyle.secondary,
                label="View Players",
                emoji="🎮",
                custom_id="78691a18398a42f6952ee2e1a967a7cf",
            ),
            discord.ui.Button(
                style=discord.ButtonStyle.danger,
                label="Admin Panel",
                emoji="🔧",
                custom_id="015c0e5956624d44eb7097e3a582206b",
            ),
        ),
        accent_colour=discord.Colour(15762110),
    )


"""
container1 = discord.ui.Container(
        discord.ui.Section(
            discord.ui.TextDisplay(content="# Tournament Hub"),
            discord.ui.TextDisplay(content="Welcome to the Guardian Angel League tournament hub."),
            discord.ui.TextDisplay(content="Below you will see the options to **Register** and **Check In**."),
            accessory=discord.ui.Thumbnail(
                media="https://media.discordapp.net/attachments/1400529171200999534/1421203430722113607/GA_Logo_Black_Background_-_Smaller.jpg?ex=68d82e56&is=68d6dcd6&hm=36df9a0841570eac40a1ef3922bc25beef773bb4f807f5e98b12fe564d369f2f&=&format=webp",
            ),
        ),
        discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small),
        discord.ui.TextDisplay(content="### 🎮 Tournament format"),
        discord.ui.Separator(visible=False, spacing=discord.SeparatorSpacing.small),
        discord.ui.TextDisplay(content="**Event Name**: K.O. GALISEUM\n**Mode**: Individual Players\n**Max Players**: 24"),
        accent_colour=discord.Colour(15762110),
    )
    
    container2 = discord.ui.Container(
        discord.ui.MediaGallery(
            discord.MediaGalleryItem(
                media="https://dummyimage.com/3999x800",
            ),
        ),
        discord.ui.TextDisplay(content="🟢 Registration Open / 🔴 Registration Closed"),
        discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small),
        discord.ui.TextDisplay(content="📊 Capacity: ⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜"),
        discord.ui.TextDisplay(content="Player count"),
        discord.ui.ActionRow(
                discord.ui.Button(
                    style=discord.ButtonStyle.primary,
                    label="Manage Check In",
                    emoji="📝",
                    custom_id="c99ed807f978427acf6e5a890c7fdab9",
                ),
                discord.ui.Button(
                    style=discord.ButtonStyle.success,
                    label="View Players",
                    emoji="🎮",
                    custom_id="50390713e31f4ee5abf6d4fe2564138f",
                ),
        ),
        accent_colour=discord.Colour(1752220),
    )
    
    container3 = discord.ui.Container(
        discord.ui.MediaGallery(
            discord.MediaGalleryItem(
                media="https://dummyimage.com/3999x800",
            ),
        ),
        discord.ui.TextDisplay(content="🟢 Check In Open / 🔴 Check In Closed"),
        discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small),
        discord.ui.TextDisplay(content="📊 Capacity: ⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜"),
        discord.ui.TextDisplay(content="Player count"),
        discord.ui.ActionRow(
                discord.ui.Button(
                    style=discord.ButtonStyle.primary,
                    label="Manage Check In",
                    emoji="📝",
                    custom_id="0594a3f00d594ca0cd5874905d0746e2",
                ),
                discord.ui.Button(
                    style=discord.ButtonStyle.success,
                    label="View Players",
                    emoji="🎮",
                    custom_id="f151584d6282436f9a716fabb84a9499",
                ),
        ),
        accent_colour=discord.Colour(1752220),
    )
    
    action_row1 = discord.ui.ActionRow(
            discord.ui.Button(
                style=discord.ButtonStyle.danger,
                label="Admin Panel",
                emoji="🔧",
                custom_id="015c0e5956624d44eb7097e3a582206b",
            ),
    )
"""
