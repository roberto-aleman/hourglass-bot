from typing import Protocol, cast

import discord
from discord import app_commands

from state import Database

EMBED_COLOR = 0x5865F2
SUCCESS_COLOR = 0x57F287


def setup_hints(db: Database, user_id: int) -> list[str]:
    """Return a list of setup steps the user still needs to complete."""
    hints: list[str] = []
    if not db.list_games(user_id):
        hints.append("Add games with `/add-game`")
    if not db.get_timezone(user_id):
        hints.append("Set your timezone with `/set-timezone`")
    else:
        avail = db.get_availability(user_id)
        if not any(avail.values()):
            hints.append("Set your availability with `/set-availability`")
    return hints


class BotClient(Protocol):
    db: Database
    tree: app_commands.CommandTree


def get_bot(interaction: discord.Interaction) -> BotClient:
    return cast(BotClient, interaction.client)


async def autocomplete_user_games(
    interaction: discord.Interaction, current: str,
) -> list[app_commands.Choice[str]]:
    """Suggest from the invoker's own game list."""
    bot = get_bot(interaction)
    games = bot.db.list_games(interaction.user.id)
    lower = current.lower()
    return [
        app_commands.Choice(name=g, value=g)
        for g in games if lower in g.lower()
    ][:25]


async def autocomplete_all_games(
    interaction: discord.Interaction, current: str,
) -> list[app_commands.Choice[str]]:
    """Suggest from all known games across all users."""
    bot = get_bot(interaction)
    games = bot.db.all_game_names()
    lower = current.lower()
    return [
        app_commands.Choice(name=g, value=g)
        for g in games if lower in g.lower()
    ][:25]
