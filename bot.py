import discord
from discord.ext import commands
import asyncio
import os

# Load environment variables
TOKEN = os.getenv("TOKEN")
SERVER_ID = int(os.getenv("SERVER_ID"))
AUCTION_CHANNEL_ID = int(os.getenv("AUCTION_CHANNEL_ID"))
REGISTER_CHANNEL_ID = int(os.getenv("REGISTER_CHANNEL_ID"))
LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID"))
AUCTION_ROLE_ID = int(os.getenv("AUCTION_ROLE_ID"))

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# Dictionary to store auction registrations
registrations = {}

# Auction-related variables
current_auction = None
bids = {}
auction_active = False

# Helper function to check for role
def has_auction_role(user):
    return any(role.id == AUCTION_ROLE_ID for role in user.roles)

# Registration Command
@bot.command()
async def register(ctx):
    """Guided Pokémon registration system."""
    if not has_auction_role(ctx.author):
        await ctx.send("You do not have permission to register Pokémon for auctions.")
        return

    questions = [
        "Enter Pokémon Name:",
        "Enter Starting Bid Amount:",
        "Enter Minimum Bid Increment:",
        "Enter Pokémon Level:",
        "Enter Total IVs:",
        "Enter HP IV:",
        "Enter ATK IV:",
        "Enter DEF IV:",
        "Enter SpA IV:",
        "Enter SpD IV:",
        "Enter SPD IV:"
    ]

    answers = []

    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel

    for question in questions:
        await ctx.send(question)
        try:
            msg = await bot.wait_for("message", check=check, timeout=120)
            answers.append(msg.content)
        except asyncio.TimeoutError:
            await ctx.send("Registration timed out. Please try again.")
            return

    registrations[ctx.author.id] = {
        "name": answers[0], "starting_bid": int(answers[1]), "min_bid_increment": int(answers[2]),
        "level": int(answers[3]), "total_ivs": int(answers[4]),
        "hp_iv": int(answers[5]), "atk_iv": int(answers[6]), "def_iv": int(answers[7]),
        "spa_iv": int(answers[8]), "spd_iv": int(answers[9]), "spd_iv": int(answers[10])
    }

    embed = discord.Embed(title="✅ Pokémon Registered!", color=discord.Color.green())
    embed.add_field(name="Pokémon Name", value=answers[0], inline=False)
    embed.add_field(name="Starting Bid", value=answers[1], inline=True)
    embed.add_field(name="Min Bid Increment", value=answers[2], inline=True)
    embed.add_field(name="Level", value=answers[3], inline=True)
    embed.add_field(name="Total IVs", value=answers[4], inline=False)
    embed.add_field(name="IVs", value=f"HP: {answers[5]}, ATK: {answers[6]}, DEF: {answers[7]}, SPA: {answers[8]}, SPD: {answers[9]}, SPD: {answers[10]}", inline=False)

    await ctx.send(embed=embed)

# Auction Start Command
@bot.command()
async def auctionstart(ctx):
    """Starts an auction if there are registered Pokémon."""
    global current_auction, bids, auction_active

    if ctx.author.id not in registrations:
        await ctx.send("You have not registered any Pokémon.")
        return

    if auction_active:
        await ctx.send("An auction is already in progress!")
        return

    auction_active = True
    current_auction = registrations.pop(ctx.author.id)

    embed = discord.Embed(title=f"✨ {current_auction['name']} Auction ✨", color=discord.Color.gold())
    embed.add_field(name="Starting Bid", value=f"{current_auction['starting_bid']}", inline=True)
    embed.add_field(name="Min Bid Increment", value=f"{current_auction['min_bid_increment']}", inline=True)
    embed.add_field(name="Level", value=f"{current_auction['level']}", inline=True)
    embed.add_field(name="Total IVs", value=f"{current_auction['total_ivs']}", inline=True)
    embed.add_field(name="IVs", value=f"HP: {current_auction['hp_iv']}, ATK: {current_auction['atk_iv']}, DEF: {current_auction['def_iv']}, SPA: {current_auction['spa_iv']}, SPD: {current_auction['spd_iv']}", inline=False)
    embed.set_footer(text="Place your bid using !bid <amount>")

    auction_channel = bot.get_channel(AUCTION_CHANNEL_ID)
    await auction_channel.send(embed=embed)

    bids = {}

# Bidding Command
@bot.command()
async def bid(ctx, amount: int):
    """Places a bid on the current auction."""
    global bids

    if not auction_active:
        await ctx.send("There is no active auction right now.")
        return

    if amount < current_auction["starting_bid"]:
        await ctx.send("Your bid must be at least the starting bid.")
        return

    if bids and amount <= max(bids.values()) + current_auction["min_bid_increment"]:
        await ctx.send(f"You must bid at least {max(bids.values()) + current_auction['min_bid_increment']}.")
        return

    bids[ctx.author.id] = amount
    await ctx.send(f"{ctx.author.mention} has placed a bid of {amount}!")

# Auction End Command
@bot.command()
async def auctionend(ctx):
    """Ends the auction and announces the winner."""
    global auction_active, current_auction, bids

    if not auction_active:
        await ctx.send("No auction is currently active.")
        return

    if not bids:
        await ctx.send("No bids were placed. Auction canceled.")
        auction_active = False
        return

    winner_id = max(bids, key=bids.get)
    winner = ctx.guild.get_member(winner_id)
    winning_bid = bids[winner_id]

    embed = discord.Embed(title=f"🏆 Auction Ended - Winner: {winner.name} 🏆", color=discord.Color.blue())
    embed.add_field(name="Winning Bid", value=f"{winning_bid}", inline=False)
    embed.set_footer(text="Trade with the owner to claim your Pokémon!")

    auction_channel = bot.get_channel(AUCTION_CHANNEL_ID)
    await auction_channel.send(embed=embed)

    auction_active = False
    current_auction = None
    bids = {}

# Auction Leaderboard Command
@bot.command()
async def leaderboard(ctx):
    """Displays top 5 users who bid the most."""
    sorted_bidders = sorted(bids.items(), key=lambda x: x[1], reverse=True)[:5]

    embed = discord.Embed(title="🏅 Top 5 Bidders 🏅", color=discord.Color.purple())
    for user_id, amount in sorted_bidders:
        user = ctx.guild.get_member(user_id)
        embed.add_field(name=user.name, value=f"Bid: {amount}", inline=False)

    await ctx.send(embed=embed)

# Run the bot
if __name__ == "__main__":
    import os
    port = int(os.getenv("PORT", 5000))  # Required for Render
    bot.run(TOKEN)
