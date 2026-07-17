# Nyarth

from dotenv import load_dotenv
from functools import wraps

import os
import discord
import datetime
import random

from discord.ext import commands
from supabase import create_client

from functions import *
from data import *

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
URL = os.getenv("SUPABASE_URL")
KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(URL, KEY)

intents = discord.Intents.all()
bot = commands.Bot(
    command_prefix="%",
    help_command=None,
    intents=intents
)
bot.activity = discord.Game(name="Pokémon Red")

cache = Cache()

def command_timeout(timeout):
    def decorator(func):
        @wraps(func)
        async def wrapper(ctx, *args, **kwargs):
            # command timeout check
            if time_string := await command_timeout_check(ctx, cache.retrieve(ctx.author.name, f"{func.__name__}_timeout"), timeout):
                await ctx.send(f"❌ You can use this command again in `{time_string}`.")
                log(ctx, func.__name__, f"command timeout ({time_string} left)", error=True)
                return
            
            # active user check
            if cache.retrieve("active", ctx.author.name):
                await ctx.send(f"❌ You already have a command running!")
                log(ctx, func.__name__, "already has another command running", error=True)
                return

            # add user to active list
            cache.update("active", ctx.author.name, True)

            # run command
            failure = await func(ctx, *args, **kwargs)

            # update command timeout
            if failure is None:
                cache.update(ctx.author.name, f"{func.__name__}_timeout", datetime.datetime.now())
            
            # remove user from active list
            cache.update("active", ctx.author.name, False)

            return failure
        return wrapper
    return decorator

@bot.event
async def on_ready():
    guilds = "\n - ".join([f"{guild.name} (id: {guild.id})" for guild in bot.guilds])
    print(f"{bot.user} is active in the following guilds:")
    print(f" - {guilds}\n")
    me = bot.get_user(587040390603866122)
    await me.send("Nyeh heh heh...")
    print("Nyarth sent a DM to doduodrio (id: 587040390603866122) upon activating!\n")

@bot.command()
@command_timeout(0)
async def ping(ctx):
    await ctx.send(f"Pong!")
    log(ctx, "ping", "pinged bot")

@bot.command(aliases=["bal"])
@command_timeout(0)
async def balance(ctx, username=None):
    if username is None:
        user = ctx.author
    else:
        if (user := find_member(ctx, username)) is None:
            await ctx.send(f"❌ Member not found.")
            log(ctx, "balance", f"invalid member ({username})", error=True)
            return False

    balance = get_balance(cache, supabase, user.name)
    
    embed = discord.Embed(color=discord.Color.gold())
    embed.set_author(name=user.name, icon_url=user.avatar.url)
    embed.add_field(name="Balance", value=f"🪙{balance}")
    await ctx.send(embed=embed)
    log(ctx, "balance", f"got balance ({balance} coins) of {user.name} (id: {user.id})")

@bot.command()
@command_timeout(300)
async def work(ctx):
    amount = random.randint(1, 100)
    if random.randint(1, 10) == 1:
        # work fail (10%)
        await ctx.send(f"<@{ctx.author.id}> did a bad job at work! You lost 🪙{amount}...")
        amount *= -1
    else:
        # work success (90%)
        await ctx.send(f"<@{ctx.author.id}> did a good job at work! You got 🪙{amount}!")
    
    # get user balance and update it
    balance = get_balance(cache, supabase, ctx.author.name)
    supabase.table("user data").update({"balance": balance+amount}).eq("username", ctx.author.name).execute()
    cache.update(ctx.author.name, "balance", balance+amount)
    log(ctx, "work", f"earned {amount} coins")

