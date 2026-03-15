from __future__ import annotations
import discord
from discord.ext import commands
from datetime import datetime
from extensions import leaderboard

# CONFIG
DEFAULT_IMAGE_URL = "https://cdn.discordapp.com/attachments/611922107345141760/1348673800874754088/Polaris_over_Yela_bright.png"
LOGGING_CHANNEL_IDS = [1091876261938343986]

CHANNEL_OPTIONS = [
    ("Server News", 1113146864804573285),
    ("Community Feed", 1388237591845011516),
    ("SC News", 569635458183856149),
    ("General News", 803341100618219540),
    ("Patch Notes", 585952222853201941),
    ("Testing", 1062905729532571719),
]

PING_ROLE_OPTIONS = [
    ("Server News", 1113152142300156004),
    ("Community Feed", 1402452172595265596),
    ("SC News", 620025828079697920),
    ("General News", 803343410794594385),
    ("Patch Notes", 620025894559547412),
    ("Evocati Patch Notes", 1305975151858552862),
    ("MOTD", 1310721100392435797),
    ("Testing", 1473004437034242260),
]

LEADERBOARD_CHANNEL_IDS = {
    1113146864804573285,
    1388237591845011516,
    569635458183856149,
    803341100618219540,
    585952222853201941,
}

EMBED_COLOR = discord.Color.blurple()
TIMEOUT = 900

# DATA MODEL
class Announcement:
    def __init__(
        self,
        title: str = "",
        description: str = "",
        url: str | None = None,
        image_url: str | None = None,
        video_url: str | None = None,
        channel: discord.TextChannel | None = None,
        ping: discord.Role | None = None,
        ping_preview: str | None = None,
        publish: bool = False,
    ):
        self.title = title
        self.description = description
        self.url = url
        self.image_url = image_url or DEFAULT_IMAGE_URL
        self.video_url = video_url
        self.channel = channel
        self.ping = ping
        self.ping_preview = ping_preview
        self.publish = publish

    @classmethod
    def from_message(cls, message: discord.Message):
        embed = message.embeds[0]
        return cls(
            title=embed.title or "",
            description=embed.description or "",
            url=embed.url,
            image_url=embed.image.url if embed.image else DEFAULT_IMAGE_URL,
            channel=message.channel,
        )

    def embed(self) -> discord.Embed:
        e = discord.Embed(
            title=self.title or None,
            description=self.description or None,
            url=self.url,
            color=EMBED_COLOR,
        )
        if self.image_url:
            e.set_image(url=self.image_url)
        return e

# MODAL
class TextModal(discord.ui.Modal):
    def __init__(self, builder, field: str, label: str, long: bool = False):
        super().__init__(title=f"Edit {label}")
        self.builder = builder
        self.field = field
        default_value = getattr(builder.announcement, field) or ""
        self.input = discord.ui.TextInput(
            label=label,
            default=default_value,
            style=discord.TextStyle.long if long else discord.TextStyle.short,
            required=False,
        )
        self.add_item(self.input)

    async def on_submit(self, interaction: discord.Interaction):
        setattr(self.builder.announcement, self.field, self.input.value)
        self.builder.update_field_buttons()
        await interaction.response.edit_message(
            embed=self.builder.announcement.embed(),
            view=self.builder.view,
        )

# SELECTS
class ChannelSelect(discord.ui.Select):
    def __init__(self, builder):
        self.builder = builder
        options = [discord.SelectOption(label=name, value=str(cid)) for name, cid in CHANNEL_OPTIONS]
        super().__init__(placeholder="Select Channel", options=options, row=0)

    async def callback(self, interaction: discord.Interaction):
        cid = int(self.values[0])
        self.builder.announcement.channel = interaction.guild.get_channel(cid)
        self.placeholder = next((name for name, id in CHANNEL_OPTIONS if id == cid), "Select Channel")
        await interaction.response.edit_message(embed=self.builder.announcement.embed(), view=self.builder.view)

class PingSelect(discord.ui.Select):
    def __init__(self, builder):
        self.builder = builder
        options = [discord.SelectOption(label=name, value=str(rid)) for name, rid in PING_ROLE_OPTIONS]
        super().__init__(placeholder="Select Ping Role", options=options, row=1)

    async def callback(self, interaction: discord.Interaction):
        rid = int(self.values[0])
        self.builder.announcement.ping = interaction.guild.get_role(rid)
        self.placeholder = next((name for name, id in PING_ROLE_OPTIONS if id == rid), "Select Ping Role")
        await interaction.response.edit_message(embed=self.builder.announcement.embed(), view=self.builder.view)

# FIELD BUTTON
class FieldButton(discord.ui.Button):
    def __init__(self, builder, field, label, row, style):
        super().__init__(label=label, row=row, style=style)
        self.builder = builder
        self.field = field

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(
            TextModal(self.builder, self.field, self.label, long=self.field=="description")
        )

