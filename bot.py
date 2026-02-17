import os
from typing import Any

import discord
from discord import app_commands
from dotenv import load_dotenv

from state import load_state

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = os.getenv("GUILD_ID")

if TOKEN is None:
    raise RuntimeError("DISCORD_TOKEN is not set in .env")

if GUILD_ID is None:
    raise RuntimeError("GUILD_ID is not set in .env")

GUILD = discord.Object(id=int(GUILD_ID))


class WheatleyClient(discord.Client):
    def __init__(self, *, intents: discord.Intents) -> None:
        super().__init__(intents=intents)
        self.state: dict[str, Any] = load_state()
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self) -> None:
        self.tree.copy_global_to(guild=GUILD)
        await self.tree.sync(guild=GUILD)
        print(f"Synced commands to guild {GUILD_ID}")

    async def on_ready(self) -> None:
        user = self.user
        if user is None:
            print("Logged in, but self.user is None")
            return
        print(f"Logged in as {user} (ID: {user.id})")
        print(f"Number of users: {len(self.state['users'])}")
        print("------")


intents = discord.Intents.default()
client = WheatleyClient(intents=intents)

# Register all command modules
from commands import games, availability, matchmaking  # noqa: E402

games.setup(client, GUILD)
availability.setup(client, GUILD)
matchmaking.setup(client, GUILD)

if __name__ == "__main__":
    client.run(TOKEN)