@bot.command()
@command_timeout(15)
async def gamble(ctx, amount=None):
    # convert amount to an integer if it isn't "all"
    try:
        if amount.lower() == "all":
            amount = amount.lower()
        else:
            amount = int(amount)
    except:
        amount = None

    # catch invalid or negative amounts
    if (amount is None) or (amount != "all" and amount <= 0):
        await ctx.send(f"❌ Invalid amount specified.")
        log(ctx, "gamble", f"invalid amount ({amount})", error=True)
        return False
    
    # get user balance
    balance = get_balance(cache, supabase, ctx.author.name)
    
    # set amount if "all" was selected
    if amount == "all":
        if balance <= 0:
            await ctx.send(f"❌ You don't have enough 🪙 to gamble...")
            log(ctx, "gamble", f"cannot gamble ({balance} balance)")
            return False
        else:
            amount = balance
    
    if balance >= amount:
        new_amount = random.randint(0, 2*amount)
        new_balance = balance-amount+new_amount
        if new_balance > balance:
            await ctx.send(f"<@{ctx.author.id}> gambled and earned 🪙{new_balance - balance}!")
        else:
            await ctx.send(f"<@{ctx.author.id}> gambled and lost 🪙{balance - new_balance}...")
        log(ctx, "gamble", f"gambled {amount} -> {new_amount} ({new_amount-amount})")
        supabase.table("user data").update({"balance": new_balance}).eq("username", ctx.author.name).execute()
        cache.update(ctx.author.name, "balance", new_balance)
    else:
        await ctx.send(f"❌ You don't have enough 🪙 to gamble... You need {amount-balance} more 🪙!")
        log(ctx, "gamble", f"not enough money (missing {amount-balance} coins)", error=True)
        return False

@bot.command(aliases=["clear"])
async def clearcache(ctx):
    if ctx.author.name != "doduodrio":
        await ctx.send("❌ You can't use this command.")
        log(ctx, "clearcache", "can't use this command", error=True)
        return False
    else:
        cache.clear_all()
        await ctx.send(f"<@{ctx.author.id}> Cache cleared!")
        log(ctx, "clearcache", "cache cleared")

@bot.command()
@command_timeout(0)
async def give(ctx, username=None, amount=None):
    if username is None:
        await ctx.send("❌ Specify a member to give 🪙 to.")
        log(ctx, "give", "recipient not specified", error=True)
        return False
    
    if (recipient := find_member(ctx, username)) is None:
        await ctx.send(f"❌ Member not found.")
        log(ctx, "give", f"invalid member {username}", error=True)
        return False
    
    # convert amount to an integer if it isn't "all"
    try:
        if amount.lower() == "all":
            amount = amount.lower()
        else:
            amount = int(amount)
    except:
        amount = None

    # catch invalid or negative amounts
    if (amount is None) or (amount != "all" and amount <= 0):
        await ctx.send(f"❌ Invalid amount specified.")
        log(ctx, "give", f"invalid amount ({amount})", error=True)
        return False

    # cannot give yourself coins
    if ctx.author == recipient:
        await ctx.send(f"❌ You cannot give yourself 🪙")
        log(ctx, "give", "cannot give self coins", error=True)
        return False
    
    # get user balance
    balance = get_balance(cache, supabase, ctx.author.name)
    
    # get recipient balance
    recipient_balance = get_balance(cache, supabase, recipient.name)
    
    # set amount if "all" was selected
    if amount == "all":
        if balance <= 0:
            await ctx.send(f"❌ You don't have any 🪙 to give...")
            log(ctx, "give", f"cannot give coins (balance: {balance})", error=True)
            return False
        else:
            amount = balance
    
    if balance >= amount:
        await ctx.send(f"<@{ctx.author.id}> gave 🪙{amount} to <@{recipient.id}>!")
        supabase.table("user data").update({"balance": balance-amount}).eq("username", ctx.author.name).execute()
        supabase.table("user data").update({"balance": recipient_balance+amount}).eq("username", recipient.name).execute()
        cache.update(ctx.author.name, "balance", balance-amount)
        cache.update(recipient.name, "balance", recipient_balance+amount)
        log(ctx, "give", f"gave {amount} coins to {recipient.name}")
    else:
        await ctx.send(f"❌ You don't have enough 🪙 to give... You need {amount-balance} more 🪙!")
        log(ctx, "give", f"can't give {amount} coin to {recipient.name} (missing {amount-balance} coins)")
        return False

