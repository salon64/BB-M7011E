# Discord Bot Service
# Main entry point for the Discord bot

import os
import logging
import discord
import httpx
import jwt
from datetime import datetime
from urllib.parse import urlencode
from app.auth import get_user_card_id, get_discord_jwt, UserNotLinkedError
from discord.ext import commands
from dotenv import load_dotenv
from typing import Optional
from supabase import Client
from common.database import get_supabase_client

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
ACCOUNT_LINK_URL = os.getenv("ACCOUNT_LINK_URL", "https://example.com/link-account")

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
            type=discord.ActivityType.watching, name=f"{COMMAND_PREFIX}help"
        )
    )


@bot.event
async def on_command_error(ctx: commands.Context, error: Exception) -> None:
    """Global error handler for commands."""
    if isinstance(error, commands.CommandNotFound):
        await ctx.send(
            f"❌ Command not found. Use `{COMMAND_PREFIX}help` for available commands."
        )
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❌ Missing required argument: `{error.param.name}`")
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ You don't have permission to use this command.")
    elif isinstance(error, commands.CommandInvokeError) and isinstance(
        error.original, UserNotLinkedError
    ):
        # User has not linked their Discord account
        discord_user = str(ctx.message.author.id)
        link_params = urlencode({"discord": discord_user})
        link_url = f"{ACCOUNT_LINK_URL}?{link_params}"
        await ctx.send(
            f"❌ Your Discord account is not linked!\n"
            f"🔗 Please link your account here: {link_url}"
        )
    else:
        logger.error(f"Command error: {error}")
        await ctx.send("❌ An error occurred while processing your command.")


@bot.command(name="ping", aliases=["p"])
async def ping(ctx: commands.Context) -> None:
    """Check if the bot is responsive."""
    latency = round(bot.latency * 1000)
    user = ctx.message.author
    await ctx.send(f"🏓 Pong! Latency: {latency}ms, user is {user}")


@bot.command(name="balance", aliases=["b"])
async def balance(ctx: commands.Context) -> None:
    """Check your account balance."""
    discord_id = str(ctx.message.author.id)
    card_id = get_user_card_id(discord_id)
    jwt_token = get_discord_jwt()

    if not jwt_token:
        await ctx.send("❌ Failed to authenticate with backend services.")
        return

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{USER_SERVICE_URL}/user/fetch_info",
                json={"user_id": int(card_id)},
                headers={"Authorization": f"Bearer {jwt_token}"},
                timeout=10.0,
            )

            if response.status_code == 200:
                data = response.json()
                balance_ore = data.get("balance", 0)
                balance_sek = balance_ore / 100
                await ctx.send(
                    f"💰 **Account Info**\n"
                    f"👤 Name: {data.get('first_name', 'N/A')} {data.get('last_name', '')}\n"
                    f"💵 Balance: {balance_sek:.2f} SEK\n"
                    f"✅ Active: {'Yes' if data.get('active') else 'No'}"
                )
            elif response.status_code == 404:
                await ctx.send("❌ User not found in the system.")
            else:
                logger.error(
                    f"User service error: {response.status_code} - {response.text}"
                )
                await ctx.send("❌ Failed to fetch balance. Please try again later.")
        except httpx.RequestError as e:
            logger.error(f"Request to user service failed: {e}")
            await ctx.send("❌ Could not connect to user service.")


@bot.command(name="items", aliases=["i"])
async def items(ctx: commands.Context) -> None:
    """List available items for purchase."""
    discord_id = str(ctx.message.author.id)
    # Verify user is linked (will raise UserNotLinkedError if not)
    get_user_card_id(discord_id)
    jwt_token = get_discord_jwt()

    if not jwt_token:
        await ctx.send("❌ Failed to authenticate with backend services.")
        return

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{ITEM_SERVICE_URL}/items/list",
                json={"active_only": True},
                headers={"Authorization": f"Bearer {jwt_token}"},
                timeout=10.0,
            )
            if response.status_code == 200:
                data = response.json()
                items_list = data.get("items", [])
                if not items_list:
                    await ctx.send("📦 No items available at the moment.")
                    return
                # Format items list
                items_text = "📦 **Available Items:**\n"
                for item in items_list[:20]:  # Limit to 20 items
                    price_ore = item["price"]
                    price_sek = price_ore / 100
                    items_text += (
                        f"  `{item['id']}` - **{item['name']}** - {price_sek:.2f} SEK\n"
                    )
                if len(items_list) > 20:
                    items_text += f"  ... and {len(items_list) - 20} more items"
                await ctx.send(items_text)
            else:
                logger.error(
                    f"Item service error: {response.status_code} - {response.text}"
                )
                await ctx.send("❌ Failed to fetch items. Please try again later.")
        except httpx.RequestError as e:
            logger.error(f"Request to item service failed: {e}")
            await ctx.send("❌ Could not connect to item service.")


