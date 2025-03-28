import discord
from discord.ext import commands
import os
import threading
import asyncio
import uvicorn
from fastapi import FastAPI
import requests

# Load environment variables
TOKEN = os.getenv("TOKEN")
SERVER_ID = int(os.getenv("SERVER_ID"))
AUCTION_CHANNEL_ID = int(os.getenv("AUCTION_CHANNEL_ID"))
REGISTER_CHANNEL_ID = int(os.getenv("REGISTER_CHANNEL_ID"))
AUCTION_ROLE_ID = int(os.getenv("AUCTION_ROLE_ID"))
LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID"))
PORT = int(os.getenv("PORT", 8080))

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
    """Automatically leaves any unauthorized servers."""
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

    await ctx.send("Enter the Pokémon level:")
    level = await bot.wait_for("message", check=check)

    await ctx.send("Enter Total IVs:")
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

    # Fetch Pokémon image from API
    pokemon_image_url = f"https://img.pokemondb.net/artwork/large/{name.content.lower()}.jpg"

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
        "min_bid_increment": int(min_bid_increment.content),
        "image_url": pokemon_image_url
    }
    registrations.append(pokemon)

    embed = discord.Embed(title="✅ Pokémon Registered!", color=discord.Color.green())
    embed.set_thumbnail(url=pokemon_image_url)
    embed.add_field(name="Pokémon Name", value=name.content, inline=False)
    embed.add_field(name="Level", value=level.content, inline=True)
    embed.add_field(name="Total IVs", value=total_ivs.content, inline=True)
    embed.add_field(name="HP IV", value=hp_iv.content, inline=True)
    embed.add_field(name="ATK IV", value=atk_iv.content, inline=True)
    embed.add_field(name="DEF IV", value=def_iv.content, inline=True)
    embed.add_field(name="SPATK IV", value=spatk_iv.content, inline=True)
    embed.add_field(name="SPDEF IV", value=spdef_iv.content, inline=True)
    embed.add_field(name="SPD IV", value=spd_iv.content, inline=True)
    embed.add_field(name="Starting Bid", value=starting_bid.content, inline=True)
    embed.add_field(name="Min Bid Increment", value=min_bid_increment.content, inline=True)
    embed.set_footer(text="Your Pokémon has been registered successfully!")

    await ctx.send(embed=embed)

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
    current_auction = registrations.pop(0)

    embed = discord.Embed(title=f"✨ {current_auction['name']} Auction ✨", color=discord.Color.gold())
    embed.set_thumbnail(url=current_auction["image_url"])
    embed.add_field(name="Level", value=current_auction["level"], inline=True)
    embed.add_field(name="Total IVs", value=current_auction["total_ivs"], inline=True)
    embed.add_field(name="HP IV", value=current_auction["hp_iv"], inline=True)
    embed.add_field(name="ATK IV", value=current_auction["atk_iv"], inline=True)
    embed.add_field(name="DEF IV", value=current_auction["def_iv"], inline=True)
    embed.add_field(name="SPATK IV", value=current_auction["spatk_iv"], inline=True)
    embed.add_field(name="SPDEF IV", value=current_auction["spdef_iv"], inline=True)
    embed.add_field(name="SPD IV", value=current_auction["spd_iv"], inline=True)
    embed.add_field(name="Starting Bid", value=current_auction["starting_bid"], inline=True)
    embed.add_field(name="Min Bid Increment", value=current_auction["min_bid_increment"], inline=True)
    embed.set_footer(text="Place your bid using !bid <amount>")

    auction_channel = bot.get_channel(AUCTION_CHANNEL_ID)
    await auction_channel.send(embed=embed)

    # Start 10-second timer
    await asyncio.sleep(10)
    await auctionend(ctx)

@bot.command()
async def auctionend(ctx):
    global auction_active, current_auction, bids

    if not auction_active:
        await ctx.send("❌ No auction is currently running.")
        return

    auction_active = False

    if bids:
        winner_id = max(bids, key=bids.get)
        winner = await bot.fetch_user(winner_id)
        await ctx.send(f"Hey {winner.mention}, you have won the auction for {current_auction['name']}!")
        await ctx.send(f"🎉| {current_auction['owner'].mention} Please trade with {winner.mention}.")
    else:
        await ctx.send("❌ No bids were placed. Auction ended.")

    current_auction = None
    bids.clear()

@bot.command()
async def ping(ctx):
    latency = round(bot.latency * 1000)
    await ctx.send(f"🏓 Pong! Latency: {latency}ms")

# Start the bot
bot.run(TOKEN)
