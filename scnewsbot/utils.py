from discord.ext import commands


class Config:
    def __init__(self, config: dict):
        self.config = config

    @property
    def debug(self) -> bool:
        return self.config.get("debug", False)

    @property
    def prefix(self) -> str:
        return self.config["bot"].get("prefix", "sc ")

    @property
    def extensions(self) -> list:
        return self.config["bot"].get("extensions", ["jishaku"])

    @property
    def allowed_guilds(self) -> list:
        return self._get_allowed_objects("allowed_guilds")

    @property
    def allowed_roles(self) -> list:
        return self._get_allowed_objects("allowed_roles")

    @property
    def allowed_users(self) -> list:
        return self._get_allowed_objects("allowed_users")

    def _get_allowed_objects(self, object_name, /) -> list:
        allowed_objects = self.config["permissions"].get(object_name, [])
        if self.debug:
            allowed_objects += self.config["permissions"]["debug"].get(object_name, [])

        return allowed_objects


def can_publish_announcements(ctx: commands.Context) -> bool:
    if not ctx.guild:
        return False

    if ctx.author.id in ctx.bot.config.allowed_users:
        return True

    if ctx.guild.id in ctx.bot.config.allowed_guilds:
        for allowed_role in ctx.bot.config.allowed_roles:
            if allowed_role in ctx.author._roles:
                return True

    return False
