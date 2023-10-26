from discord.ext import commands
import discord
from extensions.announcements import Announcement
from utils import can_publish_announcements

TEMPLATES: dict[str, Announcement] = {
    "isc": Announcement(title="Inside Star Citizen | [topic] - [subtopic]"),
    "scl": Announcement(title="Star Citizen Live | [topic] - [subtopic]"),
    "tracker": Announcement(title="Progress Tracker Update | [date]"),
    "roundup": Announcement(title="Roadmap Roundup | [date]"),
    "patchnotes": Announcement(
        title="Star Citizen Alpha X.XX.X XPTU.XXXXXXX Patch Notes"
    ),
    "galactapedia": Announcement(title="Weekly Sneak Peek | [date]"),
    "devreply": Announcement(title="Dev Reply | Topic"),
    "twisc": Announcement(
        title="This Week in Star Citizen | Week of [date]",
    ),
}
PING_PREVIEWS = """\
**Patch Notes**
- New Wave: `3.XX Wave X Release`
- PTU Update: `3.XX PTU Update`
- Live Update: `3.XX LIVE Update`

**SC News**
- ISC: `Inside Star Citizen`
- SCL: `Star Citizen Live`
- Progress Tracker: `Progress Tracker Update`
- Roadmap: `Roadmap Roundup`
- SC Monthly Report: `Star Citizen Monthly Report`
- SQ42 Monthly Report: `Squadron 42 Monthly Report`
- Dynamic Event: `Event Name PU/PTU`

**General News**
- Sneak Peek: `Weekly Sneak Peek`
- Lore Post: `Lore Post: Name`
- Dev Reply: `Dev Reply`
- Subscriber Items: `Month Subscriber Promotions`
- JP: `Jump Point`
"""
IDS = """\
__**Channels:**__
Server News - `1113146864804573285`
Patch Notes - `585952222853201941`
SC News - `569635458183856149`
General News - `803341100618219540`

__**Roles:**__
Server News - `1113152142300156004`
Patch Notes - `620025894559547412`
SC News - `620025828079697920`
General News - `803343410794594385`

__**Where to post what:**__
[Check here](https://discord.com/channels/82210263440306176/611922107345141760/1113905662217441330) for a guide on what post types go where.
"""


class TemplatesCog(commands.Cog, name="Templates"):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.templates = TEMPLATES

    @commands.guild_only()
    @commands.group(
        brief="Commands that help with designing embeds for the news system.",
        invoke_without_command=True,
    )
    async def templates(self, ctx: commands.Context) -> None:
        await ctx.send_help(ctx.command)

    @commands.check(can_publish_announcements)
    @templates.command(name="list")
    async def _list(self, ctx: commands.Context) -> None:
        templates = "\n".join([f"- {template}" for template in self.templates])
        await ctx.reply(f"Here are all of the available templates: ```\n{templates}```")

    @commands.check(can_publish_announcements)
    @templates.command()
    async def view(self, ctx: commands.Context, *, template_name: str) -> None:
        templates = {name.lower(): value for name, value in self.templates.items()}
        template_name = template_name.lower()
        template = templates.get(template_name)

        if not template:
            await ctx.reply(
                f"Could not find that template. Use `{ctx.prefix}templates list` to list all available templates."
            )

        embed = await template.get_embed(bot=self.bot)
        embed.remove_author()
        await ctx.reply(embed=embed)

    @commands.check(can_publish_announcements)
    @commands.command(brief='A shortcut to the "templates view" command.')
    async def template(self, ctx: commands.Context, *, template_name: str) -> None:
        await ctx.invoke(
            self.bot.get_command("templates").get_command("view"),
            template_name=template_name,
        )

    @commands.check(can_publish_announcements)
    @commands.command(name="previews", brief="Shows all the possible ping previews.")
    async def ping_previews(self, ctx: commands.Context) -> None:
        await ctx.reply(
            embed=discord.Embed(
                color=self.bot.config.embed_color, description=PING_PREVIEWS
            ),
            allowed_mentions=discord.AllowedMentions.none(),
        )

    @commands.check(can_publish_announcements)
    @commands.command(brief="Shows all the channel and role IDs for announcements.")
    async def ids(self, ctx: commands.Context) -> None:
        await ctx.reply(
            embed=discord.Embed(color=self.bot.config.embed_color, description=IDS)
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(TemplatesCog(bot))