@bot.command(name="buy", aliases=["purchase"])
async def buy(ctx: commands.Context, item_id: Optional[str] = None) -> None:
    """Purchase an item by ID."""
    if item_id is None:
        await ctx.send(
            f"❌ Please specify an item ID. Usage: `{COMMAND_PREFIX}buy <item_id>`"
        )
        return

    discord_id = str(ctx.message.author.id)
    card_id = get_user_card_id(discord_id)
    jwt_token = get_discord_jwt()

    if not jwt_token:
        await ctx.send("❌ Failed to authenticate with backend services.")
        return

    async with httpx.AsyncClient() as client:
        try:
            # First, get item details to show what's being purchased
            item_response = await client.post(
                f"{ITEM_SERVICE_URL}/items/fetch_info",
                json={"item_id": item_id},
                headers={"Authorization": f"Bearer {jwt_token}"},
                timeout=10.0,
            )
            if item_response.status_code == 404:
                await ctx.send(f"❌ Item `{item_id}` not found.")
                return
            elif item_response.status_code != 200:
                await ctx.send("❌ Failed to fetch item details.")
                return
            item_data = item_response.json()
            item_name = item_data.get("name", "Unknown")
            item_price_ore = item_data.get("price", 0)
            item_price_sek = item_price_ore / 100

            # Process the payment
            payment_response = await client.post(
                f"{PAYMENT_SERVICE_URL}/payments/debit",
                json={"user_id": int(card_id), "item_id": item_id},
                headers={"Authorization": f"Bearer {jwt_token}"},
                timeout=10.0,
            )

            if payment_response.status_code == 200:
                payment_data = payment_response.json()
                new_balance_ore = payment_data.get("new_balance", 0)
                new_balance_sek = new_balance_ore / 100
                await ctx.send(
                    f"✅ **Purchase Successful!**\n"
                    f"🛒 Item: **{item_name}**\n"
                    f"💵 Price: {item_price_sek:.2f} SEK\n"
                    f"💰 New Balance: {new_balance_sek:.2f} SEK"
                )
            elif payment_response.status_code == 402:
                await ctx.send(
                    f"❌ Insufficient funds to purchase **{item_name}** ({item_price_sek:.2f} SEK)."
                )
            elif payment_response.status_code == 403:
                await ctx.send(
                    "❌ Your account is not active. Please contact an administrator."
                )
            elif payment_response.status_code == 404:
                await ctx.send("❌ User not found in the payment system.")
            else:
                logger.error(
                    f"Payment service error: {payment_response.status_code} - {payment_response.text}"
                )
                await ctx.send("❌ Payment failed. Please try again later.")
        except httpx.RequestError as e:
            logger.error(f"Request to services failed: {e}")
            await ctx.send("❌ Could not connect to backend services.")


