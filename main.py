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

class Cache():
    def __init__(self):
        self.cache = {}
    
    def retrieve(self, user, key):
        try:
            return self.cache[user][key]
        except KeyError:
            return None
    
    def update(self, user, key, value):
        try:
            self.cache[user][key] = value
        except KeyError:
            self.cache[user] = {}
            self.cache[user][key] = value
    
    def clear_all(self):
        self.cache = {}

cache = Cache()

items = {
    "corn": {
        "name": "corn",
        "icon": "🌽",
        "description": "An ear of juicy corn, ready for popping.",
        "price": 20
    },
    "popcorn": {
        "name": "popcorn",
        "icon": "🍿",
        "description": "A steaming box of buttery popcorn.",
        "price": 100
    },
    "seedling": {
        "name": "seedling",
        "icon": "🌱",
        "description": "Plant one and watch it grow!",
        "price": 20
    },
    "bucket": {
        "name": "bucket",
        "icon": "🪣",
        "description": "Water your seedlings to make them grow faster!",
        "price": 100
    }
}

def command_timeout(timeout):
    def decorator(func):
        @wraps(func)
        async def wrapper(ctx, *args, **kwargs):
            # command timeout check
            if await command_timeout_check(ctx, cache.retrieve(ctx.author.name, f"{func.__name__}_timeout"), timeout):
                return
            
            # active user check
            if cache.retrieve("active", ctx.author.name):
                await ctx.send(f"❌ You already have a command running!")
                print(f"{now()} [{ctx.author.name}] {func.__name__}: already has another command running")
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
    print(f"{now()} ping: pinged bot")

@bot.command(aliases=["bal"])
@command_timeout(0)
async def balance(ctx, username=None):
    if username is None:
        user = ctx.author
    else:
        user = find_member(ctx, username)
        if user is None:
            await ctx.send(f"❌ Member not found.")
            print(f"[ERROR] {now()} [{ctx.author.name}] balance: invalid member {username}")
            return False

    balance = get_balance(cache, supabase, user.name)
    
    embed = discord.Embed(color=discord.Color.gold())
    embed.set_author(name=user.name, icon_url=user.avatar.url)
    embed.add_field(name="Balance", value=f"🪙{balance}")
    await ctx.send(embed=embed)
    print(f"{now()} [{ctx.author.name}] balance: got balance ({balance} coins) of {user.name} (id: {user.id})")

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
    print(f"{now()} [{ctx.author.name}] work: earned {amount} coins")

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
        print(f"[ERROR] {now()} [{ctx.author.name}] gamble: invalid amount")
        return False
    
    # get user balance
    if (balance := cache.retrieve(ctx.author.name, "balance")) is None:
        balance = get_balance(cache, supabase, ctx.author.name)
    
    # set amount if "all" was selected
    if amount == "all":
        if balance <= 0:
            await ctx.send(f"❌ You don't have enough 🪙 to gamble...")
            print(f"[ERROR] {now()} [{ctx.author.name}] gamble: cannot gamble ({balance} balance)")
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
        print(f"{now()} [{ctx.author.name}] gamble: gambled {amount} -> {new_amount}")
        supabase.table("user data").update({"balance": new_balance}).eq("username", ctx.author.name).execute()
        cache.update(ctx.author.name, "balance", new_balance)
    else:
        await ctx.send(f"❌ You don't have enough 🪙 to gamble... You need {amount-balance} more 🪙!")
        print(f"[ERROR] {now()} [{ctx.author.name}] gamble: not enough money (missing {amount-balance} coins)")
        return False

@bot.command(aliases=["clear"])
async def clearcache(ctx):
    if ctx.author.name != "doduodrio":
        await ctx.send("❌ You can't use this command.")
        print(f"[ERROR] {now()} [{ctx.author.name}] clearcache: can't use this command")
        return False
    else:
        cache.clear_all()
        await ctx.send(f"<@{ctx.author.id}> Cache cleared!")
        print(f"{now()} [{ctx.author.name}] clearcache: cache cleared")

