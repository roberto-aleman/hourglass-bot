from typing import cast

import discord
from discord import app_commands

from state import (
    add_game_to_state,
    get_common_games,
    list_games_from_state,
    remove_game_from_state,
    save_state,
)

# These will be set by bot.py after client creation
client: discord.Client
GUILD: discord.Object


def setup(c: discord.Client, guild: discord.Object) -> None:
    global client, GUILD
    client = c
    GUILD = guild
    _register_commands()


class RemoveGameSelect(discord.ui.Select):
    """Select menu that lets a user pick one of their games to remove."""

    def __init__(self, games: list[str]) -> None:
        options = [discord.SelectOption(label=game, value=game) for game in games[:25]]
        super().__init__(
            placeholder="Select a game to remove...",
            min_values=1,
            max_values=1,
            options=options,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        from bot import WheatleyClient

        wheatley = cast(WheatleyClient, interaction.client)
        selected_game = self.values[0]

        removed = remove_game_from_state(wheatley.state, interaction.user.id, selected_game)
        if removed:
            save_state(wheatley.state)
            message = f'Removed "{selected_game}" from your games.'
        else:
            message = f'"{selected_game}" is no longer in your games.'

        self.disabled = True
        await interaction.response.edit_message(content=message, view=self.view)


class RemoveGameView(discord.ui.View):
    def __init__(self, games: list[str]) -> None:
        super().__init__(timeout=60)
        self.add_item(RemoveGameSelect(games))


def _register_commands() -> None:
    from bot import WheatleyClient

    tree = cast(WheatleyClient, client).tree

    @tree.command(name="add-game", description="Add a game to your list.", guild=GUILD)
    async def add_game(interaction: discord.Interaction, game: str) -> None:
        wheatley = cast(WheatleyClient, interaction.client)
        add_game_to_state(wheatley.state, interaction.user.id, game)
        save_state(wheatley.state)
        await interaction.response.send_message(f'Added "{game}" to your games.', ephemeral=True)

    @tree.command(name="remove-game", description="Remove a game from your list.", guild=GUILD)
    async def remove_game(interaction: discord.Interaction, game: str) -> None:
        wheatley = cast(WheatleyClient, interaction.client)
        removed = remove_game_from_state(wheatley.state, interaction.user.id, game)
        if removed:
            save_state(wheatley.state)
            message = f'Removed "{game}" from your games.'
        else:
            message = f'"{game}" was not found in your games.'
        await interaction.response.send_message(message, ephemeral=True)

    @tree.command(name="remove-game-menu", description="Remove a game from your list using a dropdown menu.", guild=GUILD)
    async def remove_game_menu(interaction: discord.Interaction) -> None:
        wheatley = cast(WheatleyClient, interaction.client)
        games = list_games_from_state(wheatley.state, interaction.user.id)
        if not games:
            await interaction.response.send_message("You don't have any games saved.", ephemeral=True)
            return
        await interaction.response.send_message("Select a game to remove:", view=RemoveGameView(games), ephemeral=True)

    @tree.command(name="list-games", description="List the games you have saved.", guild=GUILD)
    async def list_games(interaction: discord.Interaction) -> None:
        wheatley = cast(WheatleyClient, interaction.client)
        games = list_games_from_state(wheatley.state, interaction.user.id)
        if games:
            message = f"Your games: {', '.join(games)}"
        else:
            message = "You don't have any games saved."
        await interaction.response.send_message(message, ephemeral=True)

    @tree.command(name="common-games", description="Show games you have in common with another user.", guild=GUILD)
    async def common_games(interaction: discord.Interaction, other: discord.User) -> None:
        wheatley = cast(WheatleyClient, interaction.client)
        common = get_common_games(wheatley.state, interaction.user.id, other.id)
        if not common:
            message = f"You and {other.mention} don't have any games in common."
        else:
            message = f"You and {other.mention} have these common games: {', '.join(common)}."
        await interaction.response.send_message(message, ephemeral=True)