# CANCEL / POST / PUBLISH BUTTONS
class PublishButton(discord.ui.Button):
    def __init__(self, builder):
        label = "Published: ✅" if builder.announcement.publish else "Published: ❌"
        super().__init__(label=label, style=discord.ButtonStyle.secondary, row=3)
        self.builder = builder

    async def callback(self, interaction: discord.Interaction):
        self.builder.announcement.publish = not self.builder.announcement.publish
        self.label = "Published: ✅" if self.builder.announcement.publish else "Published: ❌"
        await interaction.response.edit_message(embed=self.builder.announcement.embed(), view=self.builder.view)

class CancelButton(discord.ui.Button):
    def __init__(self, builder, editing=False):
        super().__init__(label="Cancel", style=discord.ButtonStyle.danger, row=4)
        self.builder = builder
        self.editing = editing

    async def callback(self, interaction: discord.Interaction):
        await interaction.message.delete()
        msg_text = "Announcement editing cancelled." if self.editing else "Announcement creation cancelled."
        await interaction.response.send_message(msg_text, ephemeral=True)
        self.view.stop()

class PostButton(discord.ui.Button):
    def __init__(self, builder, editing=False):
        label = "Edit" if editing else "Post"
        super().__init__(label=label, style=discord.ButtonStyle.blurple, row=4)
        self.builder = builder
        self.editing = editing

    async def callback(self, interaction: discord.Interaction):
        ann = self.builder.announcement
        if not ann.channel:
            await interaction.response.send_message("Select a channel first.", ephemeral=True)
            return

        if self.editing and self.builder.target:
            msg = self.builder.target
            await msg.edit(embed=ann.embed())
        else:
            msg = await ann.channel.send(embed=ann.embed())

        if ann.publish and isinstance(ann.channel, discord.TextChannel) and ann.channel.is_news():
            await msg.publish()

        if ann.video_url:
            await ann.channel.send(ann.video_url)

        ping_msg = ""
        if ann.ping:
            ping_msg += f"{ann.ping.mention}"
        if ann.ping_preview:
            ping_msg += f" - {ann.ping_preview}"
        if ping_msg:
            await ann.channel.send(ping_msg)

        for cid in LOGGING_CHANNEL_IDS:
            ch = self.builder.ctx.guild.get_channel(cid)
            if ch:
                await ch.send(embed=ann.embed())

        if ann.channel.id in LEADERBOARD_CHANNEL_IDS:
            leaderboard.record_announcement_post(interaction.user.id)

        await interaction.response.send_message(
            "The announcement has been posted! \nhttps://i.postimg.cc/J48Vk8my/meme-8-1.gif"
            if not self.editing else "Announcement edited!",
            ephemeral=False
        )

        self.view.stop()

# VIEW
class BuilderView(discord.ui.View):
    def __init__(self, builder, editing=False):
        super().__init__(timeout=TIMEOUT)
        self.builder = builder
        self.editing = editing

        self.add_item(ChannelSelect(builder))
        self.add_item(PingSelect(builder))
        self.update_field_buttons()
        self.add_item(PublishButton(builder))
        self.add_item(CancelButton(builder, editing=editing))
        self.add_item(PostButton(builder, editing=editing))

    def update_field_buttons(self):
        field_buttons = [item for item in self.children if isinstance(item, FieldButton)]
        for btn in field_buttons:
            self.remove_item(btn)

        for field, label, row, long in [
            ("title", "Title", 2, False),
            ("description", "Description", 2, True),
            ("url", "URL", 2, False),
            ("image_url", "Image", 3, False),
            ("video_url", "Video", 3, False),
            ("ping_preview", "Ping Preview", 3, False),
        ]:
            style = discord.ButtonStyle.success if getattr(self.builder.announcement, field) else discord.ButtonStyle.gray
            self.add_item(FieldButton(self.builder, field, label, row, style))

# BUILDER
class Builder:
    def __init__(self, ctx, announcement, target=None, editing=False):
        self.ctx = ctx
        self.announcement = announcement
        self.target = target
        self.editing = editing
        self.view = BuilderView(self, editing=editing)

    def update_field_buttons(self):
        self.view.update_field_buttons()

    async def start(self):
        await self.ctx.send(embed=self.announcement.embed(), view=self.view)

# COG
class Announcements(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.group(invoke_without_command=True)
    async def embed(self, ctx):
        await ctx.send_help(ctx.command)

    @embed.command()
    async def create(self, ctx):
        await Builder(ctx, Announcement(channel=ctx.channel)).start()

    @embed.command()
    async def edit(self, ctx, message: discord.Message):
        if not message.embeds:
            await ctx.reply("That message has no embed.")
            return
        await Builder(ctx, Announcement.from_message(message), target=message, editing=True).start()

# SETUP
async def setup(bot: commands.Bot):
    await bot.add_cog(Announcements(bot))

