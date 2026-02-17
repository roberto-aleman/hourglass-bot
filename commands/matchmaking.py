from datetime import datetime, timezone
from typing import cast

import discord
from discord import app_commands

client: discord.Client
GUILD: discord.Object


def setup(c: discord.Client, guild: discord.Object) -> None:
    global client, GUILD
    client = c
    GUILD = guild
    _register_commands()


def _register_commands() -> None:
    from bot import WheatleyClient

    tree = cast(WheatleyClient, client).tree

    @tree.command(name="ready-to-play", description="Find available players who share your games.", guild=GUILD)
    async def ready_to_play(interaction: discord.Interaction, game: str | None = None) -> None:
        wheatley = cast(WheatleyClient, interaction.client)
        now_utc = datetime.now(timezone.utc)

        matches = wheatley.db.find_ready_players(interaction.user.id, now_utc, game_filter=game)

        if not matches:
            if game:
                message = f'No one is available right now for "{game}".'
            else:
                message = "No one with matching games is available right now."
            await interaction.response.send_message(message, ephemeral=True)
            return

        lines: list[str] = []
        for user_id, common in matches:
            mention = f"<@{user_id}>"
            games_str = ", ".join(common)
            lines.append(f"{mention} — {games_str}")

        header = "Players available now:"
        message = header + "\n" + "\n".join(lines)
        await interaction.response.send_message(message)