@bot.command(aliases=["lb"])
@command_timeout(0)
async def leaderboard(ctx: commands.Context, page=None):
    # validate page number
    try:
        if page is None:
            page = 1
        else:
            page = int(page)
    except:
        await ctx.send("❌ Invalid page number.")
        log(ctx, "leaderboard", f"invalid page number ({page})", error=True)
        return False

    # retrieve data
    response = supabase.table("user data").select("*").execute()
    # update cache
    for row in response.data:
        cache.update(row["username"], "balance", row["balance"])

    # convert data into a list of pairs
    lb = [(row["username"], row["balance"]) for row in response.data]
    lb.sort(key=lambda x: x[1], reverse=True)

    # remove members that aren't in the guild
    index = 0
    for i in range(len(lb)):
        if lb[index][0] not in [i.name for i in ctx.guild.members]:
            lb.pop(index)
        else:
            index += 1
    
    # remove bot users
    for member in ctx.guild.members:
        if member.name in [i[0] for i in lb] and member.bot:
            for i in range(len(lb)):
                if lb[i][0] == member.name:
                    lb.pop(i)
                    break
    
    # validate page number
    max_pages = max(int((len(lb)-1)/10+1), 1)
    if page > max_pages:
        await ctx.send("❌ Invalid page number.")
        log(ctx, "leaderboard", f"invalid page number ({page})", error=True)
        return False
    
    padding = len(str(lb[0][1])) # length of the highest balance
    
    # construct leaderboard string
    lb_string = "```"
    for i in range(10):
        if (page-1)*10+i < len(lb):
            lb_string += f"\n{(page-1)*10+i+1:>2}. 🪙{lb[(page-1)*10+i][1]:<{padding}} {lb[(page-1)*10+i][0]}"
    lb_string += "```"
    
    embed = discord.Embed(color=discord.Color.gold())
    embed.add_field(name=f"{ctx.guild.name} Leaderboard", value=lb_string)
    embed.set_footer(text=f"Page {page}/{max_pages}")
    await ctx.send(embed=embed)
    log(ctx, "leaderboard", f"displayed leaderboard for {ctx.guild.name}")

@bot.command()
@command_timeout(0)
async def roast(ctx, username=None):
    if username is None:
        user = ctx.author
    else:
        user = find_member(ctx, username)
        if user is None:
            await ctx.send(f"❌ Member not found.")
            log(ctx, "roast", f"invalid member ({username})", error=True)
            return False
    roast = random.choice(roasts)

    await ctx.send(f"<@{user.id}> {roast}")
    log(ctx, "roast", f"roasted {user.name} (id: {user.id}) \"{roast}\"")

@bot.command(aliases=["inv"])
@command_timeout(0)
async def inventory(ctx, page=None):
    # validate page number
    try:
        if page is None:
            page = 1
        else:
            page = int(page)
    except:
        await ctx.send("❌ Invalid page number.")
        log(ctx, "inventory", f"invalid page number ({page})", error=True)
        return False
    
    # retrieve inventory
    inv = get_inventory(cache, supabase, ctx.author.name)

    # validate page number
    max_pages = max(int((len(inv)-1)/10+1), 1)
    if page > max_pages:
        await ctx.send("❌ Invalid page number.")
        log(ctx, "inventory", f"invalid page number ({page})", error=True)
        return False

    embed = discord.Embed(color=discord.Color.gold())
    embed.set_author(name=f"{ctx.author.name}'s Inventory", icon_url=ctx.author.avatar.url)
    for item in inv:
        try:
            description = item["description"]
        except KeyError:
            try:
                description = items[item["name"]]["description"]
            except KeyError:
                description = "Description not found."
        embed.add_field(
            name=f"{item["icon"]} {item["name"].title()} x{item["count"]}",
            value=description,
            inline=False
        )
    embed.set_footer(text=f"Page {page}/{max_pages}")
    await ctx.send(embed=embed)
    log(ctx, "inventory", "got inventory")

@bot.command()
@command_timeout(0)
async def help(ctx, command_name=None):
    if command_name is None:
        embed = discord.Embed(color=discord.Color.gold())
        embed.set_author(name="Help Menu", icon_url=bot.user.avatar.url)
        for category, cat_commands in categories.items():
            embed.add_field(name=category.title(), value=", ".join([f"`{i["name"]}`" for i in cat_commands]), inline=False)
        await ctx.send(embed=embed)
        log(ctx, "help", "viewed all commands")
    else:
        command = None
        for c in commands:
            if c["name"] == command_name.lower() or command_name.lower() in c["aliases"]:
                command = c
                break
        if command is None:
            await ctx.send("❌ Command not found.")
            log(ctx, "help", f"couldn't find command {command_name}", error=True)
            return False
        embed = discord.Embed(
            title=command["name"],
            description=command["description"],
            color=discord.Color.gold()
        )
        if command["aliases"]:
            embed.add_field(name="Aliases", value=f"`{", ".join(command["aliases"])}`")
        embed.add_field(name="Usage", value=f"`{command["usage"]}`")
        embed.add_field(name="Category", value=command["category"].title())
        await ctx.send(embed=embed)
        log(ctx, "help", f"viewed command {command["name"]}")

