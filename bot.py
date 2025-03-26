import discord
from discord.ext import commands
import asyncio
import os

# Bot Setup
intents = discord.Intents.all()
bot = commands.Bot(command_prefix=commands.when_mentioned, intents=intents)

# Auction Data Storage
auctions = []
bidders = {}

# Auction Role ID (Replace with your role ID)
AUCTION_ROLE_ID = 1234567890  
LOG_CHANNEL_ID = 1234567890  
AUCTION_CHANNEL_ID = 1234567890  
REGISTRATION_CHANNEL_ID = 1234567890  

# Slash Command for Registration
@bot.slash_command(name="register", description="Register a Pokémon for auction.")
async def register(ctx, pokemon_name: str, sb: int, bi: int, level: int, total_ivs: int, hp_iv: int, atk_iv: int, def_iv: int, spdef_iv: int, spatk_iv: int, spd_iv: int):
    if AUCTION_ROLE_ID not in [role.id for role in ctx.author.roles]:
        await ctx.respond("You don't have permission to register Pokémon.", ephemeral=True)
        return

    auction_data = {
        "owner": ctx.author.mention,
        "pokemon": pokemon_name,
        "sb": sb,
        "bi": bi,
        "level": level,
        "total_ivs": total_ivs,
        "ivs": f"HP: {hp_iv}, ATK: {atk_iv}, DEF: {def_iv}, SPDEF: {spdef_iv}, SPATK: {spatk_iv}, SPD: {spd_iv}",
        "highest_bid": sb,
        "highest_bidder": None
    }
    auctions.append(auction_data)
    await ctx.respond(f"✅ **{pokemon_name}** registered for auction!")

# Start Auction Command
@bot.command(name="as")
async def start_auction(ctx):
    if ctx.channel.id != AUCTION_CHANNEL_ID:
        return

    if len(auctions) == 0:
        await ctx.send("No Pokémon registered for auction today.")
        return

    for auction in auctions:
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

        # Lock channel, post auction, unlock channel
        await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=False)
        auction_msg = await ctx.send(embed=embed)
        await ctx.channel.send("🔹 **Only bidding allowed. No chatting!**")
        await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=True)

        await asyncio.sleep(10)  # Wait 10s before allowing bids
        await bid_countdown(ctx, auction_msg, auction)

# Bidding Command
@bot.command(name="bid")
async def place_bid(ctx, amount: int):
    if ctx.channel.id != AUCTION_CHANNEL_ID:
        return

    if AUCTION_ROLE_ID not in [role.id for role in ctx.author.roles]:
        await ctx.send("You don't have permission to bid.")
        return

    if not auctions:
        await ctx.send("No active auction.")
        return

    auction = auctions[0]  

    if amount < auction["highest_bid"] + auction["bi"]:
        await ctx.send(f"Bid must be at least **{auction['highest_bid'] + auction['bi']} credits**.")
        return

    auction["highest_bid"] = amount
    auction["highest_bidder"] = ctx.author.mention
    await ctx.send(f"🎉 **{ctx.author.mention}** is now the highest bidder with **{amount} credits**!")

# Bidding Countdown
async def bid_countdown(ctx, auction_msg, auction):
    await asyncio.sleep(10)  

    if auction["highest_bidder"]:
        await ctx.send(f"🏆 {auction['highest_bidder']} wins the **{auction['pokemon']}** for **{auction['highest_bid']} credits**!")
        await ctx.send(f"{auction['owner']}, auction ended. Please trade.")
    else:
        await ctx.send("No bids placed. Auction ended.")

    auctions.remove(auction)

# Error Handling
@bot.event
async def on_command_error(ctx, error):
    await ctx.send(f"⚠️ Error: {error}")

# Start Bot
bot.run(os.getenv("DISCORD_TOKEN"))
