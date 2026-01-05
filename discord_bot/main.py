# Discord Bot Service
# Main entry point for the Discord bot

import os
import logging
import discord
from app.auth import get_user_jwt
from discord.ext import commands
from dotenv import load_dotenv
from typing import Optional
from supabase import Client
from common.database import get_supabase_client, get_supabase

load_dotenv()

# Logging setup
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format='{"time":"%(asctime)s","level":"%(levelname)s","message":"%(message)s","name":"%(name)s"}',
)
logger = logging.getLogger(__name__)

# Bot configuration
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
COMMAND_PREFIX = os.getenv("COMMAND_PREFIX")

# API endpoints for other services
USER_SERVICE_URL = os.getenv("USER_SERVICE_URL")
PAYMENT_SERVICE_URL = os.getenv("PAYMENT_SERVICE_URL")
ITEM_SERVICE_URL = os.getenv("ITEM_SERVICE_URL")

# Bot intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

# Create bot instance
bot: commands.Bot = commands.Bot(command_prefix=COMMAND_PREFIX, intents=intents)
supabase: Optional[Client] = None


@bot.event
async def on_ready() -> None:
    """Called when the bot is ready and connected to Discord."""
    logger.info(f"Bot is ready! Logged in as {bot.user.name} ({bot.user.id})")
    logger.info(f"Connected to {len(bot.guilds)} guild(s)")
    global supabase
    try:
        supabase = get_supabase_client()
        logger.info("Supabase client ready")
    except Exception as e:
        logger.error(f"Failed to initialize Supabase client: {e}")
    
    # Set bot status
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name=f"{COMMAND_PREFIX}help"
        )
        
    )


@bot.event
async def on_command_error(ctx: commands.Context, error: Exception) -> None:
    """Global error handler for commands."""
    if isinstance(error, commands.CommandNotFound):
        await ctx.send(f"❌ Command not found. Use `{COMMAND_PREFIX}help` for available commands.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❌ Missing required argument: `{error.param.name}`")
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ You don't have permission to use this command.")
    else:
        logger.error(f"Command error: {error}")
        await ctx.send("❌ An error occurred while processing your command.")


@bot.command(name="ping")
async def ping(ctx: commands.Context) -> None:
    """Check if the bot is responsive."""
    latency = round(bot.latency * 1000)
    user = ctx.message.author
    await ctx.send(f"🏓 Pong! Latency: {latency}ms, user is {user}")


@bot.command(name="balance")
async def balance(ctx: commands.Context) -> None:
    """Check your account balance (TODO: implement with user service)."""
    # TODO: Integrate with user service to fetch balance
    await ctx.send("💰 Balance check coming soon! This will integrate with the user service.")


@bot.command(name="items")
async def items(ctx: commands.Context) -> None:
    """List available items (TODO: implement with item service)."""
    # TODO: Integrate with item service to list items
    await ctx.send("📦 Item listing coming soon! This will integrate with the item service.")


@bot.command(name="buy")
async def buy(ctx: commands.Context, item_id: Optional[int] = None) -> None:
    """Purchase an item (TODO: implement with payment service)."""
    if item_id is None:
        await ctx.send(f"❌ Please specify an item ID. Usage: `{COMMAND_PREFIX}buy <item_id>`")
        return
    # TODO: Integrate with payment service to process purchase
    await ctx.send(f"🛒 Purchase functionality coming soon! Item ID: {item_id}")

@bot.command(name="auth_test")
async def auth_test(ctx: commands.Context) -> None:
    """Test authentication use for dbg"""
    token = get_user_jwt(str(ctx.message.author.id))
    await ctx.send(f"🔐 Authentication test {token}")


def main() -> None:
    """Main entry point for the Discord bot."""
    if not DISCORD_TOKEN:
        logger.error("DISCORD_TOKEN environment variable is not set!")
        return
    
    logger.info("Starting Discord bot...")
    bot.run(DISCORD_TOKEN)


if __name__ == "__main__":
    main()
