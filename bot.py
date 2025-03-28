import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import os

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

TOKEN = os.getenv("TOKEN")
AUCTION_CHANNEL_ID = int(os.getenv("AUCTION_CHANNEL_ID"))  # Channel where auctions happen
LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID"))  # Channel for logging

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)  # Set a command prefix for compatibility

# ---------------------------- Slash Command: /register ----------------------------

class RegisterModal(discord.ui.Modal, title="Register a Pokémon"):
    name = discord.ui.TextInput(label="Pokémon Name", placeholder="Enter Pokémon Name")
    start_bid = discord.ui.TextInput(label="Starting Bid", placeholder="Enter starting bid", required=True)
    bid_increment = discord.ui.TextInput(label="Bid Increment", placeholder="Enter minimum bid increment", required=True)
    level = discord.ui.TextInput(label="Level", placeholder="Enter Pokémon level", required=True)
    total_ivs = discord.ui.TextInput(label="Total IVs", placeholder="Enter total IVs", required=True)
    hp_iv = discord.ui.TextInput(label="HP IV", placeholder="Enter HP IV", required=True)
    atk_iv = discord.ui.TextInput(label="ATK IV", placeholder="Enter ATK IV", required=True)
    def_iv = discord.ui.TextInput(label="DEF IV", placeholder="Enter DEF IV", required=True)
    spa_iv = discord.ui.TextInput(label="SpA IV", placeholder="Enter SpA IV", required=True)
    spd_iv = discord.ui.TextInput(label="SpD IV", placeholder="Enter SpD IV", required=True)
    spd_iv_2 = discord.ui.TextInput(label="SPD IV", placeholder="Enter SPD IV", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        embed = discord.Embed(title="Pokémon Registered", color=discord.Color.green())
        embed.add_field(name="Pokémon", value=self.name.value, inline=True)
        embed.add_field(name="Starting Bid", value=self.start_bid.value, inline=True)
        embed.add_field(name="Bid Increment", value=self.bid_increment.value, inline=True)
        embed.add_field(name="Level", value=self.level.value, inline=True)
        embed.add_field(name="Total IVs", value=self.total_ivs.value, inline=False)
        embed.add_field(name="IVs", value=f"HP: {self.hp_iv.value}, ATK: {self.atk_iv.value}, DEF: {self.def_iv.value}, SpA: {self.spa_iv.value}, SpD: {self.spd_iv.value}, SPD: {self.spd_iv_2.value}", inline=False)

        auction_channel = bot.get_channel(AUCTION_CHANNEL_ID)
        if auction_channel:
            await auction_channel.send(embed=embed)

        log_channel = bot.get_channel(LOG_CHANNEL_ID)
        if log_channel:
            await log_channel.send(f"New Pokémon registered by {interaction.user.mention}", embed=embed)

        await interaction.response.send_message("Your Pokémon has been registered!", ephemeral=True)

@bot.tree.command(name="register", description="Register a Pokémon for the auction.")
async def register(interaction: discord.Interaction):
    await interaction.response.send_modal(RegisterModal())

# ---------------------------- Bidding System ----------------------------

active_auction = None
highest_bidder = None
highest_bid = 0

@bot.command(name="start_auction")
async def start_auction(ctx, pokemon: str, start_bid: int, bid_increment: int):
    global active_auction, highest_bidder, highest_bid

    active_auction = pokemon
    highest_bid = start_bid
    highest_bidder = None

    embed = discord.Embed(title=f"Auction Started: {pokemon}", color=discord.Color.blue())
    embed.add_field(name="Starting Bid", value=f"{start_bid} credits", inline=True)
    embed.add_field(name="Bid Increment", value=f"{bid_increment} credits", inline=True)
    embed.set_footer(text="Use !bid <amount> to place a bid.")

    await ctx.send(embed=embed)

    log_channel = bot.get_channel(LOG_CHANNEL_ID)
    if log_channel:
        await log_channel.send(f"Auction started for {pokemon} by {ctx.author.mention}.")

@bot.command(name="bid")
async def bid(ctx, amount: int):
    global highest_bid, highest_bidder, active_auction

    if active_auction is None:
        await ctx.send("No active auction right now!")
        return

    if amount <= highest_bid:
        await ctx.send(f"Your bid must be higher than the current highest bid: {highest_bid} credits.")
        return

    highest_bid = amount
    highest_bidder = ctx.author

    await ctx.send(f"{ctx.author.mention} is now the highest bidder with {amount} credits!")

    log_channel = bot.get_channel(LOG_CHANNEL_ID)
    if log_channel:
        await log_channel.send(f"New bid: {ctx.author.mention} bid {amount} credits on {active_auction}.")

# ---------------------------- Moderation Commands ----------------------------

@bot.command(name="warn")
async def warn(ctx, member: discord.Member, *, reason: str):
    embed = discord.Embed(title="Warning Issued", color=discord.Color.orange())
    embed.add_field(name="User", value=member.mention, inline=True)
    embed.add_field(name="Reason", value=reason, inline=False)
    
    await ctx.send(embed=embed)

    log_channel = bot.get_channel(LOG_CHANNEL_ID)
    if log_channel:
        await log_channel.send(f"{member.mention} was warned by {ctx.author.mention} for: {reason}")

@bot.command(name="blacklist")
async def blacklist(ctx, member: discord.Member):
    await ctx.send(f"{member.mention} has been blacklisted from bidding.")

    log_channel = bot.get_channel(LOG_CHANNEL_ID)
    if log_channel:
        await log_channel.send(f"{member.mention} was blacklisted by {ctx.author.mention}.")

# ---------------------------- Ping Command ----------------------------

@bot.command(name="ping")
async def ping(ctx):
    latency = round(bot.latency * 1000, 2)
    await ctx.send(f"Pong! 🏓 {latency}ms")

# ---------------------------- Bot Events ----------------------------

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} slash commands.")
    except Exception as e:
        print(f"Error syncing commands: {e}")

bot.run(TOKEN)
