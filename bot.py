import discord
from discord.ext import commands
import os
import threading
import asyncio
import uvicorn
from fastapi import FastAPI

# Load environment variables
TOKEN = os.getenv("TOKEN")
SERVER_ID = int(os.getenv("SERVER_ID"))
AUCTION_CHANNEL_ID = int(os.getenv("AUCTION_CHANNEL_ID"))
REGISTER_CHANNEL_ID = int(os.getenv("REGISTER_CHANNEL_ID"))
AUCTION_ROLE_ID = int(os.getenv("AUCTION_ROLE_ID"))
LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID"))
PORT = int(os.getenv("PORT", 8080))  # Default port for Render

# Discord bot setup
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# Auction-related variables
registrations = []
auction_active = False
bids = {}
current_auction = None

# FastAPI app for Render
app = FastAPI()

@app.get("/")
async def home():
    return {"status": "Bot is running!"}

def run_api():
    uvicorn.run(app, host="0.0.0.0", port=PORT)

threading.Thread(target=run_api, daemon=True).start()

def has_auction_role(user):
    return any(role.id == AUCTION_ROLE_ID for role in user.roles)

async def log_event(title, description, color=discord.Color.blue()):
    """Sends an event log to the log channel."""
    log_channel = bot.get_channel(LOG_CHANNEL_ID)
    if log_channel:
        embed = discord.Embed(title=title, description=description, color=color)
        await log_channel.send(embed=embed)

@bot.event
async def on_ready():
    print(f"✅ {bot.user} is online and running!")

@bot.event
async def on_guild_join(guild):
    if guild.id != SERVER_ID:
        await guild.leave()
        print(f"❌ Left unauthorized server: {guild.name}")

@bot.command()
async def register(ctx):
    if not has_auction_role(ctx.author):
        await ctx.send("❌ You do not have permission to register Pokémon.")
        return

    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel

    await ctx.send("Enter the Pokémon name:")
    name = await bot.wait_for("message", check=check)

    await ctx.send("Enter the Pokémon Level:")
    level = await bot.wait_for("message", check=check)

    await ctx.send("Enter the Total IVs:")
    total_ivs = await bot.wait_for("message", check=check)

    await ctx.send("Enter HP IV:")
    hp_iv = await bot.wait_for("message", check=check)

    await ctx.send("Enter ATK IV:")
    atk_iv = await bot.wait_for("message", check=check)

    await ctx.send("Enter DEF IV:")
    def_iv = await bot.wait_for("message", check=check)

    await ctx.send("Enter SPATK IV:")
    spatk_iv = await bot.wait_for("message", check=check)

    await ctx.send("Enter SPDEF IV:")
    spdef_iv = await bot.wait_for("message", check=check)

    await ctx.send("Enter SPD IV:")
    spd_iv = await bot.wait_for("message", check=check)

    await ctx.send("Enter the starting bid:")
    starting_bid = await bot.wait_for("message", check=check)

    await ctx.send("Enter the minimum bid increment:")
    min_bid_increment = await bot.wait_for("message", check=check)

    pokemon = {
        "owner": ctx.author,
        "name": name.content,
        "level": level.content,
        "total_ivs": total_ivs.content,
        "hp_iv": hp_iv.content,
        "atk_iv": atk_iv.content,
        "def_iv": def_iv.content,
        "spatk_iv": spatk_iv.content,
        "spdef_iv": spdef_iv.content,
        "spd_iv": spd_iv.content,
        "starting_bid": int(starting_bid.content),
        "min_bid_increment": int(min_bid_increment.content)
    }
    registrations.append(pokemon)

    embed = discord.Embed(title="✅ Pokémon Registered!", color=discord.Color.green())
    embed.add_field(name="Pokémon Name", value=name.content, inline=True)
    embed.add_field(name="Level", value=level.content, inline=True)
    embed.add_field(name="Total IVs", value=total_ivs.content, inline=True)
    embed.add_field(name="Starting Bid", value=starting_bid.content, inline=True)
    embed.add_field(name="Min Bid Increment", value=min_bid_increment.content, inline=True)
    embed.set_footer(text="Your Pokémon has been registered successfully!")

    await ctx.send(embed=embed)
    await log_event("Pokémon Registered", f"{ctx.author.mention} registered {name.content} for auction.", discord.Color.green())

@bot.command()
async def auctionstart(ctx):
    global auction_active, bids, current_auction

    if auction_active:
        await ctx.send("❌ An auction is already in progress!")
        return

    if not registrations:
        await ctx.send("❌ No Pokémon have been registered for auction.")
        return

    auction_active = True
    bids = {}
    current_auction = registrations.pop(0)

    embed = discord.Embed(title=f"✨ {current_auction['name']} Auction ✨", color=discord.Color.gold())
    embed.add_field(name="Level", value=current_auction["level"], inline=True)
    embed.add_field(name="Total IVs", value=current_auction["total_ivs"], inline=True)
    embed.add_field(name="HP IV", value=current_auction["hp_iv"], inline=True)
    embed.add_field(name="ATK IV", value=current_auction["atk_iv"], inline=True)
    embed.set_footer(text="Place your bid using !bid <amount>")

    auction_channel = bot.get_channel(AUCTION_CHANNEL_ID)
    await auction_channel.send(embed=embed)

    await log_event("Auction Started", f"{ctx.author.mention} started an auction for {current_auction['name']}.", discord.Color.gold())

    await asyncio.sleep(20)  # 20-second timer

    if not bids:
        auction_active = False
        await auction_channel.send("No bids were placed. Auction ended.")
        await log_event("Auction Ended", "No bids were placed.", discord.Color.red())

@bot.command()
async def bid(ctx, amount: int):
    global bids

    if not auction_active:
        await ctx.send("❌ There is no active auction.")
        return

    if bids and amount <= max(bids.values()):
        await ctx.send("❌ Your bid must be higher than the current highest bid.")
        return

    bids[ctx.author.id] = amount
    await ctx.send(f"✅ {ctx.author.mention} placed a bid of {amount}!")

@bot.command()
async def auctionend(ctx):
    global auction_active

    if not auction_active:
        await ctx.send("❌ No active auction.")
        return

    auction_active = False
    winner = max(bids, key=bids.get, default=None)
    if winner:
        await ctx.send(f"🎉 {bot.get_user(winner).mention} won the auction! {current_auction['owner'].mention}, please trade.")
        await log_event("Auction Ended", f"{bot.get_user(winner).mention} won the auction!", discord.Color.blue())

@bot.command()
async def ping(ctx):
    await ctx.send(f"🏓 Pong! Latency: {round(bot.latency * 1000)}ms")

bot.run(TOKEN)