@bot.command()
@command_timeout(0)
async def shop(ctx):
    shop_items = ["seedling", "bucket"]
    embed = discord.Embed(color=discord.Color.gold())
    embed.set_author(name="Nyarth's Shop", icon_url=bot.user.avatar.url)
    index = 1
    for item in shop_items:
        item = items[item]
        embed.add_field(name=f"[{index}] {item["icon"]} {item["name"].title()} - 🪙{item["price"]}", value=item["description"], inline=False)
        index += 1
    await ctx.send(embed=embed)
    log(ctx, "shop", "viewed the shop")

@bot.command()
@command_timeout(0)
async def buy(ctx, quantity=None, *args):
    if quantity is None and len(args) == 0:
        await ctx.send("❌ No item specified.")
        log(ctx, "buy", "no item specified", error=True)
        return False
    
    # get item name
    try:
        quantity = int(quantity)
        item_name = " ".join(args).lower()
    except:
        item_name = " ".join([quantity, *args]).lower()
        quantity = 1
    
    # get item data
    item = None
    for name, i in items.items():
        if item_name in name:
            item = i
            break
    
    # make sure item exists
    if item is None:
        await ctx.send("❌ Item not found.")
        log(ctx, "buy", f"item not found ({item_name})", error=True)
        return False
    
    # make sure item is sold in the shop
    shop_items = ["seedling", "bucket"]
    if item["name"] not in shop_items:
        await ctx.send("❌ Item can't be bought.")
        log(ctx, "buy", f"item can't be bought ({item_name})", error=True)
        return False
    
    # get user balance
    balance = get_balance(cache, supabase, ctx.author.name)
    
    # check if the user has enough money
    if balance < item["price"]*quantity:
        await ctx.send(f"❌ You don't have enough 🪙 to buy this! You need {item["price"]*quantity-balance} more 🪙!")
        log(ctx, "buy", f"not enough coins to buy {quantity} {item_name} (missing {item["price"]*quantity-balance} coins)", error=True)
        return False
    
    # confirmation
    await ctx.send(f"<@{ctx.author.id}> Are you sure you want to buy {quantity}x {item["icon"]} {item["name"].title()} for 🪙{item["price"]*quantity}? (y/n)")
    message = await bot.wait_for("message", check=lambda m: (m.content.lower() == "y" or m.content.lower() == "n") and m.channel == ctx.channel)
    if message.content.lower() != "y":
        await ctx.send(f"<@{ctx.author.id}> Purchase cancelled.")
        log(ctx, "buy", f"cancelled purchase of {quantity} {item["name"]} for {item["price"]*quantity} coins")
        return False
    
    # send message to user before making the slow api calls
    await ctx.send(f"<@{ctx.author.id}> bought {quantity}x {item["icon"]} {item["name"].title()} for 🪙{item["price"]*quantity}!")
    
    # deduct balance
    supabase.table("user data").update({"balance": balance-item["price"]*quantity}).eq("username", ctx.author.name).execute()
    cache.update(ctx.author.name, "balance", balance-item["price"]*quantity)

    # get inventory
    inv = get_inventory(cache, supabase, ctx.author.name)
    
    # add item to inventory
    if item["name"] in [i["name"] for i in inv]:
        for i in inv:
            if i["name"] == item["name"]:
                i["count"] += quantity
                break
    else:
        inv.append({
            "icon": item["icon"],
            "name": item["name"],
            "count": quantity
        })
    supabase.table("user data").update({"inventory": inv}).eq("username", ctx.author.name).execute()
    cache.update(ctx.author.name, "inventory", inv)

    # log purchase
    log(ctx, "buy", f"bought {quantity} {item["name"]} for {item["price"]*quantity} coins")

