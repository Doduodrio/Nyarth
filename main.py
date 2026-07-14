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
            if await command_timeout_check(ctx, cache.retrieve(ctx.author.name, func.__name__), timeout):
                return

            # run command
            output = await func(ctx, *args, **kwargs)

            # update command timeout
            cache.update(ctx.author.name, func.__name__, datetime.datetime.now())

            return output
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
async def ping(ctx):
    await ctx.send(f"Pong!")
    print(f"{now()} ping: pinged bot")

@bot.command(aliases=["bal"])
async def balance(ctx, username=None):
    if username == None:
        user = ctx.author
    else:
        user = find_member(ctx, username)
        if user is None:
            await ctx.send(f"❌ Member not found.")
            print(f"[ERROR] {now()} [{ctx.author.name}] balance: invalid member {username}")
            return

    if cache.retrieve(user.name, "balance"):
        balance = cache.retrieve(user.name, "balance")
    else:
        response = supabase.table("user data").select("*").eq("username", user.name).execute()
        if response.data:
            balance = response.data[0]["balance"]
        else:
            supabase.table("user data").insert({"username": user.name, "balance": 0}).execute()
            balance = 0
        cache.update(user.name, "balance", balance)
    
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
    response = supabase.table("user data").select("*").eq("username", ctx.author.name).execute()
    if response.data:
        balance = response.data[0]["balance"]
        supabase.table("user data").update({"balance": balance+amount}).eq("username", ctx.author.name).execute()
        cache.update(ctx.author.name, "balance", balance+amount)
    else:
        supabase.table("user data").insert({"username": ctx.author.name, "balance": amount}).execute()
        cache.update(ctx.author.name, "balance", amount)
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
        return
    
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
            return
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

@bot.command(aliases=["clear"])
async def clearcache(ctx):
    if ctx.author.name != "doduodrio":
        await ctx.send("❌ You can't use this command.")
        print(f"[ERROR] {now()} [{ctx.author.name}] clearcache: can't use this command")
    else:
        cache.clear_all()
        await ctx.send(f"<@{ctx.author.id}> Cache cleared!")
        print(f"{now()} [{ctx.author.name}] clearcache: cache cleared")

@bot.command()
async def give(ctx, username=None, amount=None):
    if username is None:
        await ctx.send("❌ Specify a member to give 🪙 to.")
        print(f"[ERROR] {now()} [{ctx.author.name}] give: recipient not specified")
    
    recipient = find_member(ctx, username)
    
    if recipient is None:
        await ctx.send(f"❌ Member not found.")
        print(f"[ERROR] {now()} [{ctx.author.name}] give: invalid member {username}")
        return
    
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
        return

    # cannot give yourself coins
    if ctx.author == recipient:
        await ctx.send(f"❌ You cannot give yourself 🪙")
        print(f"[ERROR] {now()} [{ctx.author.name}] give: cannot give self coins")
        return
    
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
            return
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

bot.run(TOKEN)