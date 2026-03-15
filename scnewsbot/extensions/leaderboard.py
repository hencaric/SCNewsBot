import discord
from discord.ext import commands
from datetime import datetime, timedelta
import json
import os

# CONFIG
LEADERBOARD_FILE = "leaderboard.json"
EMBED_COLOR = discord.Color.gold()
TOP_EMOJIS = ["🥇", "🥈", "🥉"]
USERS_PER_PAGE = 5

# DATA
class LeaderboardData:

    def __init__(self, filepath=LEADERBOARD_FILE):
        self.filepath = filepath
        self.data = {}
        self.load()

    def load(self):
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    self.data = json.load(f)
            except Exception:
                self.data = {}
        else:
            self.data = {}

    def save(self):
        with open(self.filepath, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=4)

    # RECORD POST
    def record_post(self, user_id: int):

        uid = str(user_id)
        now = datetime.utcnow().isoformat()

        if uid not in self.data:
            self.data[uid] = {
                "count": 0,
                "last_post": now,
                "posts": []
            }

        self.data[uid]["count"] += 1
        self.data[uid]["last_post"] = now
        self.data[uid]["posts"].append(now)

        self.save()

    # SORT
    def get_sorted(self):

        return sorted(
            self.data.items(),
            key=lambda item: (-item[1]["count"], item[1]["last_post"])
        )

    # USER STATS
    def user_30_days(self, posts):

        cutoff = datetime.utcnow() - timedelta(days=30)

        return sum(
            1 for p in posts
            if datetime.fromisoformat(p) >= cutoff
        )

    def user_year(self, posts):

        year = datetime.utcnow().year

        return sum(
            1 for p in posts
            if datetime.fromisoformat(p).year == year
        )

    # GLOBAL STATS
    def global_stats(self):

        cutoff = datetime.utcnow() - timedelta(days=30)
        year = datetime.utcnow().year

        total30 = 0
        totalYear = 0
        totalAll = 0

        for user in self.data.values():

            posts = user.get("posts", [])

            totalAll += user.get("count", 0)

            for p in posts:

                dt = datetime.fromisoformat(p)

                if dt >= cutoff:
                    total30 += 1

                if dt.year == year:
                    totalYear += 1

        return total30, totalYear, totalAll


leaderboard_data = LeaderboardData()

# VIEW
class LeaderboardView(discord.ui.View):

    def __init__(self, ctx, users):

        super().__init__(timeout=180)

        self.ctx = ctx
        self.users = users
        self.page = 0
        self.max_page = (len(users) - 1) // USERS_PER_PAGE

    def build_embed(self):

        embed = discord.Embed(
            title="📊 Announcement Leaderboard",
            color=EMBED_COLOR,
            timestamp=datetime.utcnow()
        )

        start = self.page * USERS_PER_PAGE
        end = start + USERS_PER_PAGE

        page_users = self.users[start:end]

        for i, (uid, stats) in enumerate(page_users, start=start+1):

            member = self.ctx.guild.get_member(int(uid))
            name = member.display_name if member else f"User {uid}"

            posts = stats.get("posts", [])

            alltime = stats["count"]
            last30 = leaderboard_data.user_30_days(posts)
            year = leaderboard_data.user_year(posts)

            last_post = datetime.fromisoformat(stats["last_post"]).strftime("%Y-%m-%d %H:%M UTC")

            if i <= 3:
                title = f"{TOP_EMOJIS[i-1]} {name}"
            else:
                title = name

            value = (
                f"**All Time:** {alltime}\n"
                f"**30 Days:** {last30}\n"
                f"**Year:** {year}\n"
                f"**Last:** {last_post}"
            )

            if int(uid) == self.ctx.author.id:
                value += " 👈 You"

            embed.add_field(name=title, value=value, inline=False)

        # GLOBAL STATS
        total30, totalYear, totalAll = leaderboard_data.global_stats()

        embed.add_field(
            name="📈 Server Announcement Stats",
            value=(
                f"**Last 30 Days:** {total30}\n"
                f"**This Year:** {totalYear}\n"
                f"**All Time:** {totalAll}"
            ),
            inline=False
        )

        embed.set_footer(text=f"Page {self.page+1}/{self.max_page+1}")

        return embed

    # BUTTONS
    @discord.ui.button(label="⬅ Previous", style=discord.ButtonStyle.secondary)
    async def previous(self, interaction: discord.Interaction, button: discord.ui.Button):

        if self.page > 0:
            self.page -= 1

        await interaction.response.edit_message(embed=self.build_embed(), view=self)

    @discord.ui.button(label="🧑 My Rank", style=discord.ButtonStyle.primary)
    async def my_rank(self, interaction: discord.Interaction, button: discord.ui.Button):

        uid = str(interaction.user.id)

        for index, (user_id, _) in enumerate(self.users):

            if user_id == uid:

                self.page = index // USERS_PER_PAGE
                break

        await interaction.response.edit_message(embed=self.build_embed(), view=self)

    @discord.ui.button(label="Next ➡", style=discord.ButtonStyle.secondary)
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):

        if self.page < self.max_page:
            self.page += 1

        await interaction.response.edit_message(embed=self.build_embed(), view=self)


# COG
class Leaderboard(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def leaderboard(self, ctx):

        users = leaderboard_data.get_sorted()

        if not users:
            await ctx.send("No announcements have been posted yet.")
            return

        view = LeaderboardView(ctx, users)

        await ctx.send(embed=view.build_embed(), view=view)


# HELPER
def record_announcement_post(user_id: int):

    leaderboard_data.record_post(user_id)


# SETUP
async def setup(bot):

    await bot.add_cog(Leaderboard(bot))