@bot.command()
@command_timeout(0)
async def sell(ctx, quantity=None, *args):
    if quantity is None and len(args) == 0:
        await ctx.send("❌ No item specified.")
        log(ctx, "sell", "no item specified", error=True)
        return False
    
    # get item name
    try:
        quantity = int(quantity)
        item_name = " ".join(args).lower()
    except:
        if quantity.lower() == "all":
            item_name = " ".join(args).lower()
        else:
            item_name = " ".join([quantity, *args]).lower()
            quantity = 1
    
    # get inventory
    inv = get_inventory(cache, supabase, ctx.author.name)

    # make sure item is in the inventory
    item_index = -1
    for i in range(len(inv)): # check for exact matches
        if item_name == inv[i]["name"]:
            item_index = i
            break
    if item_index == -1: # check for approximate matches
        for i in range(len(inv)):
            if item_name in inv[i]["name"]:
                item_index = i
                break

    if item_index == -1:
        await ctx.send("❌ You don't have this item!")
        log(ctx, "sell", f"doesn't have item ({item_name})", error=True)
        return False
    
    if quantity == "all":
        quantity = inv[item_index]["count"]

    # make sure there is enough of the item in the inventory
    if inv[item_index]["count"] < quantity:
        await ctx.send("❌ You don't have enough to sell!")
        log(ctx, "sell", f"doesn't have enough to sell (has {item["count"]} {item_name}, wants to sell {quantity})", error=True)
        return False
    
    # get item data
    try:
        item = items[inv[item_index]["name"]]
    except KeyError:
        await ctx.send("❌ This item can't be sold!")
        log(ctx, "sell", f"can't sell item ({item_name})", error=True)
        return False
    
    # confirmation
    await ctx.send(f"<@{ctx.author.id}> Are you sure you want to sell {quantity}x {item["icon"]} {item["name"].title()} for 🪙{item["price"]*quantity}? (y/n)")
    message = await bot.wait_for("message", check=lambda m: (m.content.lower() == "y" or m.content.lower() == "n") and m.channel == ctx.channel)
    if message.content.lower() != "y":
        await ctx.send(f"<@{ctx.author.id}> Sale cancelled.")
        log(ctx, "sell", f"cancelled sale of {quantity} {item["name"]} for {item["price"]*quantity} coins")
        return False

    # send message to user before making more api calls
    await ctx.send(f"<@{ctx.author.id}> sold {quantity}x {item["icon"]} {item["name"].title()} for 🪙{item["price"]*quantity}!")
    
    # get user balance
    balance = get_balance(cache, supabase, ctx.author.name)

    # increase balance
    supabase.table("user data").update({"balance": balance+item["price"]*quantity}).eq("username", ctx.author.name).execute()
    cache.update(ctx.author.name, "balance", balance+item["price"]*quantity)
    
    # remove item from inventory
    if inv[item_index]["name"] == item["name"]:
        if inv[item_index]["count"]-quantity == 0:
            inv.pop(item_index)
        else:
            inv[item_index]["count"] -= quantity
    supabase.table("user data").update({"inventory": inv}).eq("username", ctx.author.name).execute()
    cache.update(ctx.author.name, "inventory", inv)

    # log sale
    log(ctx, "sell", f"sold {quantity} {item["name"]} for {item["price"]*quantity} coins")

@bot.command()
@command_timeout(0)
async def farm(ctx, mode=None):
    # retrieve farm data
    farm_data = get_farm_data(cache, supabase, ctx.author.name)
    
    # update farm (check if any seedlings have matured or any corn has expired)
    farm_data = update_farm_data(cache, supabase, ctx.author.name, farm_data)
    
    # view farm
    if mode is None: # view whole farm
        embed = discord.Embed(
            description="{}{}{}\n{}{}{}\n{}{}{}".format(*[i["icon"] for i in farm_data]),
            color=discord.Color.gold()
        )
        embed.set_author(name=f"{ctx.author.name}'s Farm", icon_url=ctx.author.avatar.url)
        await ctx.send(embed=embed)
        log(ctx, "farm", "viewed farm")
        return
    
    try: # view a specific tile
        mode = int(mode)
        embed = discord.Embed(color=discord.Color.gold())
        embed.set_author(name=f"{ctx.author.name}'s Farm", icon_url=ctx.author.avatar.url)
        embed.add_field(name="Contents", value=f"{farm_data[mode-1]["icon"]} {farm_data[mode-1]["contents"].title()}")
        if farm_data[mode-1]["time"]:
            if farm_data[mode-1]["contents"] == "seedling":
                embed.add_field(name="Harvest", value=f"<t:{int(farm_data[mode-1]["time"])}:R>")
            else:
                embed.add_field(name="Expires", value=f"<t:{int(farm_data[mode-1]["time"])}:R>")
        embed.set_footer(text=f"Viewing Tile {mode}")
        await ctx.send(embed=embed)
        log(ctx, "farm", f"viewed tile {mode}")
    except:
        mode = mode.lower()
        if mode.lower() in ["d", "detail", "details"]: # detailed view
            embed = discord.Embed(color=discord.Color.gold())
            embed.set_author(name=f"{ctx.author.name}'s Farm", icon_url=ctx.author.avatar.url)
            for i in range(9):
                message = "Harvest" if farm_data[i]["contents"] == "seedling" else "Expires" if farm_data[i]["contents"] != "dirt" else "It's dirt."
                if farm_data[i]["time"]:
                    message += f"<t:{int(farm_data[i]["time"])}:R>"
                embed.add_field(name=f"[{i+1}] {farm_data[i]["icon"]} {farm_data[i]["contents"].title()}", value=message)
            await ctx.send(embed=embed)
            log(ctx, "farm", "viewed detailed view")
        else: # invalid parameter
            await ctx.send("❌ Invalid parameter.")
            log(ctx, "farm", f"invalid parameter ({mode})", error=True)
            return False