@bot.command()
@command_timeout(0)
async def give(ctx, username=None, amount=None):
    if username is None:
        await ctx.send("❌ Specify a member to give 🪙 to.")
        print(f"[ERROR] {now()} [{ctx.author.name}] give: recipient not specified")
        return False
    
    recipient = find_member(ctx, username)
    
    if recipient is None:
        await ctx.send(f"❌ Member not found.")
        print(f"[ERROR] {now()} [{ctx.author.name}] give: invalid member {username}")
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
        print(f"[ERROR] {now()} [{ctx.author.name}] give: invalid amount")
        return False

    # cannot give yourself coins
    if ctx.author == recipient:
        await ctx.send(f"❌ You cannot give yourself 🪙")
        print(f"[ERROR] {now()} [{ctx.author.name}] give: cannot give self coins")
        return False
    
    # get user balance
    if (balance := cache.retrieve(ctx.author.name, "balance")) is None:
        balance = get_balance(cache, supabase, ctx.author.name)
    
    # get recipient balance 
    if (recipient_balance := cache.retrieve(recipient.name, "balance")) is None:
        balance = get_balance(cache, supabase, recipient.name)
    
    # set amount if "all" was selected
    if amount == "all":
        if balance <= 0:
            await ctx.send(f"❌ You don't have any 🪙 to give...")
            print(f"[ERROR] {now()} [{ctx.author.name}] give: cannot give ({balance} balance)")
            return False
        else:
            amount = balance
    
    if balance >= amount:
        await ctx.send(f"<@{ctx.author.id}> gave 🪙{amount} to <@{recipient.id}>!")
        supabase.table("user data").update({"balance": balance-amount}).eq("username", ctx.author.name).execute()
        supabase.table("user data").update({"balance": recipient_balance+amount}).eq("username", recipient.name).execute()
        cache.update(ctx.author.name, "balance", balance-amount)
        cache.update(recipient.name, "balance", recipient_balance+amount)
        print(f"{now()} [{ctx.author.name}] give: gave {amount} coins to {recipient.name}")
    else:
        await ctx.send(f"❌ You don't have enough 🪙 to give... You need {amount-balance} more 🪙!")
        print(f"[ERROR] {now()} [{ctx.author.name}] give: not enough money (missing {amount-balance} coins)")
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
        print(f"[ERROR] {now()} [{ctx.author.name}] leaderboard: invalid page number {page}")
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
        print(f"[ERROR] {now()} [{ctx.author.name}] leaderboard: invalid page number {page}")
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
    print(f"{now()} [{ctx.author.name}] leaderboard: displayed leaderboard for {ctx.guild.name}")

