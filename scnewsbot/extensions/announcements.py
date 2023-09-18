from __future__ import annotations

from typing import Any, Optional, Callable, Awaitable
from dataclasses import dataclass
from discord.ext import commands
import discord
from utils import can_publish_announcements

ANNOUNCEMENT_BUILDER_TIMEOUT = 1200
ANNOUNCEMENT_EMOJI = "👍" # <:upvote:354233015842635776>
DEFAULT_IMAGE_URL = "https://media.discordapp.net/attachments/1062905729532571719/1123340546979676311/NewsDefault.jpg?width=810&height=180"
INSTRUCTIONS = """\
1. Title should not use any formatting.
2. "Video" should only be used for YouTube or video links with pretty embeds.
3. URL should be used for any regular link such as a comm-link.
4. In the description box, use `-` and it will replace it with `➣`, use `+` and it will replace it with `✦` preceeded by three spaces.
5. Use the `&ids` commands to get the channel and role IDs.
6. Do not ping for every post if there are consecutive posts in the same channel, instead ping only on the final post and provide an overall preview.\n7. **ALWAYS** include a ping preview, you can find these using `&previews`.
8. Always select publish unless explicitly not needed (server only announcements).\
"""


async def get_ping_message(message: discord.Message, /) -> Optional[discord.Message]:
    async for ping in message.channel.history(limit=1, after=message.created_at):
        if ping.author.id == message._state.user.id and ping.mentions:
            return ping


def reformat_description(description: str) -> str:
    split_description = description.split("\n")

    for index, line in enumerate(split_description):
        if line.startswith("-"):
            split_description[index] = "➣" + line[1:]
        elif line.startswith("+"):
            split_description[index] = "ㅤ✦" + line[1:]

    return "\n".join(split_description)


class AnnouncementCog(commands.Cog, name="Announcements"):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.check(can_publish_announcements)
    @commands.command(brief="Gives you instructions for using the announcement system.")
    async def instructions(self, ctx: commands.Context) -> None:
        embed = discord.Embed(
            color=self.bot.config.embed_color,
            title="Instructions",
            description=INSTRUCTIONS,
        )
        await ctx.reply(embed=embed)

    @commands.guild_only()
    @commands.group(
        brief="Commands relating to the r/starcitizen Discord news system.",
        aliases=["announcement", "news", "embed"],
        invoke_without_command=True,
    )
    async def announcements(self, ctx: commands.Context) -> None:
        await ctx.send_help(ctx.command)

    @commands.check(can_publish_announcements)
    @announcements.command(
        aliases=["post"], brief="Creates and sends a new announcement."
    )
    async def create(self, ctx: commands.Context) -> None:
        announcement_builder = AnnouncementBuilder(owner=ctx.author)
        embed = await announcement_builder.get_embed(bot=self.bot)
        await ctx.send(
            content=announcement_builder.announcement.video_url,
            embed=embed,
            view=announcement_builder.view,
        )

    @commands.check(can_publish_announcements)
    @announcements.command(brief="Edits an existing announcement.")
    async def edit(self, ctx: commands.Context, message: discord.Message) -> None:
        announcement = await Announcement.from_message(message, bot=self.bot)
        announcement_builder = AnnouncementBuilder(
            edit_message=message, edit_announcement=announcement, owner=ctx.author
        )
        embed = await announcement_builder.get_embed(bot=self.bot)
        await ctx.send(
            content=announcement_builder.announcement.video_url,
            embed=embed,
            view=announcement_builder.view,
        )

    @commands.check(can_publish_announcements)
    @announcements.command(brief="Deletes an announcement.")
    async def delete(self, ctx: commands.Context, message: discord.Message) -> None:
        if message.author != self.bot.user and not message.embeds:
            await ctx.reply("That is not an announcement.")

        ping_message = await get_ping_message(message)
        if ping_message:
            await ping_message.delete()

        await message.delete()
        await ctx.reply("Deleted that announcement. 👌")

    @commands.Cog.listener()
    async def on_command_error(
        self, ctx: commands.Context, error: commands.CommandError
    ) -> None:
        if isinstance(error, commands.MessageNotFound):
            await ctx.send("Could not find that message.")
        else:
            raise error


