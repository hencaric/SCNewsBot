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
- New Wave: `@SC Patch Notes - 3.XX Wave X Release`
- PTU Update: `@SC Patch Notes - 3.XX PTU Update`
- Live Update: `@SC Patch Notes - 3.XX LIVE Update`

**SC News**
- ISC: `@SC News - Inside Star Citizen`
- SCL: `@SC News - Star Citizen Live`
- Progress Tracker: `@SC News - Progress Tracker Update`
- Roadmap: `@SC News - Roadmap Roundup`
- SC Monthly Report: `@SC News - Star Citizen Monthly Report`
- SQ42 Monthly Report: `@SC News - Squadron 42 Monthly Report`
- Dynamic Event: `@SC News - Event Name PU/PTU`

**General News**
- Sneak Peek: `@General News - Weekly Sneak Peek`
- Lore Post: `@General News - Lore Post: Name`
- Dev Reply: `@General News - Dev Reply`
- Subscriber Items: `@General News - Month Subscriber Promotions`
- JP: `@General News - Jump Point`
"""
CHANNELS = """\
Patch Notes - `585952222853201941`
SC News - `569635458183856149`
General News - `803341100618219540`
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
    @commands.command(brief="Shows all the channel IDs for announcements.")
    async def channels(self, ctx: commands.Context) -> None:
        await ctx.reply(
            embed=discord.Embed(color=self.bot.config.embed_color, description=CHANNELS)
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(TemplatesCog(bot))
