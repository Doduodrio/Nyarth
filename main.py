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
    if cache.retrieve(ctx.author.name, "balance"):
        balance = cache.retrieve(ctx.author.name, "balance")
    else:
        response = supabase.table("user data").select("*").eq("username", ctx.author.name).execute()
        if response.data:
            balance = response.data[0]["balance"]
        else:
            supabase.table("user data").insert({"username": ctx.author.name, "balance": 0}).execute()
            balance = 0
    
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
    if cache.retrieve(ctx.author.name, "balance"):
        balance = cache.retrieve(ctx.author.name, "balance")
    else:
        response = supabase.table("user data").select("*").eq("username", ctx.author.name).execute()
        if response.data:
            balance = response.data[0]["balance"]
        else:
            supabase.table("user data").insert({"username": ctx.author.name, "balance": 0}).execute()
            balance = 0
    
    # get recipient balance
    if cache.retrieve(recipient.name, "balance"):
        recipient_balance = cache.retrieve(recipient.name, "balance")
    else:
        response = supabase.table("user data").select("*").eq("username", recipient.name).execute()
        if response.data:
            recipient_balance = response.data[0]["balance"]
        else:
            supabase.table("user data").insert({"username": recipient.name, "balance": 0}).execute()
            recipient_balance = 0
    
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
            lb_string += f"\n{(page-1)*10+i+1}. 🪙{lb[(page-1)*10+i][1]:<{padding}} {lb[(page-1)*10+i][0]}"
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
        "Don't worry, the first 40 years of childhood are always the hardest."
    ]
    roast = random.choice(roasts)

    await ctx.send(f"<@{user.id}> {roast}")
    print(f"{now()} [{ctx.author.name}] roast: roasted {user.name} (id: {user.id}) \"{roast}\"")

# @bot.command(aliases=["inv"])
# @command_timeout(0)
# async def inventory(ctx, page=None):
#     # validate page number
#     try:
#         if page is None:
#             page = 1
#         else:
#             page = int(page)
#     except:
#         await ctx.send("❌ Invalid page number.")
#         print(f"[ERROR] {now()} [{ctx.author.name}] inventory: invalid page number {page}")
#         return False
    
    

bot.run(TOKEN)