class InvalidAnnouncementException(Exception):
    pass


@dataclass
class Option:
    id: str
    name: str
    directions: Optional[str] = None
    row: int = 0
    is_long: bool = False


class Announcement:
    def __init__(
        self,
        *,
        title: str = "Announcement",
        url: Optional[str] = None,
        description: Optional[str] = None,
        video_url: Optional[str] = None,
        image_url: Optional[str] = DEFAULT_IMAGE_URL,
        channel: Optional[discord.abc.Messageable] = None,
        ping: Optional[discord.Role] = None,
        ping_preview: Optional[str] = None,
        author_id: Optional[int] = None,
        is_anonymous: bool = False,
        will_notify: bool = False,
    ) -> None:
        self.title = title
        self.url = url
        self.description = description
        self.video_url = video_url
        self.image_url = image_url
        self.channel = channel
        self.ping = ping
        self.ping_preview = ping_preview

        self.author_id = author_id
        self.is_anonymous = is_anonymous
        self.will_notify = will_notify

    async def set_option(
        self, option: Option, value: Any, *, guild: discord.Guild
    ) -> bool:
        if option is None:
            setattr(self, option.id, converted_value)
            return True

        if option.id == "description":
            converted_value = reformat_description(value)
        elif option.id == "channel":
            if value.startswith("#"):
                value = value[1:]

            converted_value = discord.utils.find(
                lambda c: c.name.lower() == value.lower(), guild.text_channels
            )
            if not converted_value and value.isnumeric():
                converted_value = guild.get_channel(int(value))
        elif option.id == "ping":
            converted_value = discord.utils.find(
                lambda r: r.name.lower() == value.lower(), guild.roles
            )
            if not converted_value and value.isnumeric():
                converted_value = guild.get_role(int(value))
        else:
            if option.id == "video_url" and self.image_url == DEFAULT_IMAGE_URL:
                self.image_url = None

            converted_value = value

        if converted_value is None:
            return False

        setattr(self, option.id, converted_value)
        return True

    async def get_embed(self, *, bot: commands.Bot, show_author: bool = False) -> discord.Embed:
        embed = discord.Embed(
            color=bot.config.embed_color,
            title=self.title,
            description=self.description,
        )
        embed.set_image(url=self.image_url)

        if self.url and self.description:
            embed.description = f"{self.url}\n\n" + embed.description
        elif self.url:
            embed.description = self.url

        if not self.is_anonymous or show_author:
            if self.author_id:
                author = await bot.fetch_user(self.author_id)
                embed.set_footer(text=f"This post was written by {author}")
            else:
                embed.set_footer(text="Unknown Author")

        return embed

    @classmethod
    async def from_message(
        cls, message: discord.Message, /, *, bot: commands.Bot
    ) -> Any:
        if message.author != message.guild.me:
            raise InvalidAnnouncementException("This is not a bot message.")
            return

        if not len(message.embeds) == 1:
            raise InvalidAnnouncementException("This message does not have any embeds.")
            return

        if message.components:
            raise InvalidAnnouncementException("This message has not been posted yet.")
            return

        embed = message.embeds[0]
        author = discord.utils.find(
            lambda member: str(member) == embed.author.name, message.guild.members
        )

        ping = None
        ping_preview = None
        ping_message = await get_ping_message(message)

        if ping_message:
            split_message = ping_message.content.split(" - ")
            ping = await commands.RoleConverter.convert(
                await bot.get_context(ping_message), split_message[0]
            )

            if len(split_message) == 2:
                ping_preview = split_message[1]

        url = None
        description = embed.description

        if embed.description is not None:
            if len(embed.description.split("\n\n")) > 0:
                url = embed.description.split("\n\n")[0]
                description = "\n\n".join(description.split("\n\n")[1:])

        return cls(
            title=embed.title,
            url=url,
            description=description,
            video_url=message.content,
            image_url=embed.image.url,
            channel=message.channel,
            ping=ping,
            ping_preview=ping_preview,
            author_id=author.id if author else None,
            is_anonymous=embed.author is None,
            will_notify=False,
        )


