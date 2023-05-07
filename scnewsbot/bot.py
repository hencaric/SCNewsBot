from discord.ext import commands
import discord
from utils import Config

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
        )
        self.config = config

    async def setup_hook(self) -> None:
        for extension in self.config.extensions:
            await self.load_extension(extension)