@bot.command()
@command_timeout(0)
async def roast(ctx, username=None):
    if username is None:
        user = ctx.author
    else:
        user = find_member(ctx, username)
        if user is None:
            await ctx.send(f"❌ Member not found.")
            print(f"[ERROR] {now()} [{ctx.author.name}] balance: invalid member {username}")
            return False
    
    roasts = [
        "You have a face that would make onions cry.",
        "I look at you and think, “Two billion years of evolution, for this?”",
        "I am jealous of all the people who have never met you.",
        "I consider you my Sun. Now, please get 93 million miles away from here.",
        "If laughter is the best medicine, your face must be curing the world.",
        "You're not simply a drama queen/king. You're the whole royal family.",
        "I was thinking about you today. It reminded me to take out the trash.",
        "You are the human version of cramps.",
        "You haven't changed since the last time I saw you. You really should.",
        "If ignorance is bliss, you must be the happiest person on Earth.",
        "Oh, sorry, did the middle of my sentence interrupt the beginning of yours?",
        "Don't worry, the first 40 years of childhood are always the hardest.",
        "When your mom dropped you off to school, she was arrested for littering."
    ]
    roast = random.choice(roasts)

    await ctx.send(f"<@{user.id}> {roast}")
    print(f"{now()} [{ctx.author.name}] roast: roasted {user.name} (id: {user.id}) \"{roast}\"")

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
        print(f"[ERROR] {now()} [{ctx.author.name}] inventory: invalid page number {page}")
        return False
    
    # retrieve inventory
    if (inv := cache.retrieve(ctx.author.name, "inventory")) is None:
        response = supabase.table("user data").select("*").eq("username", ctx.author.name).execute()
        if response.data:
            inv = response.data[0]["inventory"]
        else:
            supabase.table("user data").insert({"username": ctx.author.name}).execute()
            inv = []
        cache.update(ctx.author.name, "inventory", inv)

    # validate page number
    max_pages = max(int((len(inv)-1)/10+1), 1)
    if page > max_pages:
        await ctx.send("❌ Invalid page number.")
        print(f"[ERROR] {now()} [{ctx.author.name}] inventory: invalid page number {page}")
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
    print(f"{now()} [{ctx.author.name}] inventory: got inventory")

@bot.command()
@command_timeout(0)
async def help(ctx, command_name=None):
    commands = [
        {
            "name": "ping",
            "aliases": [],
            "description": "Ping Nyarth.",
            "usage": "%ping",
            "category": "utility"
        },
        {
            "name": "balance",
            "aliases": ["bal"],
            "description": "Check how many 🪙 you have.",
            "usage": "%balance (user)",
            "category": "money"
        },
        {
            "name": "work",
            "aliases": [],
            "description": "Go to work and earn up to 🪙100. If you do a bad job, you could lose up to 🪙100...",
            "usage": "%work",
            "category": "money"
        },
        {
            "name": "gamble",
            "aliases": [],
            "description": "Gamble your 🪙! You could double your bet, but you could also lose it all...",
            "usage": "%gamble [amount | all]",
            "category": "money"
        },
        {
            "name": "clearcache",
            "aliases": ["clear"],
            "description": "Reset all cooldowns and clear cached data. Only admin can use this command.",
            "usage": "%clearcache",
            "category": "utility"
        },
        {
            "name": "give",
            "aliases": [],
            "description": "Give another user some of your 🪙. Sharing is caring!",
            "usage": "%give [user] [amount | all]",
            "category": "money"
        },
        {
            "name": "leaderboard",
            "aliases": ["lb"],
            "description": "View a list the richest people in the server!",
            "usage": "%leaderboard (page)",
            "category": "utility"
        },
        {
            "name": "roast",
            "aliases": [],
            "description": "Roast your friends!",
            "usage": "%roast (user)",
            "category": "fun"
        },
        {
            "name": "inventory",
            "aliases": ["inv"],
            "description": "View your inventory items.",
            "usage": "%inventory (page)",
            "category": "utility"
        },
        {
            "name": "help",
            "aliases": [],
            "description": "View a list of all commands with descriptions.",
            "usage": "%help (command name)",
            "category": "utility"
        },
        {
            "name": "shop",
            "aliases": [],
            "description": "View a list of available items to buy.",
            "usage": "%shop",
            "category": "shop"
        },
        {
            "name": "buy",
            "aliases": [],
            "description": "Buy an item from the shop.",
            "usage": "%buy (quantity) [item]",
            "category": "shop"
        },
        {
            "name": "sell",
            "aliases": [],
            "description": "Sell items from your inventory.",
            "usage": "%sell (quantity | all) [item]",
            "category": "shop"
        },
        {
            "name": "farm",
            "aliases": [],
            "description": "View your farm. Tile and detailed views are available.",
            "usage": "%farm (tile | details)",
            "category": "farm"
        },
        {
            "name": "plant",
            "aliases": [],
            "description": "Plant 🌱 in your farm.",
            "usage": "%plant (tile)",
            "category": "farm"
        },
        {
            "name": "harvest",
            "aliases": [],
            "description": "Harvest 🌽 or other crops from your farm.",
            "usage": "%harvest (tile)",
            "category": "farm"
        }
    ]
    commands.sort(key=lambda x: x["name"])

    categories = {
        "utility": [],
        "money": [],
        "shop": [],
        "farm": [],
        "fun": []
    }
    for command in commands:
        categories[command["category"]].append(command)

    if command_name is None:
        embed = discord.Embed(color=discord.Color.gold())
        embed.set_author(name="Help Menu", icon_url=bot.user.avatar.url)
        for category, cat_commands in categories.items():
            embed.add_field(name=category.title(), value=", ".join([f"`{i["name"]}`" for i in cat_commands]), inline=False)
        await ctx.send(embed=embed)
        print(f"{now()} [{ctx.author.name}] help: viewed all commands")
    else:
        command = None
        for c in commands:
            if c["name"] == command_name.lower() or command_name.lower() in c["aliases"]:
                command = c
                break
        if command is None:
            await ctx.send("❌ Command not found.")
            print(f"[ERROR] {now()} [{ctx.author.name}] help: couldn't find command {command_name}")
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
        print(f"{now()} [{ctx.author.name}] help: viewed command {command["name"]}")

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
    print(f"{now()} [{ctx.author.name}] shop: viewed the shop")