@bot.command(name="transactions", aliases=["t"])
async def transactions(
    ctx: commands.Context,
    user_id: Optional[str] = None,
    limit: Optional[str] = "20",
    offset: Optional[str] = "0",
) -> None:
    """List transaction history. Usage: `!transactions [user_id] [limit] [offset]`"""
    # Ensure user is linked; this will raise UserNotLinkedError if not
    discord_id = str(ctx.message.author.id)
    get_user_card_id(discord_id)
    jwt_token = get_discord_jwt()

    if not jwt_token:
        await ctx.send("❌ Failed to authenticate with backend services.")
        return

    # Parse optional params
    query_params = {}
    try:
        limit_v = int(limit) if limit is not None else 20
    except ValueError:
        await ctx.send("❌ Invalid `limit` parameter. It must be an integer.")
        return
    try:
        offset_v = int(offset) if offset is not None else 0
    except ValueError:
        await ctx.send("❌ Invalid `offset` parameter. It must be an integer.")
        return

    # Only include user_id if provided (admins/service accounts can pass this)
    if user_id is not None:
        try:
            query_params["user_id"] = int(user_id)
        except ValueError:
            await ctx.send("❌ Invalid `user_id`. It must be an integer.")
            return

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{PAYMENT_SERVICE_URL}/transactions/history",
                params={**query_params, "limit": limit_v, "offset": offset_v},
                headers={"Authorization": f"Bearer {jwt_token}"},
                timeout=10.0,
            )

            if response.status_code == 200:
                data = response.json()
                transactions_list = data.get("transactions", [])
                if not transactions_list:
                    await ctx.send("📭 No transactions found.")
                    return

                # Format a concise list (limit to 50 shown)
                text = f"📜 **Transaction History** (showing {len(transactions_list)} items)\n"
                for tx in transactions_list[:50]:
                    tx_id = tx.get("id")
                    tx_user = tx.get("user")
                    tx_amount = tx.get("amount") or tx.get("price") or tx.get("value")
                    if isinstance(tx_amount, (int, float)):
                        try:
                            tx_amount_display = f"{int(tx_amount) / 100:.2f} SEK"
                        except Exception:
                            tx_amount_display = str(tx_amount)
                    else:
                        tx_amount_display = str(tx_amount)
                    tx_time = tx.get("created_at") or tx.get("timestamp") or ""
                    text += f"• `{tx_id}` user={tx_user} amount={tx_amount_display} at {tx_time}\n"

                await ctx.send(text)
            elif response.status_code == 403:
                await ctx.send("❌ You are not authorized to view these transactions.")
            else:
                logger.error(
                    f"Payment service error (transactions): {response.status_code} - {response.text}"
                )
                await ctx.send(
                    "❌ Failed to fetch transactions. Please try again later."
                )
        except httpx.RequestError as e:
            logger.error(f"Request to payment service failed: {e}")
            await ctx.send("❌ Could not connect to payment service.")


@bot.command(name="transaction", aliases=["td"])
async def transaction(
    ctx: commands.Context, transaction_id: Optional[str] = None
) -> None:
    """Fetch a single transaction by ID. Usage: `!transaction <transaction_id>`"""
    if not transaction_id:
        await ctx.send(
            f"❌ Please specify a transaction ID. Usage: `{COMMAND_PREFIX}transaction <transaction_id>`"
        )
        return

    discord_id = str(ctx.message.author.id)
    # verify linked
    get_user_card_id(discord_id)
    jwt_token = get_discord_jwt()

    if not jwt_token:
        await ctx.send("❌ Failed to authenticate with backend services.")
        return

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{PAYMENT_SERVICE_URL}/transactions/history/{transaction_id}",
                headers={"Authorization": f"Bearer {jwt_token}"},
                timeout=10.0,
            )

            if response.status_code == 200:
                data = response.json()
                tx = data.get("transaction") or {}
                tx_id = tx.get("id")
                tx_user = tx.get("user")
                tx_amount = tx.get("amount") or tx.get("price") or tx.get("value")
                tx_time = tx.get("created_at") or tx.get("timestamp") or ""
                tx_desc = tx.get("description") or tx.get("note") or ""
                amount_display = ""
                if isinstance(tx_amount, (int, float)):
                    try:
                        amount_display = f"{int(tx_amount) / 100:.2f} SEK"
                    except Exception:
                        amount_display = str(tx_amount)
                else:
                    amount_display = str(tx_amount)

                text = (
                    f"📘 **Transaction**\n"
                    f"ID: `{tx_id}`\n"
                    f"User: {tx_user}\n"
                    f"Amount: {amount_display}\n"
                    f"Time: {tx_time}\n"
                    f"Desc: {tx_desc}"
                )
                await ctx.send(text)
            elif response.status_code == 404:
                await ctx.send("❌ Transaction not found.")
            elif response.status_code == 403:
                await ctx.send("❌ You are not authorized to view this transaction.")
            else:
                logger.error(
                    f"Payment service error (transaction): {response.status_code} - {response.text}"
                )
                await ctx.send(
                    "❌ Failed to fetch transaction. Please try again later."
                )
        except httpx.RequestError as e:
            logger.error(f"Request to payment service failed: {e}")
            await ctx.send("❌ Could not connect to payment service.")


