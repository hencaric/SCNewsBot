import discord
import asyncio
from discord.ext import commands, tasks
from utils import Config
from typing import Union

class RStarCitizen(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._last_member = None

    @commands.command(description='Modmail Close Message')
    async def mmc(self, ctx):
        await ctx.reply("```=aclose Situation resolved, please only reply if there is something else.```")

    @tasks.loop(hours=1)
    async def update_member_count(self):
        guild = self.bot.get_guild(82210263440306176)  # Replace YOUR_GUILD_ID with your actual guild ID
        channel = guild.get_channel(1223778123472965755)  # Replace YOUR_CHANNEL_ID with your actual channel ID

        member_count = len(guild.members)
        await channel.edit(name=f'Members: {member_count}')

    @commands.Cog.listener()
    async def on_ready(self):
        print('MemberCount cog is ready.')
        self.update_member_count.start()

async def setup(bot):
    await bot.add_cog(RStarCitizen(bot))