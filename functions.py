import datetime
from discord.ext import commands

logging = True
t = datetime.datetime.now()
logtime = '{}-{}-{}_{}.{}.{}'.format(*[t.year, t.month, t.day, t.hour, t.minute, t.second])

# override the default print function!
print_copy = print
def print(*args, **kwargs):
    print_copy(*args, **kwargs)
    if not logging:
        return
    # log_2026-01-01_00.00.00.txt
    with open(f'logs/log_{logtime}.txt', 'a') as file:
        print_copy(*args, file=file, **kwargs)

def now():
    # returns current timestamp
    time = datetime.datetime.now()
    date = [time.month, time.day, time.year, time.hour, time.minute, time.second]
    for i in range(len(date)):
        date[i] = str(date[i])
        if len(date[i])==1: date[i] = '0' + date[i]
    return '[{}-{}-{} {}:{}:{}]'.format(*date)

async def command_timeout_check(ctx: commands.Context, last_used: datetime.datetime, timeout: int):
    # last_used: datetime object
    # timeout  : # of seconds between uses

    if last_used is None:
        return False

    dt = (datetime.datetime.now() - last_used).total_seconds()
    if dt - timeout >= 0:
        return False

    delay = [
        int((timeout-dt) // 3600),      # hours
        int((timeout-dt % 3600) // 60), # minutes
        int((timeout-dt) % 60)          # seconds
    ]
    units = ["hours", "minutes", "seconds"]
    time_string = ", ".join([f"{delay[i]} {units[i]}" for i in range(3) if delay[i] > 0])
    if time_string == "":
        return False

    await ctx.send(f"❌ You can use this command again in `{time_string}`.")
    print(f"{now()} [{ctx.author.name}] work: command timeout ({time_string} left)")

    return True

def find_member(ctx: commands.Context, username: str):
    if username is None:
        return None
    else:
        user = None

        # check mention format
        try:
            id = int(username.lstrip("<@").rstrip(">"))
        except:
            id = 0
        
        # find member in guild list
        members = ctx.guild.members
        for member in members:
            if member.id == id or username.lower() in member.name.lower():
                user = member
                break
            if member.global_name is not None and username.lower() in member.global_name.lower():
                user = member
                break
            if member.display_name is not None and username.lower() in member.display_name.lower():
                user = member
                break
    return user

def get_balance(cache, supabase, username):
    if cache.retrieve(username, "balance"):
        return cache.retrieve(username, "balance")
    else:
        response = supabase.table("user data").select("*").eq("username", username).execute()
        if response.data:
            balance = response.data[0]["balance"]
        else:
            supabase.table("user data").insert({"username": username, "balance": 0}).execute()
            balance = 0
        cache.update(username, "balance", balance)
        return balance