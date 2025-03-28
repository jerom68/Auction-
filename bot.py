import discord
import asyncio
import os
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("TOKEN")
LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID"))
AUCTION_CHANNEL_ID = int(os.getenv("AUCTION_CHANNEL_ID"))

bot = commands.Bot(command_prefix="!", intents=discord.Intents.all())

registrations = []
auction_active = False
bids = {}
current_auction = None

# 📌 Utility function for logging events in an embed
async def log_event(title, description, color=discord.Color.blue()):
    log_channel = bot.get_channel(LOG_CHANNEL_ID)
    if log_channel:
        embed = discord.Embed(title=title, description=description, color=color)
        await log_channel.send(embed=embed)

# ✅ !register command
@bot.command()
async def register(ctx):
    await ctx.send("📢 Enter Pokémon name (e.g., `Shiny Eevee` or `Gmax Charizard`):")
    name = await bot.wait_for("message", check=lambda m: m.author == ctx.author)
    
    await ctx.send("📢 Enter Pokémon level:")
    level = await bot.wait_for("message", check=lambda m: m.author == ctx.author)

    await ctx.send("📢 Enter Pokémon total IVs (%):")
    total_ivs = await bot.wait_for("message", check=lambda m: m.author == ctx.author)

    await ctx.send("📢 Enter Pokémon IVs (HP, ATK, DEF, SPATK, SPDEF, SPD) separated by spaces:")
    ivs = await bot.wait_for("message", check=lambda m: m.author == ctx.author)
    ivs = ivs.content.split()

    await ctx.send("📢 Enter starting bid amount:")
    starting_bid = await bot.wait_for("message", check=lambda m: m.author == ctx.author)

    await ctx.send("📢 Enter minimum bid increment:")
    min_bid_increment = await bot.wait_for("message", check=lambda m: m.author == ctx.author)

    # Store Pokémon info
    pokemon = {
        "name": name.content,
        "level": level.content,
        "total_ivs": total_ivs.content,
        "hp_iv": ivs[0],
        "atk_iv": ivs[1],
        "def_iv": ivs[2],
        "spatk_iv": ivs[3],
        "spdef_iv": ivs[4],
        "spd_iv": ivs[5],
        "starting_bid": starting_bid.content,
        "min_bid_increment": min_bid_increment.content,
        "owner": ctx.author.mention,
    }
    registrations.append(pokemon)

    # ✅ Register Embed
    embed = discord.Embed(
        title="✅ Pokémon Registered!",
        description=f"Your Pokémon `{pokemon['name']}` has been registered for auction.",
        color=discord.Color.green(),
    )
    embed.add_field(name="🔢 Level", value=pokemon["level"], inline=True)
    embed.add_field(name="📊 Total IVs", value=f"{pokemon['total_ivs']}%", inline=True)
    embed.add_field(
        name="⚔️ IV Stats",
        value=f"**HP:** {pokemon['hp_iv']} | **ATK:** {pokemon['atk_iv']} | **DEF:** {pokemon['def_iv']}\n"
              f"**SPATK:** {pokemon['spatk_iv']} | **SPDEF:** {pokemon['spdef_iv']} | **SPD:** {pokemon['spd_iv']}",
        inline=False,
    )
    await ctx.send(embed=embed)

    await log_event("📌 Pokémon Registered", f"{ctx.author.mention} registered `{pokemon['name']}` for auction.", discord.Color.green())

# ✅ !auctionstart command
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

    embed = discord.Embed(
        title=f"🔥 Auction Started for {current_auction['name']}!",
        description="**Place your bids now!** Use `!bid <amount>` to participate.",
        color=discord.Color.gold(),
    )

    embed.add_field(name="🆔 Pokémon", value=f"**{current_auction['name']}**", inline=True)
    embed.add_field(name="🔢 Level", value=f"{current_auction['level']}", inline=True)
    embed.add_field(name="📊 Total IVs", value=f"{current_auction['total_ivs']}%", inline=True)

    embed.add_field(
        name="⚔️ IV Stats",
        value=f"**HP:** {current_auction['hp_iv']} | **ATK:** {current_auction['atk_iv']} | **DEF:** {current_auction['def_iv']}\n"
              f"**SPATK:** {current_auction['spatk_iv']} | **SPDEF:** {current_auction['spdef_iv']} | **SPD:** {current_auction['spd_iv']}",
        inline=False,
    )

    embed.add_field(name="💰 Starting Bid", value=f"**{current_auction['starting_bid']}** credits", inline=True)
    embed.add_field(name="📈 Min Bid Increment", value=f"**{current_auction['min_bid_increment']}** credits", inline=True)
    embed.set_footer(text="🏆 Highest bid will win at the end of the timer!")

    auction_channel = bot.get_channel(AUCTION_CHANNEL_ID)
    await auction_channel.send(embed=embed)

    await asyncio.sleep(20)  # 20-second timer

    if not bids:
        auction_active = False
        await auction_channel.send("⚠️ No bids were placed. Auction has ended.")
        return

    highest_bidder = max(bids, key=bids.get)
    winner_amount = bids[highest_bidder]

    await auction_channel.send(f"🎉 {highest_bidder.mention} you won the auction for `{current_auction['name']}` at **{winner_amount} credits!**\n"
                               f"📌 {current_auction['owner']} please trade with {highest_bidder.mention}.")

    auction_active = False

# ✅ !bid command
@bot.command()
async def bid(ctx, amount: int):
    global bids

    if not auction_active:
        await ctx.send("❌ No active auction!")
        return

    if ctx.author in bids and amount <= bids[ctx.author]:
        await ctx.send("❌ You must bid a higher amount!")
        return

    bids[ctx.author] = amount
    await ctx.send(f"💸 {ctx.author.mention} placed a bid of **{amount} credits!**")

# ✅ !ping command
@bot.command()
async def ping(ctx):
    await ctx.send(f"🏓 Pong! {round(bot.latency * 1000)}ms")

# ✅ Start the bot
bot.run(TOKEN)
