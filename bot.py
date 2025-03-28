import discord
from discord.ext import commands
import os
import asyncio
import threading
import flask

# Load environment variables
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
AUCTION_CHANNEL_ID = int(os.getenv("AUCTION_CHANNEL_ID", "0"))  # Auction chat
LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID", "0"))  # Auction logs
REGISTER_CHANNEL_ID = int(os.getenv("REGISTER_CHANNEL_ID", "0"))  # Registration
PORT = int(os.getenv("PORT", "8080"))  # Port for Render hosting

# Enable all intents
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# Auction data storage
auction_data = None
highest_bid = 0
highest_bidder = None
auction_active = False
bid_increment = 0


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    print("Bot is ready!")


# Function to log messages in log channel
async def log_message(message):
    log_channel = bot.get_channel(LOG_CHANNEL_ID)
    if log_channel:
        await log_channel.send(message)


# Auction start command (!auctionstart)
@bot.command(name="auctionstart")
async def auction_start(ctx):
    global auction_data, auction_active, highest_bid, highest_bidder

    auction_channel = bot.get_channel(AUCTION_CHANNEL_ID)
    if not auction_channel:
        await ctx.send("auction channel is not set properly.")
        return

    if auction_active:
        await ctx.send("an auction is already in progress!")
        return
    if not auction_data:
        await ctx.send("no pokémon registered for auction.")
        return

    auction_active = True
    highest_bid = auction_data["start_bid"]
    highest_bidder = None

    auction_embed = discord.Embed(
        title=f"{'✨ ' if 'shiny' in auction_data['pokemon'].lower() else ''}{auction_data['pokemon']} auction{' ✨' if 'shiny' in auction_data['pokemon'].lower() else ''}",
        description=(
            f"**starting bid:** {auction_data['start_bid']}\n"
            f"**bid increment:** {auction_data['bid_increment']}\n"
            f"**level:** {auction_data['level']}\n"
            f"**total ivs:** {auction_data['total_ivs']}\n"
            f"**stats:** {auction_data['ivs']}"
        ),
        color=discord.Color.blue()
    )

    await auction_channel.send(embed=auction_embed)
    await auction_channel.send("auction has started! place your bids using `!bid <amount>`.")

    await log_message(f"🔔 **Auction Started**\nPokémon: {auction_data['pokemon']}\nStarting Bid: {auction_data['start_bid']}")


# Bidding command (!bid)
@bot.command(name="bid")
async def bid(ctx, amount: int):
    global highest_bid, highest_bidder, auction_active, bid_increment

    auction_channel = bot.get_channel(AUCTION_CHANNEL_ID)
    if not auction_active:
        await ctx.send("no auction is currently active!")
        return
    if amount < highest_bid + bid_increment:
        await ctx.send(f"minimum bid must be at least {highest_bid + bid_increment}!")
        return

    highest_bid = amount
    highest_bidder = ctx.author
    await auction_channel.send(f"{ctx.author.mention} placed a bid of {amount}!")

    # Log bid
    await log_message(f"💰 **New Bid**\nUser: {ctx.author} ({ctx.author.id})\nBid: {amount}")

    # Start countdown
    asyncio.create_task(countdown(auction_channel))


async def countdown(channel):
    global highest_bidder, auction_active

    await asyncio.sleep(10)
    if highest_bidder:
        for i in range(5, 0, -1):
            await channel.send(f"auction closing in {i} seconds...")
            await asyncio.sleep(1)
        await channel.send(f"🎉 auction ended! {highest_bidder.mention} won with {highest_bid}!")

        # Log auction end
        await log_message(f"🏆 **Auction Ended**\nWinner: {highest_bidder} ({highest_bidder.id})\nFinal Bid: {highest_bid}")

        auction_active = False


# Cancel auction command (!cancel)
@bot.command(name="cancel")
@commands.has_permissions(administrator=True)
async def cancel(ctx):
    global auction_active

    auction_channel = bot.get_channel(AUCTION_CHANNEL_ID)
    if not auction_active:
        await ctx.send("no auction to cancel!")
        return

    auction_active = False
    await auction_channel.send("auction has been cancelled.")

    # Log cancellation
    await log_message(f"⚠️ **Auction Cancelled** by {ctx.author}")


# Ping command (!ping)
@bot.command(name="ping")
async def ping(ctx):
    latency = round(bot.latency * 1000)  # Convert to ms
    await ctx.send(f"🏓 pong! latency: {latency}ms")


# Keep bot alive with a port for Render
app = flask.Flask(__name__)

@app.route("/")
def home():
    return "bot is running!"

def run_flask():
    app.run(host="0.0.0.0", port=PORT, threaded=True)

# Run Flask in a separate thread
threading.Thread(target=run_flask, daemon=True).start()

# Run the bot
bot.run(TOKEN)