@bot.command(name="add_funds", aliases=["deposit"])
async def add_funds(ctx: commands.Context, amount: Optional[str] = None) -> None:
    """Add funds to your account. Requires an image attachment as proof of payment."""
    if amount is None:
        await ctx.send(
            f"❌ Please specify an amount. Usage: `{COMMAND_PREFIX}add_funds <amount>` with an image attachment"
        )
        return

    # Validate amount is a positive number
    try:
        amount_value = float(amount)
        if amount_value <= 0:
            await ctx.send("❌ Amount must be a positive number.")
            return
    except ValueError:
        await ctx.send("❌ Invalid amount. Please enter a valid number.")
        return

    # Check for image attachment
    if not ctx.message.attachments:
        await ctx.send(
            "❌ Please attach an image (receipt/proof of payment) with your request."
        )
        return

    # Find image attachment
    image_attachment = None
    valid_image_types = [
        "image/png",
        "image/jpeg",
        "image/jpg",
        "image/gif",
        "image/webp",
    ]
    for attachment in ctx.message.attachments:
        if attachment.content_type and attachment.content_type in valid_image_types:
            image_attachment = attachment
            break

    if not image_attachment:
        await ctx.send("❌ Please attach a valid image file (PNG, JPEG, GIF, or WebP).")
        return

    discord_id = str(ctx.message.author.id)
    card_id = get_user_card_id(discord_id)
    jwt_token = get_discord_jwt()

    if not jwt_token:
        await ctx.send("❌ Failed to authenticate with backend services.")
        return

    # Call user service to add balance
    async with httpx.AsyncClient() as client:
        try:
            amount_ore = int(amount_value * 100)  # Convert to öre (cents)
            response = await client.post(
                f"{USER_SERVICE_URL}/user/add_balance",
                json={"card_id": int(card_id), "amount": amount_ore},
                headers={"Authorization": f"Bearer {jwt_token}"},
                timeout=10.0,
            )

            if response.status_code == 200:
                data = response.json()
                new_balance_sek = data.get("new_balance", 0) / 100
                await ctx.send(
                    f"✅ **Funds Added Successfully!**\n"
                    f"💵 Amount: {amount_value:.2f} SEK\n"
                    f"📎 Receipt: Attached\n"
                    f"💰 New Balance: {new_balance_sek:.2f} SEK"
                )
                logger.info(
                    f"Funds added: user={discord_id}, amount={amount_value} SEK, receipt={image_attachment.url}"
                )
            elif response.status_code == 403:
                await ctx.send(
                    "❌ You don't have permission to add funds to this account."
                )
            elif response.status_code == 404:
                await ctx.send("❌ User not found in the system.")
            else:
                logger.error(
                    f"User service error: {response.status_code} - {response.text}"
                )
                await ctx.send("❌ Failed to add funds. Please try again later.")
        except httpx.RequestError as e:
            logger.error(f"Request to user service failed: {e}")
            await ctx.send("❌ Could not connect to user service.")


@bot.command(name="auth_test", aliases=["auth"])
async def auth_test(ctx: commands.Context) -> None:
    """Test authentication - returns user's card_id and bot JWT"""
    discord_id = str(ctx.message.author.id)
    card_id = get_user_card_id(discord_id)
    jwt_token = get_discord_jwt()

    # Truncate JWT for display (show first 20 and last 10 chars)
    jwt_display = (
        f"{jwt_token[:20]}...{jwt_token[-10:]}"
        if jwt_token and len(jwt_token) > 30
        else jwt_token
    )

    # Decode JWT to get expiration time
    expires_display = "N/A"
    if jwt_token:
        try:
            decoded = jwt.decode(jwt_token, options={"verify_signature": False})
            if "exp" in decoded:
                exp_timestamp = decoded["exp"]
                exp_datetime = datetime.fromtimestamp(exp_timestamp)
                expires_display = exp_datetime.strftime("%Y-%m-%d %H:%M:%S")
        except Exception as e:
            logger.error(f"Failed to decode JWT: {e}")
            expires_display = "Error decoding"

    await ctx.send(
        f"🔐 Authentication test:\n"
        f"📇 Card ID: `{card_id}`\n"
        f"🎫 JWT: `{jwt_display}`\n"
        f"⏰ Expires: `{expires_display}`"
    )


def main() -> None:
    """Main entry point for the Discord bot."""
    if not DISCORD_TOKEN:
        logger.error("DISCORD_TOKEN environment variable is not set!")
        return

    logger.info("Starting Discord bot...")
    bot.run(DISCORD_TOKEN)


if __name__ == "__main__":
    main()
