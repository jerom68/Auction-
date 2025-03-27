import discord
from discord.ext import commands
import os
import asyncio

# Load environment variables
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
AUCTION_CHANNEL_ID = int(os.getenv("AUCTION_CHANNEL_ID", "0"))
REGISTER_CHANNEL_ID = int(os.getenv("REGISTER_CHANNEL_ID", "0"))
LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID", "0"))
AUCTION_ROLE_ID = int(os.getenv("AUCTION_ROLE_ID", "0"))
PORT = int(os.getenv("PORT", "8080"))  # Port for Render hosting

# Enable all intents
intents = discord.Intents.all()

# Set up the bot
bot = commands.Bot(command_prefix="!", intents=intents)

# Store auction data
auction_data = None
highest_bid = 0
highest_bidder = None
auction_active = False
bid_increment = 0


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    print("Bot is ready!")


# Registration command
@bot.slash_command(name="register", description="Register a Pokémon for auction.")
async def register(ctx, pokemon: str, start_bid: int, bid_increment_value: int, level: int, total_ivs: int, hp_iv: int, atk_iv: int, def_iv: int, spa_iv: int, spd_iv: int, spe_iv: int):
    role = discord.utils.get(ctx.guild.roles, id=AUCTION_ROLE_ID)
    if role not in ctx.author.roles:
        await ctx.respond("You don't have permission to register Pokémon!", ephemeral=True)
        return

    global auction_data, bid_increment
    auction_data = {
        "pokemon": pokemon,
        "start_bid": start_bid,
        "bid_increment": bid_increment_value,
        "level": level,
        "total_ivs": total_ivs,
        "ivs": {"HP": hp_iv, "ATK": atk_iv, "DEF": def_iv, "SpA": spa_iv, "SpD": spd_iv, "SPD": spe_iv},
    }
    bid_increment = bid_increment_value

    await ctx.respond(f"Pokémon {pokemon} registered for auction with a starting bid of {start_bid}!")


# Auction start command
@bot.command(name="auctionstart")
async def start_auction(ctx):
    global auction_data, auction_active, highest_bid, highest_bidder

    if auction_active:
        await ctx.send("An auction is already in progress!")
        return
    if not auction_data:
        await ctx.send("No Pokémon registered for auction.")
        return

    auction_active = True
    highest_bid = auction_data["start_bid"]
    highest_bidder = None

    auction_embed = discord.Embed(
        title=f"{'✨ ' if 'shiny' in auction_data['pokemon'].lower() else ''}{auction_data['pokemon']} Auction {'✨ ' if 'shiny' in auction_data['pokemon'].lower() else ''}",
        description=f"**Starting Bid:** {auction_data['start_bid']}\n**Bid Increment:** {auction_data['bid_increment']}\n**Level:** {auction_data['level']}\n**Total IVs:** {auction_data['total_ivs']}\n**Stats:** {auction_data['ivs']}",
        color=discord.Color.blue()
    )
    
    auction_channel = bot.get_channel(AUCTION_CHANNEL_ID)
    if auction_channel:
        await auction_channel.send(embed=auction_embed)
    else:
        await ctx.send("Auction channel is not set properly.")


# Bidding command
@bot.command()
async def bid(ctx, amount: int):
    global highest_bid, highest_bidder, auction_active, bid_increment

    if not auction_active:
        await ctx.send("No auction is currently active!")
        return
    if amount < highest_bid + bid_increment:
        await ctx.send(f"Minimum bid must be at least {highest_bid + bid_increment}!")
        return

    highest_bid = amount
    highest_bidder = ctx.author
    await ctx.send(f"{ctx.author.mention} placed a bid of {amount}!")

    # Start countdown
    await countdown(ctx)


async def countdown(ctx):
    global highest_bidder, auction_active

    await asyncio.sleep(10)
    if highest_bidder:
        for i in range(5, 0, -1):
            await ctx.send(f"Auction closing in {i} seconds...")
            await asyncio.sleep(1)
        await ctx.send(f"Auction ended! {highest_bidder.mention} won with {highest_bid}!")
        auction_active = False


# Cancel auction command (Admin only)
@bot.command()
@commands.has_permissions(administrator=True)
async def cancel(ctx):
    global auction_active

    if not auction_active:
        await ctx.send("No auction to cancel!")
        return

    auction_active = False
    await ctx.send("Auction has been cancelled.")


# Auction history command
@bot.command(name="auction_history")
async def auction_history(ctx):
    await ctx.send("Feature coming soon!")


# Leaderboard command
@bot.command(name="leaderboard")
async def leaderboard(ctx):
    await ctx.send("Feature coming soon!")


# Moderation commands
@bot.command()
@commands.has_permissions(manage_messages=True)
async def warn(ctx, member: discord.Member, *, reason="No reason provided"):
    log_channel = bot.get_channel(LOG_CHANNEL_ID)
    if log_channel:
        await log_channel.send(f"{member.mention} was warned for: {reason}")
    await ctx.send(f"{member.mention} has been warned.")


@bot.command()
@commands.has_permissions(manage_messages=True)
async def blacklist(ctx, member: discord.Member):
    await ctx.send(f"{member.mention} has been blacklisted from bidding.")


@bot.command()
@commands.has_permissions(manage_messages=True)
async def unblacklist(ctx, member: discord.Member):
    await ctx.send(f"{member.mention} has been removed from the blacklist.")


@bot.command()
@commands.has_permissions(manage_channels=True)
async def setrules(ctx, *, rules):
    await ctx.send(f"Auction rules updated:\n{rules}")


@bot.command()
@commands.has_permissions(manage_channels=True)
async def setannounce(ctx, channel: discord.TextChannel):
    global ANNOUNCEMENT_CHANNEL_ID
    ANNOUNCEMENT_CHANNEL_ID = channel.id
    await ctx.send(f"Auction announcement channel set to {channel.mention}")


# Run the bot
bot.run(TOKEN)
