from datetime import timezone
from logging import getLogger
from typing import Optional

from dateutil.parser import ParserError
from dateutil.parser import parse as parse_date
from discord.ext import commands

from ..utils import can_publish_announcements

log = getLogger(__name__)


FORMATS = ["d", "s", "S", "D", "t", "T", "f", "F", "R"]


class DtConverterCog(commands.Cog, name="DTConverter"):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.check(can_publish_announcements)
    @commands.command(brief="Convert dt to discord timestamp")
    async def convert(
        self, ctx: commands.Context, format_: str, timestamps: list[str]
    ) -> None:
        """
        Attempts to convert a given datetime string into a Discord epoch timestamp.
        Available formats:
            - d: 11/18/2025
            - s: 11/18/2025 4:11 PM
            - s: 11/18/2025 4:11 PM
            - D: November 18, 2025
            - t: 4:00 PM
            - T: 4:00:00 PM
            - f:  November 18th, 2025 4:00 PM
            - F: Tuesday, November 18th, 2025 4:00 PM
            - R: 1 hour ago
        """

        if format_ not in FORMATS:
            await ctx.reply(
                f"Invalid format: {format_}. "
                f"Please use on of the following: {[fmt for fmt in FORMATS]}"
            )
            return

        results: list[str] = []
        for timestamp in timestamps:
            if res := self.try_convert_dt(timestamp):
                post = format_[-1]
                results.append(f"<t:{res}:{post}>")
        if not results:
            await ctx.reply("Failed to convert any valid datetime strings")
            return
        await ctx.reply(self.fmt_results(results))

    @staticmethod
    def fmt_results(results: list[str]) -> str:
        """Prettify the message string before having the bot respond with the results"""
        msg = "Retrieved the following results:\n"
        result_lines = [f" - {result} `{result}`" for result in results]

        return msg + "\n".join(result_lines)

    @staticmethod
    def try_convert_dt(time_txt: str) -> Optional[int]:
        """
        Takes a given string and attempts to convert into a python datetime object
        then passes that epoch into a string of the given format.
        """
        try:
            if dt := parse_date(time_txt):
                if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return round(dt.timestamp())
        except ParserError:
            log.error(f"Unknown datetime format from {time_txt}")
        except OverflowError:
            log.error(
                f"{time_txt} would return too large of an integer. How'd you do that?"
            )
        except Exception:
            log.exception(
                f"Failed to convert {time_txt} to epoch timestamp with error:"
            )
        return None
