import os
from discord.ext import commands
import discord
from dotenv import load_dotenv
import tracemalloc

# Start tracing memory allocations
tracemalloc.start()

load_dotenv()

TOKEN = os.getenv('BOT_TOKEN')
GUILD_ID = int(os.getenv('GUILD_ID'))

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    print('------')
    try:
        for filename in os.listdir('./cogs'):
            if filename.endswith('.py'):
                await bot.load_extension(f'cogs.{filename[:-3]}')
        print("All cogs loaded successfully.")
    except Exception as e:
        print(f"Error loading cogs: {e}")

    # Sync guild-specific commands
    try:
        guild = discord.Object(id=GUILD_ID)
        await bot.tree.sync(guild=guild)
        print(f"Commands synced to guild {GUILD_ID}.")
    except Exception as e:
        print(f"Failed to sync commands: {e}")

    # Print memory allocation statistics
    snapshot = tracemalloc.take_snapshot()
    top_stats = snapshot.statistics('lineno')

    print("[ Top 10 memory allocations ]")
    for stat in top_stats[:10]:
        print(stat)

bot.run(TOKEN)
