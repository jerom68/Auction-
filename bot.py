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
LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID"))
AUCTION_ROLE_ID = int(os.getenv("AUCTION_ROLE_ID"))
PORT = int(os.getenv("PORT", 8080))

# Discord bot setup
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# Auction-related variables
registrations = []
auction_active = False
bids = {}
current_auction = None
auction_timer = None

# FastAPI app for Render's health check
app = FastAPI()

@app.get("/")
async def home():
    return {"status": "Bot is running!"}

def run_api():
    uvicorn.run(app, host="0.0.0.0", port=PORT)

threading.Thread(target=run_api, daemon=True).start()

def has_auction_role(user):
    return any(role.id == AUCTION_ROLE_ID for role in user.roles)

@bot.event
async def on_ready():
    print(f"✅ {bot.user} is online and running!")

@bot.command()
async def ping(ctx):
    latency = round(bot.latency * 1000)  # Convert to milliseconds
    await ctx.send(f"🏓 Pong! `{latency}ms`")

@bot.command()
async def register(ctx):
    if not has_auction_role(ctx.author):
        await ctx.send("❌ You do not have permission to register Pokémon.")
        return

    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel

    await ctx.send("Enter the Pokémon name:")
    name_msg = await bot.wait_for("message", check=check)
    user_input = name_msg.content.strip()

    is_shiny = user_input.lower().startswith("shiny ")
    is_gmax = user_input.lower().startswith("gmax ")
    
    if is_shiny:
        pokemon_name = user_input[6:].strip()
    elif is_gmax:
        pokemon_name = user_input[5:].strip()
    else:
        pokemon_name = user_input

    await ctx.send("Enter the Pokémon level:")
    level_msg = await bot.wait_for("message", check=check)

    await ctx.send("Enter total IVs:")
    total_ivs_msg = await bot.wait_for("message", check=check)

    await ctx.send("Enter HP IV:")
    hp_iv_msg = await bot.wait_for("message", check=check)

    await ctx.send("Enter ATK IV:")
    atk_iv_msg = await bot.wait_for("message", check=check)

    await ctx.send("Enter DEF IV:")
    def_iv_msg = await bot.wait_for("message", check=check)

    await ctx.send("Enter SPATK IV:")
    spatk_iv_msg = await bot.wait_for("message", check=check)

    await ctx.send("Enter SPDEF IV:")
    spdef_iv_msg = await bot.wait_for("message", check=check)

    await ctx.send("Enter SPD IV:")
    spd_iv_msg = await bot.wait_for("message", check=check)

    await ctx.send("Enter the starting bid:")
    starting_bid_msg = await bot.wait_for("message", check=check)

    await ctx.send("Enter the minimum bid increment:")
    min_bid_increment_msg = await bot.wait_for("message", check=check)

    await ctx.send("Enter the Pokémon image URL:")
    image_url_msg = await bot.wait_for("message", check=check)

    pokemon = {
        "owner": ctx.author,
        "name": pokemon_name,
        "is_shiny": is_shiny,
        "is_gmax": is_gmax,
        "level": level_msg.content,
        "total_ivs": total_ivs_msg.content,
        "hp_iv": hp_iv_msg.content,
        "atk_iv": atk_iv_msg.content,
        "def_iv": def_iv_msg.content,
        "spatk_iv": spatk_iv_msg.content,
        "spdef_iv": spdef_iv_msg.content,
        "spd_iv": spd_iv_msg.content,
        "starting_bid": int(starting_bid_msg.content),
        "min_bid_increment": int(min_bid_increment_msg.content),
        "image_url": image_url_msg.content
    }
    registrations.append(pokemon)

    await ctx.send("✅ Pokémon Registered!")

@bot.command()
async def auctionstart(ctx):
    global auction_active, bids, current_auction, auction_timer

    if auction_active:
        await ctx.send("❌ An auction is already in progress!")
        return

    if not registrations:
        await ctx.send("❌ No Pokémon have been registered for auction.")
        return

    auction_active = True
    current_auction = registrations.pop(0)
    bids.clear()

    embed_title = f"✨ {('Shiny ' if current_auction['is_shiny'] else '')}{('Gmax ' if current_auction['is_gmax'] else '')}{current_auction['name']} Auction ✨"
    embed = discord.Embed(title=embed_title, color=discord.Color.gold())
    embed.add_field(name="Starting Bid", value=f"{current_auction['starting_bid']}", inline=True)
    embed.add_field(name="Min Bid Increment", value=f"{current_auction['min_bid_increment']}", inline=True)
    embed.set_thumbnail(url=current_auction["image_url"])
    embed.set_footer(text="Place your bid using !bid <amount>")

    auction_channel = bot.get_channel(AUCTION_CHANNEL_ID)
    await auction_channel.send(embed=embed)

    async def auction_timer_func():
        await asyncio.sleep(10)
        await auctionend(ctx)

    auction_timer = asyncio.create_task(auction_timer_func())

@bot.command()
async def bid(ctx, amount: int):
    global bids

    if not auction_active:
        await ctx.send("❌ No active auction!")
        return

    if amount < current_auction["starting_bid"]:
        await ctx.send("❌ Your bid must be at least the starting bid!")
        return

    if bids:
        highest_bid = max(bids.values())
        min_increment = current_auction["min_bid_increment"]
        if amount < highest_bid + min_increment:
            await ctx.send(f"❌ Your bid must be at least {highest_bid + min_increment}!")
            return

    bids[ctx.author] = amount
    await ctx.send(f"✅ {ctx.author.mention} placed a bid of {amount}!")

@bot.command()
async def auctionend(ctx):
    global auction_active, bids, current_auction, auction_timer

    if not auction_active:
        await ctx.send("❌ No active auction to end!")
        return

    if bids:
        highest_bidder = max(bids, key=bids.get)
        highest_bid = bids[highest_bidder]
        auction_winner_msg = f"🎉 {highest_bidder.mention} won the auction for {('Shiny ' if current_auction['is_shiny'] else '')}{('Gmax ' if current_auction['is_gmax'] else '')}{current_auction['name']} with {highest_bid}!"
    else:
        auction_winner_msg = "❌ No bids placed. Auction ended."

    auction_active = False
    current_auction = None
    bids.clear()

    await ctx.send(auction_winner_msg)

bot.run(TOKEN)
