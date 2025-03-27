import os
import discord
from discord.ext import commands
from discord import app_commands
import asyncio
from flask import Flask

TOKEN = os.getenv("DISCORD_BOT_TOKEN")
AUCTION_CHANNEL_ID = int(os.getenv("AUCTION_CHANNEL_ID"))
REGISTER_CHANNEL_ID = int(os.getenv("REGISTER_CHANNEL_ID"))
LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID"))
AUCTION_ROLE_ID = int(os.getenv("AUCTION_ROLE_ID"))
PORT = int(os.getenv("PORT", 8080))  # Default port 8080

# Enable all intents
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="@", intents=intents)

# Flask Web Server for Render
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is running!"

def run_flask():
    app.run(host="0.0.0.0", port=PORT)

auctions = []  # Stores auction Pokémon details

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    await bot.tree.sync()
    print("Slash commands synced!")

    # Send a log message when the bot starts
    log_channel = bot.get_channel(LOG_CHANNEL_ID)
    if log_channel:
        await log_channel.send("✅ Bot has started and is online!")

# Slash Command for Registration
@bot.tree.command(name="register", description="Register a Pokémon for auction")
@app_commands.describe(
    pokemon="Pokémon Name",
    sb="Starting Bid",
    bi="Bid Increment",
    level="Pokémon Level",
    total_ivs="Total IVs",
    hp_iv="HP IV",
    atk_iv="ATK IV",
    def_iv="DEF IV",
    spdef_iv="SPDEF IV",
    spatk_iv="SPATK IV",
    spd_iv="SPD IV"
)
async def register(interaction: discord.Interaction, pokemon: str, sb: int, bi: int, level: int, total_ivs: int, hp_iv: int, atk_iv: int, def_iv: int, spdef_iv: int, spatk_iv: int, spd_iv: int):
    if AUCTION_ROLE_ID not in [role.id for role in interaction.user.roles]:
        return await interaction.response.send_message("You do not have permission to register Pokémon.", ephemeral=True)
    
    if len(auctions) >= 10:
        return await interaction.response.send_message("Auction slots are full for today!", ephemeral=True)

    auction_data = {
        "owner": interaction.user.mention,
        "pokemon": pokemon,
        "sb": sb,
        "bi": bi,
        "level": level,
        "total_ivs": total_ivs,
        "ivs": f"HP: {hp_iv}, ATK: {atk_iv}, DEF: {def_iv}, SPDEF: {spdef_iv}, SPATK: {spatk_iv}, SPD: {spd_iv}",
        "highest_bid": None,
        "highest_bidder": None
    }
    auctions.append(auction_data)

    await interaction.response.send_message(f"✅ **{pokemon} registered for auction!**", ephemeral=True)

@bot.command()
async def auctionstart(ctx):
    if ctx.channel.id != AUCTION_CHANNEL_ID:
        return

    if not auctions:
        return await ctx.send("No Pokémon are registered for auction today.")

    await ctx.send("🚀 **Auction Starting Now!** 🚀")
    
    for auction in auctions:
        await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=False)
        
        embed = discord.Embed(
            title=f"✨ {auction['pokemon']} Auction ✨" if "shiny" in auction["pokemon"].lower() else f"{auction['pokemon']} Auction",
            description=f"**Owner:** {auction['owner']}\n"
                        f"**Starting Bid:** {auction['sb']} credits\n"
                        f"**Bid Increment:** {auction['bi']} credits\n"
                        f"**Level:** {auction['level']}\n"
                        f"**Total IVs:** {auction['total_ivs']}\n"
                        f"**IVs:** {auction['ivs']}",
            color=discord.Color.blue()
        )
        embed.set_footer(text="Place your bid using @bot bid <amount>")
        message = await ctx.send(embed=embed)

        await asyncio.sleep(3)
        await ctx.send("📜 **Auction Rules:**\n- Only bidding allowed.\n- Use `@bot bid <amount>` to place a bid.\n- No chatting allowed.")
        await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=True)
        
        highest_bid = auction["sb"]
        highest_bidder = None

        for _ in range(10):  # 10 rounds of bidding max
            try:
                msg = await bot.wait_for("message", timeout=10, check=lambda m: m.channel.id == ctx.channel.id and m.content.startswith("@bot bid"))
                bid_amount = int(msg.content.split()[2])

                if bid_amount >= highest_bid + auction["bi"]:
                    highest_bid = bid_amount
                    highest_bidder = msg.author
                    await ctx.send(f"💰 **New Highest Bid:** {highest_bid} credits by {highest_bidder.mention}")

            except asyncio.TimeoutError:
                break

        await ctx.send(f"⏳ No new bids, finalizing auction...")

        if highest_bidder:
            await ctx.send(f"🎉 **Auction Won by {highest_bidder.mention} for {highest_bid} credits!**")
            await ctx.send(f"{auction['owner']} Auction Ended. Please trade.")

        auctions.remove(auction)

    await ctx.send("🎯 **Today's Auctions Have Ended!**")

# Run Flask in a separate thread to keep bot alive
import threading
threading.Thread(target=run_flask, daemon=True).start()

bot.run(TOKEN)
