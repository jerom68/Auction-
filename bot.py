import discord
from discord.ext import commands
import os
import asyncio
import threading
import flask

TOKEN = os.getenv("DISCORD_BOT_TOKEN")
AUCTION_CHANNEL_ID = int(os.getenv("AUCTION_CHANNEL_ID", "0"))
REGISTER_CHANNEL_ID = int(os.getenv("REGISTER_CHANNEL_ID", "0"))
LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID", "0"))  # Added log channel
PORT = int(os.getenv("PORT", "8080"))  # Port for Render hosting

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# Ensure bot syncs commands on startup
@bot.event
async def on_ready():
    await bot.tree.sync()  # Sync slash commands
    print(f"Logged in as {bot.user}")

# Lowercase modal for Pokémon Registration
class registermodal(discord.ui.Modal, title="Register Pokémon for Auction"):
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
                                               f"**Total IVs:** {fields[4]}", ephemeral=True)


# **Slash command for /register**
@bot.tree.command(name="register", description="Register a Pokémon for auction")
async def register(interaction: discord.Interaction):
    await interaction.response.send_modal(registermodal())

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
