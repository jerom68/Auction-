import discord
from discord.ext import commands
import os
import asyncio
import threading
import flask

# Load environment variables
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
AUCTION_CHANNEL_ID = int(os.getenv("AUCTION_CHANNEL_ID", "0"))
REGISTER_CHANNEL_ID = int(os.getenv("REGISTER_CHANNEL_ID", "0"))
LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID", "0"))
AUCTION_ROLE_ID = int(os.getenv("AUCTION_ROLE_ID", "0"))
PORT = int(os.getenv("PORT", "8080"))  # Port for Render hosting

# Enable all intents
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# Auction data storage
auction_data = None
highest_bid = 0
highest_bidder = None
auction_active = False
bid_increment = 0


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    print("Bot is ready!")


# Modal for Pokémon Registration
class RegisterModal(discord.ui.Modal, title="Register Pokémon for Auction"):
    def __init__(self, ctx):
        super().__init__()
        self.ctx = ctx

        self.pokemon = discord.ui.TextInput(label="Pokémon Name", placeholder="Enter Pokémon name")
        self.start_bid = discord.ui.TextInput(label="Starting Bid", placeholder="Enter starting bid", style=discord.TextStyle.short)
        self.bid_increment_value = discord.ui.TextInput(label="Bid Increment", placeholder="Enter minimum bid increment", style=discord.TextStyle.short)
        self.level = discord.ui.TextInput(label="Level", placeholder="Enter Pokémon level", style=discord.TextStyle.short)
        self.total_ivs = discord.ui.TextInput(label="Total IVs", placeholder="Enter total IVs", style=discord.TextStyle.short)
        self.hp_iv = discord.ui.TextInput(label="HP IV", placeholder="Enter HP IV", style=discord.TextStyle.short)
        self.atk_iv = discord.ui.TextInput(label="ATK IV", placeholder="Enter ATK IV", style=discord.TextStyle.short)
        self.def_iv = discord.ui.TextInput(label="DEF IV", placeholder="Enter DEF IV", style=discord.TextStyle.short)
        self.spa_iv = discord.ui.TextInput(label="SpA IV", placeholder="Enter SpA IV", style=discord.TextStyle.short)
        self.spd_iv = discord.ui.TextInput(label="SpD IV", placeholder="Enter SpD IV", style=discord.TextStyle.short)
        self.spe_iv = discord.ui.TextInput(label="SPE IV", placeholder="Enter Speed IV", style=discord.TextStyle.short)

        self.add_item(self.pokemon)
        self.add_item(self.start_bid)
        self.add_item(self.bid_increment_value)
        self.add_item(self.level)
        self.add_item(self.total_ivs)
        self.add_item(self.hp_iv)
        self.add_item(self.atk_iv)
        self.add_item(self.def_iv)
        self.add_item(self.spa_iv)
        self.add_item(self.spd_iv)
        self.add_item(self.spe_iv)

    async def on_submit(self, interaction: discord.Interaction):
        role = discord.utils.get(interaction.guild.roles, id=AUCTION_ROLE_ID)
        if role not in interaction.user.roles:
            await interaction.response.send_message("You don't have permission to register Pokémon!", ephemeral=True)
            return

        global auction_data, bid_increment
        auction_data = {
            "pokemon": self.pokemon.value,
            "start_bid": int(self.start_bid.value),
            "bid_increment": int(self.bid_increment_value.value),
            "level": int(self.level.value),
            "total_ivs": int(self.total_ivs.value),
            "ivs": {
                "HP": int(self.hp_iv.value),
                "ATK": int(self.atk_iv.value),
                "DEF": int(self.def_iv.value),
                "SpA": int(self.spa_iv.value),
                "SpD": int(self.spd_iv.value),
                "SPD": int(self.spe_iv.value),
            },
        }
        bid_increment = int(self.bid_increment_value.value)

        await interaction.response.send_message(f"Pokémon {self.pokemon.value} registered for auction with a starting bid of {self.start_bid.value}!")


# Command to register Pokémon
@bot.command(name="register")
async def register(ctx):
    modal = RegisterModal(ctx)
    await ctx.send("Please fill out the modal to register your Pokémon!", view=modal)


# Auction start command
@bot.command(name="auctionstart")
async def auction_start(ctx):
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
        title=f"{'✨ ' if 'shiny' in auction_data['pokemon'].lower() else ''}{auction_data['pokemon']} Auction{' ✨' if 'shiny' in auction_data['pokemon'].lower() else ''}",
        description=(
            f"**Starting Bid:** {auction_data['start_bid']}\n"
            f"**Bid Increment:** {auction_data['bid_increment']}\n"
            f"**Level:** {auction_data['level']}\n"
            f"**Total IVs:** {auction_data['total_ivs']}\n"
            f"**Stats:** {auction_data['ivs']}"
        ),
        color=discord.Color.blue()
    )

    auction_channel = bot.get_channel(AUCTION_CHANNEL_ID)
    if auction_channel:
        await auction_channel.send(embed=auction_embed)
    else:
        await ctx.send("Auction channel is not set properly.")


# Bidding command
@bot.command(name="bid")
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
    asyncio.create_task(countdown(ctx))


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
@bot.command(name="cancel")
@commands.has_permissions(administrator=True)
async def cancel(ctx):
    global auction_active

    if not auction_active:
        await ctx.send("No auction to cancel!")
        return

    auction_active = False
    await ctx.send("Auction has been cancelled.")


# Moderation commands
@bot.command(name="warn")
@commands.has_permissions(manage_messages=True)
async def warn(ctx, member: discord.Member, *, reason="No reason provided"):
    log_channel = bot.get_channel(LOG_CHANNEL_ID)
    if log_channel:
        await log_channel.send(f"{member.mention} was warned for: {reason}")
    await ctx.send(f"{member.mention} has been warned.")


@bot.command(name="blacklist")
@commands.has_permissions(manage_messages=True)
async def blacklist(ctx, member: discord.Member):
    await ctx.send(f"{member.mention} has been blacklisted from bidding.")


@bot.command(name="unblacklist")
@commands.has_permissions(manage_messages=True)
async def unblacklist(ctx, member: discord.Member):
    await ctx.send(f"{member.mention} has been removed from the blacklist.")


# Keep bot alive with a port for Render
app = flask.Flask(__name__)

@app.route("/")
def home():
    return "Bot is running!"

def run_flask():
    app.run(host="0.0.0.0", port=PORT, threaded=True)

# Run Flask in a separate thread
threading.Thread(target=run_flask, daemon=True).start()

# Run the bot
bot.run(TOKEN)