@bot.command()
@command_timeout(0)
async def buy(ctx, quantity=None, *args):
    if quantity is None and len(args) == 0:
        await ctx.send("❌ No item specified.")
        print(f"[ERROR] {now} [{ctx.author.name}] buy: no item specified")
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
        print(f"[ERROR] {now()} [{ctx.author.name}] buy: item not found ({item_name})")
        return False
    
    # make sure item is sold in the shop
    shop_items = ["seedling", "bucket"]
    if item["name"] not in shop_items:
        await ctx.send("❌ Item can't be bought.")
        print(f"[ERROR] {now()} [{ctx.author.name}] buy: item can't be bought ({item_name})")
        return False
    
    # get user balance
    balance = get_balance(cache, supabase, ctx.author.name)
    
    # check if the user has enough money
    if balance < item["price"]*quantity:
        await ctx.send(f"❌ You don't have enough 🪙 to buy this! You need {item["price"]*quantity-balance} more 🪙!")
        print(f"[ERROR] {now()} [{ctx.author.name}] buy: not enough coins to buy {item_name} (missing {item["price"]*quantity-balance} coins)")
        return False
    
    # confirmation
    await ctx.send(f"<@{ctx.author.id}> Are you sure you want to buy {quantity}x {item["icon"]} {item["name"].title()} for 🪙{item["price"]*quantity}? (y/n)")
    message = await bot.wait_for("message", check=lambda m: (m.content.lower() == "y" or m.content.lower() == "n") and m.channel == ctx.channel)
    if message.content.lower() != "y":
        await ctx.send(f"<@{ctx.author.id}> Purchase cancelled.")
        print(f"{now()} [{ctx.author.name}] buy: cancelled purchase of {quantity} {item["name"]} for {item["price"]*quantity} coins")
        return False
    
    # send message to user before making the slow api calls
    await ctx.send(f"<@{ctx.author.id}> bought {quantity}x {item["icon"]} {item["name"].title()} for 🪙{item["price"]*quantity}!")
    
    # deduct balance
    supabase.table("user data").update({"balance": balance-item["price"]*quantity}).eq("username", ctx.author.name).execute()
    cache.update(ctx.author.name, "balance", balance-item["price"]*quantity)

    # get inventory
    if (inv := cache.retrieve(ctx.author.name, "inventory")) is None:
        response = supabase.table("user data").select("*").eq("username", ctx.author.name).execute()
        if response.data:
            inv = response.data[0]["inventory"]
        else:
            supabase.table("user data").insert({"username": ctx.author.name}).execute()
            inv = []
        cache.update(ctx.author.name, "inventory", inv)
    
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
    print(f"{now()} [{ctx.author.name}] buy: bought {quantity} {item["name"]} for {item["price"]*quantity} coins")

