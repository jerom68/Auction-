import discord
from discord.ext import commands
import asyncio
import os
from flask import Flask

# Variables
TOKEN = "YOUR_DISCORD_BOT_TOKEN"
AUCTION_CHANNEL_ID = 123456789012345678  # Channel where auctions & announcements happen
REGISTER_CHANNEL_ID = 123456789012345678  # Channel for registration
LOG_CHANNEL_ID = 123456789012345678  # Log channel
AUCTION_ROLE_ID = 123456789012345678  # Role required to access auction services

# Bot setup
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# Web server for Render hosting
app = Flask(__name__)

@app.route("/")
def home():
    return "Auction Bot is running!"

def run_server():
    app.run(host="0.0.0.0", port=8080)

# ------------------- Auction System -------------------

auction_active = False
current_auction = None
highest_bid = 0
highest_bidder = None
bid_increment = 0

@bot.command()
@commands.has_role(AUCTION_ROLE_ID)
async def auctionstart(ctx):
    """Starts an auction with the registered Pokémon."""
    global auction_active, current_auction, highest_bid, highest_bidder, bid_increment

    if auction_active:
        await ctx.send("⚠️ An auction is already in progress!")
        return

    # Fetch the Pokémon details from the registration list (To be implemented)
    current_auction = {"name": "Pikachu", "level": 35, "ivs": "90%", "starting_bid": 1000, "bid_increment": 500}
    bid_increment = current_auction["bid_increment"]

    auction_active = True
    highest_bid = current_auction["starting_bid"]
    highest_bidder = None

    embed = discord.Embed(title=f"✨ {current_auction['name']} Auction ✨", color=discord.Color.gold())
    embed.add_field(name="Level", value=current_auction["level"], inline=True)
    embed.add_field(name="IVs", value=current_auction["ivs"], inline=True)
    embed.add_field(name="Starting Bid", value=f"{highest_bid} credits", inline=False)
    embed.add_field(name="Minimum Bid Increment", value=f"{bid_increment} credits", inline=False)
    
    auction_channel = bot.get_channel(AUCTION_CHANNEL_ID)
    await auction_channel.send(embed=embed)
    await auction_channel.send("💰 Use `!bid <amount>` to place your bid!")

@bot.command()
@commands.has_role(AUCTION_ROLE_ID)
async def bid(ctx, amount: int):
    """Places a bid on the current auction."""
    global highest_bid, highest_bidder, auction_active

    if not auction_active:
        await ctx.send("⚠️ No active auction right now!")
        return

    if amount < highest_bid + bid_increment:
        await ctx.send(f"⚠️ Your bid must be at least {highest_bid + bid_increment} credits!")
        return

    highest_bid = amount
    highest_bidder = ctx.author

    await ctx.send(f"✅ {ctx.author.mention} is now the highest bidder with **{highest_bid} credits**!")

# ------------------- Moderation Commands -------------------

@bot.command()
@commands.has_permissions(administrator=True)
async def warn(ctx, member: discord.Member, *, reason="No reason provided"):
    """Warns a user for breaking auction rules."""
    log_channel = bot.get_channel(LOG_CHANNEL_ID)
    await log_channel.send(f"⚠️ {member.mention} has been warned: {reason}")
    await ctx.send(f"⚠️ {member.mention} has been warned.")

@bot.command()
@commands.has_permissions(administrator=True)
async def blacklist(ctx, member: discord.Member):
    """Blacklists a user from bidding."""
    await ctx.send(f"🚫 {member.mention} has been blacklisted from auctions.")

@bot.command()
@commands.has_permissions(administrator=True)
async def unblacklist(ctx, member: discord.Member):
    """Removes a user from the blacklist."""
    await ctx.send(f"✅ {member.mention} is now allowed to participate in auctions again.")

# ------------------- Run Bot & Web Server -------------------

if __name__ == "__main__":
    import threading
    threading.Thread(target=run_server).start()
    bot.run(TOKEN)