@bot.command()
@command_timeout(0)
async def plant(ctx, tile=None):
    # retrieve farm data
    farm_data = get_farm_data(cache, supabase, ctx.author.name)
    
    # update farm (check if any seedlings have matured or any corn has expired)
    farm_data = update_farm_data(cache, supabase, ctx.author.name, farm_data)
    
    # validate tile if provided
    if tile is not None:
        try:
            tile = int(tile)
            if tile <= 0 or tile > 9:
                raise Exception
        except:
            await ctx.send("❌ Invalid tile. Please select a tile from 1 - 9.")
            log(ctx, "plant", f"invalid tile ({tile})", error=True)
            return False
    
    # generate list of plantable tiles
    if tile is not None:
        plantable_tiles = [tile] if farm_data[tile-1]["contents"] == "dirt" else []
    else:
        plantable_tiles = [i+1 for i in range(9) if farm_data[i]["contents"] == "dirt"]
    
    if len(plantable_tiles) == 0:
        await ctx.send("❌ You can't plant there.")
        log(ctx, "plant", "can't plant", error=True)
        return False
    
    # retrieve inventory
    inv = get_inventory(cache, supabase, ctx.author.name)
    
    # make sure the user has a seedling to plant
    seedling_index = -1
    for i in range(len(inv)):
        if inv[i]["name"] == "seedling":
            seedling_index = i
            break
    
    if seedling_index == -1:
        await ctx.send("❌ You don't have any seedlings!")
        log(ctx, "plant", "doesn't have any seedlings", error=True)
        return False
    
    # cap the plantable tiles at the number of seedlings the user has
    while len(plantable_tiles) > inv[seedling_index]["count"]:
        plantable_tiles.pop()
    
    # send message to user before making more api calls
    ready_time = datetime.datetime.now().timestamp()+3600
    if len(plantable_tiles) == 1:
        await ctx.send(f"<@{ctx.author.id}> planted a 🌱 in Tile {plantable_tiles[0]}! It will be fully grown <t:{int(ready_time)}:R>")
    else:
        await ctx.send(f"<@{ctx.author.id}> planted {len(plantable_tiles)}x 🌱 in Tiles {", ".join([str(i) for i in plantable_tiles])}! They will be fully grown <t:{int(ready_time)}:R>")
    
    # remove seedlings from the inventory
    if inv[seedling_index]["name"] == "seedling":
        if inv[seedling_index]["count"] - len(plantable_tiles) == 0:
            inv.pop(seedling_index)
        else:
            inv[seedling_index]["count"] -= len(plantable_tiles)
    supabase.table("user data").update({"inventory": inv}).eq("username", ctx.author.name).execute()
    cache.update(ctx.author.name, "inventory", inv)

    # plant the seedlings
    for i in plantable_tiles:
        farm_data[i-1] = {
            "contents": "seedling",
            "icon": "🌱",
            "time": ready_time
        }
    supabase.table("user data").update({"farm": farm_data}).eq("username", ctx.author.name).execute()
    cache.update(ctx.author.name, "farm", farm_data)
    log(ctx, "plant", f"planted {len(plantable_tiles)} seedlings")

