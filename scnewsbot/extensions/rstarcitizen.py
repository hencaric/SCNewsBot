import discord
import asyncio
from discord.ext import commands, tasks
from utils import Config
from typing import Union

MEMBER_COUNT_CHANNELS: tuple[int] = (
    1223778123472965755,
    1225449497124012134,
)

class RStarCitizen(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._last_member = None

    @commands.command(description='Modmail Close Message')
    async def mmc(self, ctx):
        await ctx.reply("```=aclose Situation resolved, please only reply if there is something else.```")

#    @commands.Cog.listener()
#    async def on_ready(self) -> None:
#        for channel_id in MEMBER_COUNT_CHANNELS:
#            self.update_member_count.start(channel_id)

#    @tasks.loop(hours = 12)
#    async def update_member_count(self, channel_id: int) -> None:
#        for channel_id in MEMBER_COUNT_CHANNELS:
#            channel = self.bot.get_channel(channel_id)
#            member_count = channel.guild.member_count
#            await channel.edit(name=f"Members: {member_count}")

#    @commands.command(description='Update Member Count Channel')
#    async def mc(self, channel_id: int):
#        for channel_id in MEMBER_COUNT_CHANNELS:
#            channel = self.bot.get_channel(channel_id)
#            member_count = channel.guild.member_count
#            await channel.edit(name=f"Members: {member_count}")

async def setup(bot):
    await bot.add_cog(RStarCitizen(bot))