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
    def __init__(self):
        super().__init__()

        self.add_item(discord.ui.TextInput(label="Pokémon Name", placeholder="Enter Pokémon name"))
        self.add_item(discord.ui.TextInput(label="Starting Bid", placeholder="Enter starting bid", style=discord.TextStyle.short))
        self.add_item(discord.ui.TextInput(label="Bid Increment", placeholder="Enter minimum bid increment", style=discord.TextStyle.short))
        self.add_item(discord.ui.TextInput(label="Level", placeholder="Enter Pokémon level", style=discord.TextStyle.short))
        self.add_item(discord.ui.TextInput(label="Total IVs", placeholder="Enter total IVs", style=discord.TextStyle.short))
        self.add_item(discord.ui.TextInput(label="HP IV", placeholder="Enter HP IV", style=discord.TextStyle.short))
        self.add_item(discord.ui.TextInput(label="ATK IV", placeholder="Enter ATK IV", style=discord.TextStyle.short))
        self.add_item(discord.ui.TextInput(label="DEF IV", placeholder="Enter DEF IV", style=discord.TextStyle.short))
        self.add_item(discord.ui.TextInput(label="SpA IV", placeholder="Enter SpA IV", style=discord.TextStyle.short))
        self.add_item(discord.ui.TextInput(label="SpD IV", placeholder="Enter SpD IV", style=discord.TextStyle.short))
        self.add_item(discord.ui.TextInput(label="SPD IV", placeholder="Enter Speed IV", style=discord.TextStyle.short))

    async def on_submit(self, interaction: discord.Interaction):
        global auction_data, bid_increment

        fields = [item.value for item in self.children]
        auction_data = {
            "pokemon": fields[0],
            "start_bid": int(fields[1]),
            "bid_increment": int(fields[2]),
            "level": int(fields[3]),
            "total_ivs": int(fields[4]),
            "ivs": {
                "HP": int(fields[5]),
                "ATK": int(fields[6]),
                "DEF": int(fields[7]),
                "SpA": int(fields[8]),
                "SpD": int(fields[9]),
                "SPD": int(fields[10]),
            },
        }
        bid_increment = int(fields[2])

        await interaction.response.send_message(f"✅ **Pokémon {fields[0]} has been registered for auction!**\n"
                                               f"**Starting Bid:** {fields[1]}\n"
                                               f"**Bid Increment:** {fields[2]}\n"
                                               f"**Level:** {fields[3]}\n"
                                               f"**Total IVs:** {fields[4]}")


# Command to register Pokémon
@bot.command(name="register")
async def register(ctx):
    await ctx.send("Please fill out the modal to register your Pokémon!", view=discord.ui.View().add_item(RegisterModal()))


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
