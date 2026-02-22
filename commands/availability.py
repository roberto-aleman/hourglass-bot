from zoneinfo import available_timezones

import discord
from discord import app_commands
from discord.ext import commands

from commands.helpers import EMBED_COLOR, fmt_day, fmt_time
from state import DAY_KEYS, Database, validate_time

_ALL_TIMEZONES = sorted(available_timezones())
_ALL_TIMEZONES_SET = set(_ALL_TIMEZONES)

# Common abbreviations -> IANA timezone for autocomplete friendliness
_TZ_ALIASES: dict[str, str] = {
    "PST": "America/Los_Angeles", "PDT": "America/Los_Angeles", "Pacific": "America/Los_Angeles",
    "MST": "America/Denver", "MDT": "America/Denver", "Mountain": "America/Denver",
    "CST": "America/Chicago", "CDT": "America/Chicago", "Central": "America/Chicago",
    "EST": "America/New_York", "EDT": "America/New_York", "Eastern": "America/New_York",
    "AKST": "America/Anchorage", "AKDT": "America/Anchorage", "Alaska": "America/Anchorage",
    "HST": "Pacific/Honolulu", "Hawaii": "Pacific/Honolulu",
    "GMT": "Europe/London", "BST": "Europe/London",
    "CET": "Europe/Berlin", "CEST": "Europe/Berlin",
    "EET": "Europe/Bucharest", "EEST": "Europe/Bucharest",
    "IST": "Asia/Kolkata",
    "JST": "Asia/Tokyo",
    "AEST": "Australia/Sydney", "AEDT": "Australia/Sydney",
}
# Build searchable list: (display_name, iana_value)
_TZ_ALIAS_ENTRIES = [(f"{abbr} — {iana}", iana) for abbr, iana in _TZ_ALIASES.items()]

DAY_CHOICES = [app_commands.Choice(name=fmt_day(d), value=d) for d in DAY_KEYS]

# Pre-built 15-minute interval time choices: display "6:00 PM", store "18:00"
_TIME_CHOICES = []
for _h in range(24):
    for _m in (0, 15, 30, 45):
        _val = f"{_h:02d}:{_m:02d}"
        _TIME_CHOICES.append((_val, fmt_time(_val)))


async def autocomplete_time(
    interaction: discord.Interaction, current: str,
) -> list[app_commands.Choice[str]]:
    lower = current.lower().strip()
    return [
        app_commands.Choice(name=display, value=val)
        for val, display in _TIME_CHOICES
        if lower in display.lower() or lower in val
    ][:25]


async def autocomplete_timezone(
    interaction: discord.Interaction, current: str,
) -> list[app_commands.Choice[str]]:
    lower = current.lower()
    results: list[app_commands.Choice[str]] = []
    seen: set[str] = set()
    # Abbreviation matches first (PST, Eastern, etc.)
    for display, iana in _TZ_ALIAS_ENTRIES:
        if lower in display.lower() and iana not in seen:
            results.append(app_commands.Choice(name=display, value=iana))
            seen.add(iana)
    # Then standard IANA matches
    for tz in _ALL_TIMEZONES:
        if lower in tz.lower() and tz not in seen:
            results.append(app_commands.Choice(name=tz, value=tz))
            seen.add(tz)
        if len(results) >= 25:
            break
    return results[:25]


class AvailabilityCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @property
    def db(self) -> Database:
        return self.bot.db  # type: ignore[attr-defined]

    @app_commands.command(name="set-timezone", description="Set your timezone.")
    @app_commands.describe(timezone="Your timezone (e.g. PST, Eastern, Europe/London)")
    @app_commands.autocomplete(timezone=autocomplete_timezone)
    async def set_timezone(self, interaction: discord.Interaction, timezone: str) -> None:
        if timezone not in _ALL_TIMEZONES_SET:
            await interaction.response.send_message(
                f'"{timezone}" is not a valid timezone. Start typing to see suggestions.', ephemeral=True,
            )
            return
        self.db.set_timezone(interaction.user.id, timezone)
        await interaction.response.send_message(f"Set your timezone to {timezone}.", ephemeral=True)

    @app_commands.command(name="my-timezone", description="Show your saved timezone.")
    async def my_timezone(self, interaction: discord.Interaction) -> None:
        tz = self.db.get_timezone(interaction.user.id)
        if tz:
            message = f"Your timezone: {tz}"
        else:
            message = "You don't have a timezone saved."
        await interaction.response.send_message(message, ephemeral=True)

    @app_commands.command(name="set-availability", description="Add a time slot for a weekday.")
    @app_commands.describe(day="Day of the week", start="Start time", end="End time (can be past midnight)")
    @app_commands.choices(day=DAY_CHOICES)
    @app_commands.autocomplete(start=autocomplete_time, end=autocomplete_time)
    async def set_availability(
        self, interaction: discord.Interaction,
        day: app_commands.Choice[str],
        start: str,
        end: str,
    ) -> None:
        if not validate_time(start) or not validate_time(end):
            await interaction.response.send_message(
                "Please pick a time from the suggestions.", ephemeral=True,
            )
            return

        if start == end:
            await interaction.response.send_message(
                "Start and end times must be different.", ephemeral=True,
            )
            return

        slots = self.db.add_day_availability(interaction.user.id, day.value, start, end)
        schedule = ", ".join(f"{fmt_time(s['start'])}–{fmt_time(s['end'])}" for s in slots)
        await interaction.response.send_message(
            f"Updated {fmt_day(day.value)}: {schedule}", ephemeral=True,
        )

    @app_commands.command(name="clear-availability", description="Clear all time slots for a weekday.")
    @app_commands.describe(day="Day of the week to clear")
    @app_commands.choices(day=DAY_CHOICES)
    async def clear_availability(
        self, interaction: discord.Interaction,
        day: app_commands.Choice[str],
    ) -> None:
        self.db.clear_day_availability(interaction.user.id, day.value)
        await interaction.response.send_message(
            f"Cleared all availability on {fmt_day(day.value)}.", ephemeral=True,
        )

    @app_commands.command(name="my-availability", description="Show your saved weekly availability.")
    async def my_availability(self, interaction: discord.Interaction) -> None:
        uid = interaction.user.id
        tz = self.db.get_timezone(uid)
        availability = self.db.get_availability(uid)

        embed = discord.Embed(title="Your Availability", color=EMBED_COLOR)
        embed.add_field(name="Timezone", value=tz or "not set", inline=False)

        has_any = False
        for day in DAY_KEYS:
            slots = availability[day]
            if slots:
                has_any = True
                value = ", ".join(f"{fmt_time(s['start'])}–{fmt_time(s['end'])}" for s in slots)
                embed.add_field(name=fmt_day(day), value=value, inline=True)

        if not has_any:
            embed.add_field(name="Schedule", value="No availability set.", inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(AvailabilityCog(bot))
