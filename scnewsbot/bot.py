import subprocess
from discord.ext import commands
import discord
from utils import Config

VERSION = "1.0.3"
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
        print("The bot is now ready.")

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

    @commands.hybrid_command(description="Shows you some info about the bot.")
    async def info(self, ctx: commands.Context) -> None:
        embed = discord.Embed(
            color=self.bot.config.embed_color,
            title="Info",
            description="SCNewsBot is a Discord bot created for the r/starcitizen\n Discord server to help with writing news posts.",
        )
        embed.add_field(
            name="Version", value=f"v{self.bot.version}+{self._get_version()}"
        )
        embed.add_field(
            name="Library", value=f"discord.py v{discord.__version__}", inline=False
        )
        embed.add_field(
            name="Authors",
            value=f"Ian (<@1088892000348151839>), and mudkip (<@998070081709932654>)",
        )
        view = discord.ui.View()
        view.add_item(
            discord.ui.Button(
                label="Source Code",
                url="https://github.com/mudkipdev/scnewsbot",
                style=discord.ButtonStyle.link,
            )
        )
        await ctx.reply(embed=embed, view=view, mention_author=False)
