import subprocess
from discord.ext import commands
from discord.ui import Button
import discord
import datetime
from utils import Config

VERSION = "1.0.4"
INTENTS = discord.Intents.default()
INTENTS.message_content = True
INTENTS.members = True


class Bot(commands.Bot):
    def __init__(self, config: Config, /) -> None:
        super().__init__(
            intents=INTENTS,
            command_prefix=commands.when_mentioned_or(config.prefix),
            allowed_mentions=discord.AllowedMentions(everyone=False),
            case_insensitive=True,
            activity=discord.Activity(
                type=discord.ActivityType.watching, name="the devs..."
            ),
        )
        self.config = config
        self.version = VERSION

    async def setup_hook(self) -> None:
        for extension in self.config.extensions:
            await self.load_extension(extension)

        await self.add_cog(CoreCog(self))


class CoreCog(commands.Cog, name="Core"):
    def __init__(self, bot: Bot) -> None:
        self.bot = bot

    def _get_version(self) -> str:
        return (
            subprocess.check_output(["git", "rev-parse", "--short", "HEAD"])
            .decode("ascii")
            .strip()
        )

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        print("The News Bot is now ready.")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if (
            message.channel.id in self.bot.config.publish_channels
            and message.channel.type is discord.ChannelType.news
        ):
            try:
                await message.publish()
            except discord.Forbidden:
                pass

#    @commands.Cog.listener()
#    async def on_message(self, message):
#        if message.channel.id == 649390966259580929 and message.author.id != 1091116499936223252:
#            if message.embeds:
#                for embed in message.embeds:
#                    reply_channel = self.bot.get_channel(611922107345141760)
#                    if "Patch Notes" in embed.title:
#                        await reply_channel.send(f"<@&159107041896562688> CIG has published new [Patch Notes](<{embed.url}>).")
#                    elif "Galactapedia" in embed.title:
#                        await reply_channel.send(f"<@&159107041896562688> CIG has published a new [Galactapedia update](<{embed.url}>).")
#                    elif "This Week in Star Citizen" in embed.title:
#                        await reply_channel.send(f"<@&159107041896562688> CIG has published a new [TWISC](<{embed.url}>).")
#                    elif "Monthly Report" in embed.title:
#                        await reply_channel.send(f"<@&159107041896562688> CIG has published a new [Monthly Report](<{embed.url}>).")

    @commands.hybrid_command(description="Shows you some info about the bot.")
    async def info(self, ctx: commands.Context) -> None:
        embed = discord.Embed(
            color=self.bot.config.embed_color,
            title="Info",
            description="The SC News Bot is a bot created for the r/starcitizen Discord server to help with writing news posts.",
        )
        embed.add_field(
            name="Version", value=f"v{self.bot.version}+{self._get_version()}"
        )
        embed.add_field(
            name="Library", value=f"discord.py v{discord.__version__}", inline=False
        )
        embed.add_field(
            name="Authors",
            value=f"<@288522211164160010> and <@998070081709932654>",
        )
        embed.add_field(
            name="Production Code",
            value=f"[Link](https://github.com/hencaric/SCNewsBot)",
        )
        view = discord.ui.View()
        view.add_item(
            discord.ui.Button(
                label="Source Code for Public Use",
                url="https://github.com/mudkipdev/scnewsbot",
                style=discord.ButtonStyle.link,
            )
        )
        await ctx.reply(embed=embed, view=view, mention_author=False)
