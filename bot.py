import discord
from discord.ext import commands
import os
import threading
import asyncio
import uvicorn
from fastapi import FastAPI

# Load environment variables
TOKEN = os.getenv("TOKEN")
SERVER_ID = int(os.getenv("SERVER_ID"))  # Only allow bot in this server
AUCTION_CHANNEL_ID = int(os.getenv("AUCTION_CHANNEL_ID"))
REGISTER_CHANNEL_ID = int(os.getenv("REGISTER_CHANNEL_ID"))
LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID"))  # Log Channel
AUCTION_ROLE_ID = int(os.getenv("AUCTION_ROLE_ID"))
PORT = int(os.getenv("PORT", 8080))  # Port for Render

# Discord bot setup
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# Auction-related variables
registrations = []
auction_active = False
bids = {}
current_auction = None
auction_task = None

# FastAPI app for Render health check
app = FastAPI()

@app.get("/")
async def home():
    return {"status": "Bot is running!"}

# Start FastAPI server in a separate thread
def run_api():
    uvicorn.run(app, host="0.0.0.0", port=PORT)

threading.Thread(target=run_api, daemon=True).start()

def has_auction_role(user):
    return any(role.id == AUCTION_ROLE_ID for role in user.roles)

@bot.event
async def on_ready():
    print(f"✅ {bot.user} is online and running!")

@bot.event
async def on_guild_join(guild):
    """Auto leave if bot joins an unauthorized server."""
    if guild.id != SERVER_ID:
        await guild.leave()
        print(f"❌ Left unauthorized server: {guild.name}")

async def send_log(embed):
    """Send logs to the log channel."""
    log_channel = bot.get_channel(LOG_CHANNEL_ID)
    if log_channel:
        await log_channel.send(embed=embed)

@bot.command()
async def register(ctx):
    """Register a Pokémon for auction."""
    if not has_auction_role(ctx.author):
        await ctx.send("❌ You do not have permission to register Pokémon.")
        return

    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel

    await ctx.send("Enter the Pokémon name:")
    name = await bot.wait_for("message", check=check)

    await ctx.send("Enter the Pokémon level:")
    level = await bot.wait_for("message", check=check)

    await ctx.send("Enter the total IVs:")
    total_ivs = await bot.wait_for("message", check=check)

    ivs = {}
    for stat in ["HP", "Attack", "Defense", "Sp. Atk", "Sp. Def", "Speed"]:
        await ctx.send(f"Enter the {stat} IV:")
        ivs[stat] = await bot.wait_for("message", check=check)

    await ctx.send("Enter the starting bid:")
    starting_bid = await bot.wait_for("message", check=check)

    await ctx.send("Enter the minimum bid increment:")
    min_bid_increment = await bot.wait_for("message", check=check)

    pokemon = {
        "owner": ctx.author,
        "name": name.content,
        "level": level.content,
        "total_ivs": total_ivs.content,
        "ivs": {k: v.content for k, v in ivs.items()},
        "starting_bid": int(starting_bid.content),
        "min_bid_increment": int(min_bid_increment.content)
    }
    registrations.append(pokemon)

    embed = discord.Embed(title="✅ Pokémon Registered!", color=discord.Color.green())
    embed.add_field(name="Pokémon Name", value=name.content, inline=False)
    embed.add_field(name="Level", value=level.content, inline=True)
    embed.add_field(name="Total IVs", value=total_ivs.content, inline=True)
    for stat, value in ivs.items():
        embed.add_field(name=f"{stat} IV", value=value.content, inline=True)
    embed.add_field(name="Starting Bid", value=starting_bid.content, inline=True)
    embed.add_field(name="Min Bid Increment", value=min_bid_increment.content, inline=True)
    embed.set_footer(text="Your Pokémon has been registered successfully!")

    await ctx.send(embed=embed)
    await send_log(embed)

@bot.command()
async def auctionstart(ctx):
    """Start an auction for the next registered Pokémon."""
    global auction_active, bids, current_auction, auction_task

    if auction_active:
        await ctx.send("❌ An auction is already in progress!")
        return

    if not registrations:
        await ctx.send("❌ No Pokémon have been registered for auction.")
        return

    auction_active = True
    current_auction = registrations.pop(0)
    bids.clear()

    embed = discord.Embed(title=f"✨ {current_auction['name']} Auction ✨", color=discord.Color.gold())
    embed.add_field(name="Starting Bid", value=f"{current_auction['starting_bid']}", inline=True)
    embed.add_field(name="Min Bid Increment", value=f"{current_auction['min_bid_increment']}", inline=True)
    embed.set_footer(text="Place your bid using !bid <amount>")

    auction_channel = bot.get_channel(AUCTION_CHANNEL_ID)
    await auction_channel.send(embed=embed)
    await send_log(embed)

    # Start auction timer
    auction_task = asyncio.create_task(auction_timer())

async def auction_timer():
    """Automatically end the auction if no bids are placed within 10 seconds."""
    global auction_active, auction_task

    await asyncio.sleep(10)
    if bids:
        await auctionend()
    else:
        await bot.get_channel(AUCTION_CHANNEL_ID).send("❌ Auction ended due to no bids.")
        auction_active = False
        auction_task = None

@bot.command()
async def bid(ctx, amount: int):
    """Place a bid in the auction."""
    global bids

    if not auction_active:
        await ctx.send("❌ There is no active auction right now.")
        return

    if bids and amount <= max(bids.values()):
        await ctx.send(f"❌ Your bid must be higher than the current highest bid.")
        return

    bids[ctx.author.id] = amount

    embed = discord.Embed(title="💵 New Bid Placed", color=discord.Color.blue())
    embed.add_field(name="Bidder", value=ctx.author.mention, inline=True)
    embed.add_field(name="Amount", value=amount, inline=True)

    await ctx.send(embed=embed)
    await send_log(embed)

@bot.command()
async def auctionend(ctx=None):
    """Manually end an auction."""
    global auction_active, bids, auction_task

    if not auction_active:
        return

    auction_active = False
    auction_task = None

    if not bids:
        await bot.get_channel(AUCTION_CHANNEL_ID).send("❌ Auction ended with no bids.")
        return

    winner_id = max(bids, key=bids.get)
    winner = bot.get_user(winner_id)
    winning_bid = bids[winner_id]

    embed = discord.Embed(title="🏅 Auction Ended", color=discord.Color.green())
    embed.add_field(name="Winner", value=winner.mention, inline=True)
    embed.add_field(name="Winning Bid", value=winning_bid, inline=True)
    embed.set_footer(text="Please complete the trade!")

    auction_channel = bot.get_channel(AUCTION_CHANNEL_ID)
    await auction_channel.send(embed=embed)
    await send_log(embed)

    owner = current_auction["owner"]
    await auction_channel.send(f"📢 {owner.mention}, please trade with {winner.mention}.")

@bot.command()
async def ping(ctx):
    """Check bot latency."""
    latency = round(bot.latency * 1000)
    await ctx.send(f"🏓 Pong! Latency: {latency}ms")

# Start the bot
bot.run(TOKEN)