class AnnouncementBuilder:
    def __init__(
        self,
        *,
        edit_announcement: Optional[Announcement] = None,
        edit_message: Optional[discord.Message] = None,
        owner: discord.User = None,
    ) -> None:
        self.announcement = edit_announcement or Announcement(author_id=owner.id)
        self.message = edit_message
        self.edit = edit_announcement is not None
        self.view = AnnouncementBuilderView(self)
        self.owner = owner

        _items = self.view.children
        self.view.clear_items()

        self.options: list[Option] = []
        self.add_option(Option(id="title", name="Title"))
        self.add_option(Option(id="url", name="URL"))
        self.add_option(Option(id="description", name="Description", is_long=True))
        self.add_option(Option(id="video_url", name="Video"))
        self.add_option(Option(id="image_url", name="Image"))
        self.add_option(Option(id="channel", name="Channel", row=1))
        self.add_option(Option(id="ping", name="Ping", row=1))
        self.add_option(Option(id="ping_preview", name="Ping Preview", row=1))

        for item in _items:
            self.view.add_item(item)

    async def get_embed(self, bot: commands.Bot) -> discord.Embed:
        return await self.announcement.get_embed(bot=bot)

    def add_option(self, option: Option, /) -> None:
        button = OptionButton(
            self, custom_id=option.id, label=option.name, row=option.row
        )
        self.options.append(option)
        self.view.add_item(button)


