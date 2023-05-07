from __future__ import annotations

from typing import Any, Optional, Callable, Awaitable
from dataclasses import dataclass
from discord.ext import commands
import discord
from utils import can_publish_announcements

ANNOUNCEMENT_BUILDER_TIMEOUT = 1200
EMBED_THUMBNAIL = "https://imgur.com/MJnM3LU.png"


async def get_ping_message(message: discord.Message, /) -> Optional[discord.Message]:
    async for ping in message.channel.history(limit=1, after=message.created_at):
        if ping.author.id == message._state.user.id and ping.mentions:
            return ping


class AnnouncementCog(commands.Cog, name="Announcements"):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.guild_only()
    @commands.group(
        brief="Commands relating to the r/starcitizen Discord news system.",
        aliases=["announcement", "news", "embed"],
        invoke_without_command=True,
    )
    async def announcements(self, ctx: commands.Context) -> None:
        await ctx.send_help(ctx.command)

    @commands.check(can_publish_announcements)
    @announcements.command(brief="Creates and sends a new announcement.")
    async def create(self, ctx: commands.Context) -> None:
        announcement_builder = AnnouncementBuilder(owner=ctx.author)
        embed = await announcement_builder.get_embed(bot=self.bot)
        await ctx.send(embed=embed, view=announcement_builder.view)

    @commands.check(can_publish_announcements)
    @announcements.command(brief="Edits an existing announcement.")
    async def edit(self, ctx: commands.Context, message: discord.Message) -> None:
        announcement = await Announcement.from_message(message, bot=self.bot)
        announcement_builder = AnnouncementBuilder(
            edit_message=message, edit_announcement=announcement, owner=ctx.author
        )
        embed = await announcement_builder.get_embed(bot=self.bot)
        await ctx.send(embed=embed, view=announcement_builder.view)

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
        image_url: Optional[str] = None,
        channel: Optional[discord.abc.Messageable] = None,
        ping: Optional[discord.Role] = None,
        ping_preview: Optional[str] = None,
        author_id: Optional[int] = None,
        is_private: bool = False,
        will_notify: bool = False,
    ) -> None:
        self.title = title
        self.url = url
        self.description = description
        self.image_url = image_url
        self.channel = channel
        self.ping = ping
        self.ping_preview = ping_preview

        self.author_id = author_id
        self.is_private = is_private
        self.will_notify = will_notify

    async def set_option(
        self, option: Option, value: Any, *, guild: discord.Guild
    ) -> bool:
        if option is None:
            setattr(self, option.id, converted_value)
            return True

        if option.id == "channel":
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
            converted_value = value

        if converted_value is None:
            return False

        setattr(self, option.id, converted_value)
        return True

    async def get_embed(self, *, bot: commands.Bot) -> discord.Embed:
        embed = discord.Embed(
            color=bot.config.embed_color,
            title=self.title,
            url=self.url,
            description=self.description,
        )
        embed.set_image(url=self.image_url)
        if EMBED_THUMBNAIL:
            embed.set_thumbnail(url=EMBED_THUMBNAIL)

        if not self.is_private:
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

        return cls(
            title=embed.title,
            url=embed.url,
            description=embed.description,
            image_url=embed.image.url,
            channel=message.channel,
            ping=ping,
            ping_preview=ping_preview,
            author_id=author.id if author else None,
            is_private=embed.author is None,
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
        self.add_option(
            Option(
                id="description",
                name="Description",
                directions="Here are some directions.",
                is_long=True,
            )
        )
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

    @discord.ui.button(custom_id="private", label="Private", row=2)
    async def toggle_private(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        self.announcement_builder.announcement.is_private = (
            not self.announcement_builder.announcement.is_private
        )
        if self.announcement_builder.announcement.is_private:
            button.style = discord.ButtonStyle.green
        else:
            button.style = discord.ButtonStyle.gray

        await self._update(interaction)

    @discord.ui.button(
        custom_id="notification", label="Published", row=2, disabled=True
    )
    async def toggle_notification(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
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
                content=role.mention if role else None, embed=embed
            )
            return

        if not announcement.title and announcement.channel:
            await interaction.response.send_message(
                "You must have a title and channel selected!", ephemeral=True
            )
            return

        if announcement.ping_preview and not announcement.ping:
            await interaction.response.send_message(
                "You cannot have a ping preview selected without a ping!",
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            "Your announcement was posted! 🎉", ephemeral=True
        )
        self.stop()

        message = await announcement.channel.send(
            embed=await announcement.get_embed(bot=interaction.client),
        )
        if announcement.will_notify:
            await message.publish()

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