@bot.command()
@command_timeout(0)
async def sell(ctx, quantity=None, *args):
    if quantity is None and len(args) == 0:
        await ctx.send("❌ No item specified.")
        print(f"[ERROR] {now} [{ctx.author.name}] sell: no item specified")
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
    if (inv := cache.retrieve(ctx.author.name, "inventory")) is None:
        response = supabase.table("user data").select("*").eq("username", ctx.author.name).execute()
        if response.data:
            inv = response.data[0]["inventory"]
        else:
            supabase.table("user data").insert({"username": ctx.author.name}).execute()
            inv = []
        cache.update(ctx.author.name, "inventory", inv)

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
        print(f"[ERROR] {now()} [{ctx.author.name}] sell: doesn't have item ({item_name})")
        return False
    
    if quantity == "all":
        quantity = inv[item_index]["count"]

    # make sure there is enough of the item in the inventory
    if inv[item_index]["count"] < quantity:
        await ctx.send("❌ You don't have enough to sell!")
        print(f"[ERROR] {now()} [{ctx.author.name}] sell: doesn't have enough to sell (has {item["count"]} {item_name}, wants to sell {quantity})")
        return False
    
    # get item data
    try:
        item = items[inv[item_index]["name"]]
    except KeyError:
        await ctx.send("❌ This item can't be sold!")
        print(f"[ERROR] {now()} [{ctx.author.name}] sell: can't sell item ({item_name})")
        return False
    
    # confirmation
    await ctx.send(f"<@{ctx.author.id}> Are you sure you want to sell {quantity}x {item["icon"]} {item["name"].title()} for 🪙{item["price"]*quantity}? (y/n)")
    message = await bot.wait_for("message", check=lambda m: (m.content.lower() == "y" or m.content.lower() == "n") and m.channel == ctx.channel)
    if message.content.lower() != "y":
        await ctx.send(f"<@{ctx.author.id}> Sale cancelled.")
        print(f"{now()} [{ctx.author.name}] sell: cancelled sale of {quantity} {item["name"]} for {item["price"]*quantity} coins")
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
    print(f"{now()} [{ctx.author.name}] sell: sold {quantity} {item["name"]} for {item["price"]*quantity} coins")

@bot.command()
@command_timeout(0)
async def farm(ctx, mode=None):
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
    
    # update farm (check if any seedlings have matured or any corn has expired)
    update_needed = False
    time_now = datetime.datetime.now().timestamp()
    for i in range(9):
        if farm_data[i]["contents"] == "dirt":
            continue
        elapsed = time_now - farm_data[i]["time"]
        if farm_data[i]["contents"] == "seedling" and elapsed >= 0 and elapsed < 86400:
            # mature seedling turns into corn
            farm_data[i] = {
                "contents": "corn",
                "icon": "🌽",
                "time": farm_data[i]["time"]+86400
            }
            update_needed = True
        elif (farm_data[i]["contents"] not in ("dirt", "seedling") and elapsed >= 0) or (farm_data[i]["contents"] == "seedling" and elapsed >= 86400):
            # expired corn (or seedling that was supposed to turn into expired corn) turns into dirt
            farm_data[i] = {
                "contents": "dirt",
                "icon": "🟫",
                "time": ""
            }
            update_needed = True
    if update_needed:
        supabase.table("user data").update({"farm": farm_data}).eq("username", ctx.author.name).execute()
        cache.update(ctx.author.name, "farm", farm_data)
    
    # view farm
    if mode is None: # view whole farm
        embed = discord.Embed(
            description="{}{}{}\n{}{}{}\n{}{}{}".format(*[i["icon"] for i in farm_data]),
            color=discord.Color.gold()
        )
        embed.set_author(name=f"{ctx.author.name}'s Farm", icon_url=ctx.author.avatar.url)
        await ctx.send(embed=embed)
        print(f"{now()} [{ctx.author.name}] farm: viewed farm")
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
        print(f"{now()} [{ctx.author.name}] farm: viewed tile {mode}")
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
            print(f"{now()} [{ctx.author.name}] farm: viewed detailed view")
        else: # invalid parameter
            await ctx.send("❌ Invalid parameter.")
            print(f"[ERROR] {now()} [{ctx.author.name}] farm: invalid parameter ({mode})")
            return False