class AnnouncementBuilderView(discord.ui.View):
    def __init__(self, announcement_builder: AnnouncementBuilder, /) -> None:
        super().__init__(timeout=ANNOUNCEMENT_BUILDER_TIMEOUT)
        self.announcement_builder = announcement_builder

    def _has_permission(self, user: discord.User) -> bool:
        return user == self.announcement_builder.owner

    async def _update(self, interaction: discord.Interaction, /) -> None:
        if (
            self.announcement_builder.announcement.channel
            and self.announcement_builder.announcement.channel.type
            is discord.ChannelType.news
        ):
            self.toggle_notification.disabled = False
        else:
            self.announcement_builder.announcement.will_notify = False
            self.toggle_notification.style = discord.ButtonStyle.gray
            self.toggle_notification.disabled = True

        await interaction.response.edit_message(
            content=self.announcement_builder.announcement.video_url,
            embed=await self.announcement_builder.get_embed(bot=interaction.client),
            view=self,
            allowed_mentions=discord.AllowedMentions.none(),
        )

    async def button_callback(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        if not self._has_permission(interaction.user):
            await interaction.response.send_message(
                "You cannot use this menu.", ephemeral=True
            )
            return

        await interaction.response.send_modal(
            ChangeOptionModal(
                announcement_builder=self.announcement_builder,
                option=discord.utils.get(
                    self.announcement_builder.options, id=button.custom_id
                ),
            )
        )

    @discord.ui.button(custom_id="anonymous", label="Anonymous?", row=2)
    async def toggle_anonymous(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        if not self._has_permission(interaction.user):
            await interaction.response.send_message(
                "You cannot use this menu.", ephemeral=True
            )
            return

        self.announcement_builder.announcement.is_anonymous = (
            not self.announcement_builder.announcement.is_anonymous
        )
        if self.announcement_builder.announcement.is_anonymous:
            button.style = discord.ButtonStyle.green
        else:
            button.style = discord.ButtonStyle.gray

        await self._update(interaction)

    @discord.ui.button(
        custom_id="notification", label="Published?", row=2, disabled=True
    )
    async def toggle_notification(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        if not self._has_permission(interaction.user):
            await interaction.response.send_message(
                "You cannot use this menu.", ephemeral=True
            )
            return

        self.announcement_builder.announcement.will_notify = (
            not self.announcement_builder.announcement.will_notify
        )
        if self.announcement_builder.announcement.will_notify:
            button.style = discord.ButtonStyle.green
        else:
            button.style = discord.ButtonStyle.gray

        await self._update(interaction)

    @discord.ui.button(
        custom_id="publish", label="Post", style=discord.ButtonStyle.blurple, row=2
    )
    async def publish(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        if not self._has_permission(interaction.user):
            await interaction.response.send_message(
                "You cannot use this menu.", ephemeral=True
            )
            return

        announcement = self.announcement_builder.announcement
        role = announcement.ping
        allowed_mentions = (
            discord.AllowedMentions(everyone=False, users=False, roles=[role])
            if role
            else discord.AllowedMentions.none()
        )

        if self.announcement_builder.edit:
            await interaction.response.send_message(
                "Your announcement was edited! 🎉", ephemeral=True
            )
            self.stop()

            embed = await self.announcement_builder.get_embed(bot=interaction.client)
            embed.remove_footer()

            await self.announcement_builder.message.edit(
                content=self.announcement_builder.announcement.video_url, embed=embed
            )
            return

        if not announcement.channel:
            await interaction.response.send_message(
                "You must have a channel selected!", ephemeral=True
            )
            return

        if announcement.ping_preview and not announcement.ping:
            await interaction.response.send_message(
                "You cannot have a ping preview selected without a ping!",
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            "Your announcement was posted! 🎉 https://i.imgur.com/HRoxTzg.gif",
            ephemeral=True,
        )
        self.stop()
        bot = interaction.client

        message = await announcement.channel.send(
            content=announcement.video_url,
            embed=await announcement.get_embed(bot=bot),
        )
        await message.add_reaction(ANNOUNCEMENT_EMOJI)

        for channel_id in bot.config.repost_channels:
            repost_channel = await bot.fetch_channel(channel_id)
            await repost_channel.send(
                content=announcement.video_url,
                embed=await announcement.get_embed(bot=bot, show_author=True),
            )
            await repost_channel.send(f"(posted in {announcement.channel.mention})")

        if announcement.will_notify:
            try:
                await message.publish()
            except discord.Forbidden:
                # Not an announcement channel
                pass

        if announcement.ping and announcement.ping_preview:
            await announcement.channel.send(
                f"{announcement.ping.mention} - {announcement.ping_preview}",
                allowed_mentions=allowed_mentions,
            )
        elif announcement.ping:
            await announcement.channel.send(
                announcement.ping.mention, allowed_mentions=allowed_mentions
            )


class ChangeOptionModal(discord.ui.Modal):
    def __init__(
        self, announcement_builder: AnnouncementBuilder, option: Option
    ) -> None:
        super().__init__(title=option.name)
        self.announcement_builder = announcement_builder
        self.option = option

        self.option_input = discord.ui.TextInput(
            custom_id=self.option.id,
            label=self.option.name,
            required=self.option.id in ("title", "channel"),
            placeholder=self.option.directions,
            style=discord.TextStyle.long
            if self.option.is_long
            else discord.TextStyle.short,
        )
        self.add_item(self.option_input)

    async def on_submit(self, interaction: discord.Interaction, /) -> None:
        option_value = self.option_input.value
        conversion_success = await self.announcement_builder.announcement.set_option(
            self.option, option_value, guild=interaction.guild
        )
        item = discord.utils.get(
            self.announcement_builder.view.children, custom_id=self.option.id
        )

        if conversion_success and not option_value:
            item.style = discord.ButtonStyle.gray
            await self.announcement_builder.view._update(interaction)
        elif conversion_success:
            item.style = discord.ButtonStyle.green
            await self.announcement_builder.view._update(interaction)
        else:
            await interaction.response.send_message(
                "Could not find that role or channel.", ephemeral=True
            )


class OptionButton(discord.ui.Button):
    def __init__(
        self, announcement_builder: AnnouncementBuilder, *args, **kwargs
    ) -> None:
        super().__init__(*args, **kwargs)
        self.announcement_builder = announcement_builder

    async def callback(self, interaction: discord.Interaction, /) -> None:
        await self.announcement_builder.view.button_callback(interaction, self)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(AnnouncementCog(bot))