@bot.command()
@command_timeout(0)
async def harvest(ctx, tile=None):
    # retrieve farm data
    farm_data = get_farm_data(cache, supabase, ctx.author.name)
    
    # update farm (check if any seedlings have matured or any corn has expired)
    farm_data = update_farm_data(cache, supabase, ctx.author.name, farm_data, update=False)
    
    # validate tile if provided
    if tile is not None:
        try:
            tile = int(tile)
            if tile <= 0 or tile > 9:
                raise Exception
        except:
            await ctx.send("❌ Invalid tile. Please select a tile from 1 - 9.")
            log(ctx, "harvest", f"invalid tile {tile}", error=True)
            return False
    
    # generate list of tiles to harvest (1-9)
    if tile is not None:
        harvest_tiles = [tile] if farm_data[tile-1]["contents"] == "corn" else []
    else:
        harvest_tiles = [i+1 for i in range(9) if farm_data[i]["contents"] == "corn"]

    # make sure there is corn to harvest
    if len(harvest_tiles) == 0:
        await ctx.send("❌ There is nothing to harvest.")
        log(ctx, "harvest", "nothing to harvest", error=True)
        return False
    
    # send message to user before making more api calls
    harvested_corn = sum([random.randint(1, 5) for i in harvest_tiles])
    if len(harvest_tiles) == 1:
        harvest_tile_string = f"Tile {harvest_tiles[0]}"
    else:
        harvest_tile_string = f"Tiles {", ".join([str(i) for i in harvest_tiles])}"
    await ctx.send(f"<@{ctx.author.id}> harvested {harvested_corn} 🌽 from {harvest_tile_string}!")

    # remove corn from farm
    for i in harvest_tiles:
        farm_data[i-1] = {
            "contents": "dirt",
            "icon": "🟫",
            "time": ""
        }
    supabase.table("user data").update({"farm": farm_data}).eq("username", ctx.author.name).execute()
    cache.update(ctx.author.name, "farm", farm_data)

    # get inventory
    inv = get_inventory(cache, supabase, ctx.author.name)

    # add corn to inventory
    if "corn" in [i["name"] for i in inv]:
        for i in inv:
            if i["name"] == "corn":
                i["count"] += harvested_corn
                break
    else:
        inv.append({
            "icon": "🌽",
            "name": "corn",
            "count": harvested_corn
        })
    supabase.table("user data").update({"inventory": inv}).eq("username", ctx.author.name).execute()
    cache.update(ctx.author.name, "inventory", inv)

    log(ctx, "harvest", f"harvested {harvested_corn} corn")

@bot.command()
@command_timeout(300)
async def water(ctx, tile=None):
    if tile is None:
        await ctx.send("❌ No tile specified.")
        log(ctx, "water", "no tile specified", error=True)
        return False
    
    # validate tile
    try:
        tile = int(tile)
        if tile <= 0 or tile > 9:
            raise Exception
    except:
        await ctx.send("❌ Invalid tile. Please select a tile from 1 - 9.")
        log(ctx, "water", f"invalid tile ({tile})", error=True)
        return False
    
    # get inventory
    inv = get_inventory(cache, supabase, ctx.author.name)

    # make sure the user has a bucket
    if "bucket" not in [i["name"] for i in inv]:
        await ctx.send("❌ You don't have a bucket to water with!")
        log(ctx, "water", "no bucket", error=True)
        return False
    
    # retrieve farm data
    if (farm_data := cache.retrieve(ctx.author.name, "farm")) is None:
        response = supabase.table("user data").select("*").eq("username", ctx.author.name).execute()
        if response.data and response.data[0]["farm"]:
            farm_data = response.data[0]["farm"]
        else:
            farm_data = [
                {
                    "contents": "dirt",
                    "icon": "🟫",
                    "time": ""
                } for i in range(9)
            ]
            supabase.table("user data").update({"farm": farm_data}).eq("username", ctx.author.name).execute()
        cache.update(ctx.author.name, "farm", farm_data)

    # make sure selected tile is a seedling
    if farm_data[tile-1]["contents"] != "seedling":
        await ctx.send(f"❌ You can't water {farm_data[tile-1]["icon"]}!")
        log(ctx, "water", f"can't water {farm_data[tile-1]["contents"]}")
        return False
    
    # speed up harvest by 5 minutes
    farm_data[tile-1]["time"] -= 300
    await ctx.send(f"<@{ctx.author.id}> watered the 🌱 in Tile {tile}! It will grow a bit faster!")
    log(ctx, "water", f"watered tile {tile}")

    # update farm
    supabase.table("user data").update({"farm": farm_data}).eq("username", ctx.author.name).execute()
    cache.update(ctx.author.name, "farm", farm_data)

bot.run(TOKEN)