@bot.command()
@command_timeout(0)
async def plant(ctx, tile=None):
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
    
    # update farm (check if any seedlings have matured or any corn has expired)
    update_needed = False
    time_now = datetime.datetime.now().timestamp()
    for i in range(9):
        if farm_data[i]["contents"] == "dirt":
            continue
        elapsed = time_now - farm_data[i]["time"]
        if farm_data[i]["contents"] == "seedling" and elapsed >= 0 and elapsed < 86400:
            # mature seedling turns into corn
            farm_data[i] = {
                "contents": "corn",
                "icon": "🌽",
                "time": farm_data[i]["time"]+86400
            }
            update_needed = True
        elif (farm_data[i]["contents"] not in ("dirt", "seedling") and elapsed >= 0) or (farm_data[i]["contents"] == "seedling" and elapsed >= 86400):
            # expired corn (or seedling that was supposed to turn into expired corn) turns into dirt
            farm_data[i] = {
                "contents": "dirt",
                "icon": "🟫",
                "time": ""
            }
            update_needed = True
    if update_needed:
        supabase.table("user data").update({"farm": farm_data}).eq("username", ctx.author.name).execute()
        cache.update(ctx.author.name, "farm", farm_data)
    
    # validate tile if provided
    if tile is not None:
        try:
            tile = int(tile)
            if tile <= 0 or tile > 9:
                raise Exception
        except:
            await ctx.send("❌ Invalid tile. Please select a tile from 1 - 9.")
            print(f"[ERROR] {now()} [{ctx.author.name}] plant: invalid tile ({tile})")
            return False
    
    # generate list of plantable tiles
    if tile is not None:
        plantable_tiles = [tile] if farm_data[tile-1]["contents"] == "dirt" else []
    else:
        plantable_tiles = [i+1 for i in range(9) if farm_data[i]["contents"] == "dirt"]
    
    if len(plantable_tiles) == 0:
        await ctx.send("❌ You can't plant there.")
        print(f"[ERROR] {now()} [{ctx.author.name}] plant: can't plant")
        return False
    
    # retrieve inventory
    if (inv := cache.retrieve(ctx.author.name, "inventory")) is None:
        response = supabase.table("user data").select("*").eq("username", ctx.author.name).execute()
        if response.data:
            inv = response.data[0]["inventory"]
        else:
            supabase.table("user data").insert({"username": ctx.author.name}).execute()
            inv = []
        cache.update(ctx.author.name, "inventory", inv)
    
    # make sure the user has a seedling to plant
    seedling_index = -1
    for i in range(len(inv)):
        if inv[i]["name"] == "seedling":
            seedling_index = i
            break
    
    if seedling_index == -1:
        await ctx.send("❌ You don't have any seedlings!")
        print(f"{now()} [{ctx.author.name}] farm: doesn't have any seedlings")
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
    print(f"{now()} [{ctx.author.name}] farm: planted seedling")

