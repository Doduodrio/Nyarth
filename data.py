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

commands_list = [
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
commands_list.sort(key=lambda x: x["name"])

categories = {
    "utility": [],
    "money": [],
    "shop": [],
    "farm": [],
    "fun": []
}
for command in commands_list:
    categories[command["category"]].append(command)