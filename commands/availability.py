from typing import cast

import discord
from discord import app_commands

from state import (
    DAY_KEYS,
    format_user_availability,
    get_timezone_from_state,
    save_state,
    set_day_availability_in_state,
    set_timezone_in_state,
    validate_time,
    validate_timezone,
)

# These will be set by bot.py after client creation
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

    @tree.command(name="set-timezone", description="Set your timezone.", guild=GUILD)
    async def set_timezone(interaction: discord.Interaction, tz: str) -> None:
        if not validate_timezone(tz):
            await interaction.response.send_message(
                f'"{tz}" is not a valid timezone. Use an IANA name like "America/New_York".',
                ephemeral=True,
            )
            return
        wheatley = cast(WheatleyClient, interaction.client)
        set_timezone_in_state(wheatley.state, interaction.user.id, tz)
        save_state(wheatley.state)
        await interaction.response.send_message(f'Set "{tz}" as your timezone.', ephemeral=True)

    @tree.command(name="my-timezone", description="Show your saved timezone.", guild=GUILD)
    async def my_timezone(interaction: discord.Interaction) -> None:
        wheatley = cast(WheatleyClient, interaction.client)
        tz = get_timezone_from_state(wheatley.state, interaction.user.id)
        if tz:
            message = f"Your timezone: {tz}"
        else:
            message = "You don't have a timezone saved."
        await interaction.response.send_message(message, ephemeral=True)

    @tree.command(name="set-availability", description="Set or clear your availability for a single weekday.", guild=GUILD)
    @app_commands.choices(day=[app_commands.Choice(name=d, value=d) for d in DAY_KEYS])
    async def set_availability(
        interaction: discord.Interaction,
        day: app_commands.Choice[str],
        start: str | None = None,
        end: str | None = None,
    ) -> None:
        wheatley = cast(WheatleyClient, interaction.client)
        day_key = day.value

        if (start and not end) or (end and not start):
            await interaction.response.send_message(
                "You must provide both start and end, or neither to clear.", ephemeral=True,
            )
            return

        if start and end:
            if not validate_time(start) or not validate_time(end):
                await interaction.response.send_message(
                    "Times must be in HH:MM format (e.g. 18:00).", ephemeral=True,
                )
                return

        set_day_availability_in_state(wheatley.state, interaction.user.id, day_key, start, end)
        save_state(wheatley.state)

        if not start or not end:
            message = f"Cleared your availability on {day_key}."
        else:
            message = f"Set your availability on {day_key} from {start} to {end}."
        await interaction.response.send_message(message, ephemeral=True)

    @tree.command(name="my-availability", description="Show your saved weekly availability.", guild=GUILD)
    async def my_availability(interaction: discord.Interaction) -> None:
        wheatley = cast(WheatleyClient, interaction.client)
        summary = format_user_availability(wheatley.state, interaction.user.id)
        await interaction.response.send_message(summary, ephemeral=True)