@bot.command()
@command_timeout(0)
async def harvest(ctx, tile=None):
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
    
    # update farm (check if any seedlings have matured or any corn has expired)
    time_now = datetime.datetime.now().timestamp()
    for i in range(9):
        if farm_data[i]["contents"] == "dirt":
            continue
        elapsed = time_now - farm_data[i]["time"]
        if farm_data[i]["contents"] == "seedling" and elapsed >= 0 and elapsed < 86400:
            # mature seedling turns into corn
            farm_data[i] = {
                "contents": "corn",
                "icon": "🌽",
                "time": farm_data[i]["time"]+86400
            }
        elif (farm_data[i]["contents"] not in ("dirt", "seedling") and elapsed >= 0) or (farm_data[i]["contents"] == "seedling" and elapsed >= 86400):
            # expired corn (or seedling that was supposed to turn into expired corn) turns into dirt
            farm_data[i] = {
                "contents": "dirt",
                "icon": "🟫",
                "time": ""
            }
    
    # validate tile if provided
    if tile is not None:
        try:
            tile = int(tile)
            if tile <= 0 or tile > 9:
                raise Exception
        except:
            await ctx.send("❌ Invalid tile. Please select a tile from 1 - 9.")
            print(f"[ERROR] {now()} [{ctx.author.name}] harvest: invalid tile ({tile})")
            return False
    
    # generate list of tiles to harvest (1-9)
    if tile is not None:
        harvest_tiles = [tile] if farm_data[tile-1]["contents"] == "corn" else []
    else:
        harvest_tiles = [i+1 for i in range(9) if farm_data[i]["contents"] == "corn"]

    # make sure there is corn to harvest
    if len(harvest_tiles) == 0:
        await ctx.send("❌ There is nothing to harvest.")
        print(f"[ERROR] {now()} [{ctx.author.name}] harvest: nothing to harvest")
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
    if (inv := cache.retrieve(ctx.author.name, "inventory")) is None:
        response = supabase.table("user data").select("*").eq("username", ctx.author.name).execute()
        if response.data:
            inv = response.data[0]["inventory"]
        else:
            supabase.table("user data").insert({"username": ctx.author.name}).execute()
            inv = []
        cache.update(ctx.author.name, "inventory", inv)

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

    print(f"{now()} [{ctx.author.name}] farm: harvested {harvested_corn} corn")

@bot.command()
@command_timeout(300)
async def water(ctx, tile=None):
    if tile is None:
        await ctx.send("❌ No tile specified.")
        print(f"[ERROR] {now()} [{ctx.author.name}] water: no tile specified")
        return False
    
    # validate tile
    try:
        tile = int(tile)
        if tile <= 0 or tile > 9:
            raise Exception
    except:
        await ctx.send("❌ Invalid tile. Please select a tile from 1 - 9.")
        print(f"[ERROR] {now()} [{ctx.author.name}] water: invalid tile ({tile})")
        return False
    
    # get inventory
    if (inv := cache.retrieve(ctx.author.name, "inventory")) is None:
        response = supabase.table("user data").select("*").eq("username", ctx.author.name).execute()
        if response.data:
            inv = response.data[0]["inventory"]
        else:
            supabase.table("user data").insert({"username": ctx.author.name}).execute()
            inv = []
        cache.update(ctx.author.name, "inventory", inv)

    # make sure the user has a bucket
    if "bucket" not in [i["name"] for i in inv]:
        await ctx.send("❌ You don't have a bucket to water with!")
        print(f"[ERROR] {now()} [{ctx.author.name}] water: no bucket")
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
        print(f"[ERROR] {now()} [{ctx.author.name}] water: can't water {farm_data[tile-1]["contents"]}")
        return False
    
    # speed up harvest by 5 minutes
    farm_data[tile-1]["time"] -= 300
    await ctx.send(f"<@{ctx.author.id}> watered the 🌱 in Tile {tile}! It will grow a bit faster!")
    print(f"{now()} [{ctx.author.name}] water: watered tile {tile}")

    # update farm
    supabase.table("user data").update({"farm": farm_data}).eq("username", ctx.author.name).execute()
    cache.update(ctx.author.name, "farm", farm_data)

bot.run(TOKEN)