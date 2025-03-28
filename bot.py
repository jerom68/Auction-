import discord
from discord.ext import commands
import os
import threading
import asyncio
import uvicorn
from fastapi import FastAPI
import aiohttp  # For fetching Pokémon images

# Load environment variables
TOKEN = os.getenv("TOKEN")
SERVER_ID = int(os.getenv("SERVER_ID"))  # Ensure this is set in your environment variables
AUCTION_CHANNEL_ID = int(os.getenv("AUCTION_CHANNEL_ID"))
REGISTER_CHANNEL_ID = int(os.getenv("REGISTER_CHANNEL_ID"))
AUCTION_ROLE_ID = int(os.getenv("AUCTION_ROLE_ID"))
PORT = int(os.getenv("PORT", 8080))  # Default port for Render

# Discord bot setup
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# Auction-related variables
registrations = []
auction_active = False
bids = {}

# FastAPI app for Render's health check
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

async def get_pokemon_image(name):
    """Fetches the Pokémon image from PokéAPI."""
    url = f"https://pokeapi.co/api/v2/pokemon/{name.lower()}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                return data["sprites"]["other"]["official-artwork"]["front_default"]
            else:
                return None  # No image found

@bot.command()
async def register(ctx):
    if not has_auction_role(ctx.author):
        await ctx.send("❌ You do not have permission to register Pokémon.")
        return

    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel

    await ctx.send("Enter the Pokémon name:")
    name = await bot.wait_for("message", check=check)

    await ctx.send("Enter the starting bid:")
    starting_bid = await bot.wait_for("message", check=check)

    await ctx.send("Enter the minimum bid increment:")
    min_bid_increment = await bot.wait_for("message", check=check)

    image_url = await get_pokemon_image(name.content)

    pokemon = {
        "owner": ctx.author,
        "name": name.content,
        "starting_bid": int(starting_bid.content),
        "min_bid_increment": int(min_bid_increment.content),
        "image_url": image_url
    }
    registrations.append(pokemon)

    embed = discord.Embed(title="✅ Pokémon Registered!", color=discord.Color.green())
    embed.add_field(name="Pokémon Name", value=name.content, inline=False)
    embed.add_field(name="Starting Bid", value=starting_bid.content, inline=True)
    embed.add_field(name="Min Bid Increment", value=min_bid_increment.content, inline=True)
    embed.set_footer(text="Your Pokémon has been registered successfully!")
    
    if image_url:
        embed.set_thumbnail(url=image_url)

    await ctx.send(embed=embed)

@bot.command()
async def auctionstart(ctx):
    global auction_active, bids

    if auction_active:
        await ctx.send("❌ An auction is already in progress!")
        return

    if not registrations:
        await ctx.send("❌ No Pokémon have been registered for auction.")
        return

    auction_active = True
    current_auction = registrations.pop(0)

    embed = discord.Embed(title=f"✨ {current_auction['name']} Auction ✨", color=discord.Color.gold())
    embed.add_field(name="Starting Bid", value=f"{current_auction['starting_bid']}", inline=True)
    embed.add_field(name="Min Bid Increment", value=f"{current_auction['min_bid_increment']}", inline=True)
    embed.set_footer(text="Place your bid using !bid <amount>")

    if current_auction["image_url"]:
        embed.set_thumbnail(url=current_auction["image_url"])

    auction_channel = bot.get_channel(AUCTION_CHANNEL_ID)

    auction_rules = """
**🏆 Auction Rules 🏆**
- Place bids using `!bid <amount>`
- Each bid must be **higher** than the last bid
- Minimum increment: **{}**
- Only users with the auction role can participate
- The highest bid wins at the end of the auction!
""".format(current_auction["min_bid_increment"])

    await auction_channel.send(auction_rules)
    await auction_channel.send(embed=embed)
    bids.clear()

@bot.command()
async def bid(ctx, amount: int):
    global bids

    if not auction_active:
        await ctx.send("❌ There is no active auction right now.")
        return

    if bids and amount <= max(bids.values()):
        await ctx.send(f"❌ Your bid must be higher than the current highest bid.")
        return

    bids[ctx.author.id] = amount
    await ctx.send(f"✅ {ctx.author.mention} has placed a bid of {amount}!")

@bot.command()
async def ping(ctx):
    latency = round(bot.latency * 1000)
    await ctx.send(f"🏓 Pong! Latency: {latency}ms")

# Start the bot
bot.run(TOKEN)
