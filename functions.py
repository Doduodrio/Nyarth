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
    with open(f'logs/log_{logtime}.txt', 'a', encoding='utf-8') as file:
        print_copy(*args, file=file, **kwargs)

def now():
    # returns current timestamp
    time = datetime.datetime.now()
    date = [time.month, time.day, time.year, time.hour, time.minute, time.second]
    for i in range(len(date)):
        date[i] = str(date[i])
        if len(date[i])==1: date[i] = '0' + date[i]
    return '[{}-{}-{} {}:{}:{}]'.format(*date)

def log(ctx: commands.Context, command_name: str, message: str, error: bool = False):
    print(f"{"[ERROR] " if error else ""}{now()} [{ctx.author.name}] {command_name}: {message}")

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
    
    return time_string or False

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
    if (balance := cache.retrieve(username, "balance")) is None:
        response = supabase.table("user data").select("*").eq("username", username).execute()
        if response.data:
            balance = response.data[0]["balance"]
        else:
            supabase.table("user data").insert({"username": username}).execute()
            balance = 0
        cache.update(username, "balance", balance)
    return balance

def get_inventory(cache, supabase, username):
    if (inv := cache.retrieve(username, "inventory")) is None:
        response = supabase.table("user data").select("*").eq("username", username).execute()
        if response.data:
            inv = response.data[0]["inventory"]
        else:
            supabase.table("user data").insert({"username": username}).execute()
            inv = []
        cache.update(username, "inventory", inv)
    return inv

def get_farm_data(cache, supabase, username):
    if (farm_data := cache.retrieve(username, "farm")) is None:
        response = supabase.table("user data").select("*").eq("username", username).execute()
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
            supabase.table("user data").update({"farm": farm_data}).eq("username", username).execute()
        cache.update(username, "farm", farm_data)
    return farm_data

def update_farm_data(cache, supabase, username, farm_data, update=True):
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
    if update and update_needed:
        supabase.table("user data").update({"farm": farm_data}).eq("username", username).execute()
        cache.update(username, "farm", farm_data)
    return farm_data