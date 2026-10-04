import os
from dotenv import load_dotenv

load_dotenv()

# ── Telegram ─────────────────────────────
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
OWNER_ID = int(os.getenv("OWNER_ID", 0))
# ── MongoDB ──────────────────────────────
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
MONGODB_DB = os.getenv("MONGODB_DB", "hacker_bot")

# ── Intro assets (for DM /start animation) ─
INTRO_EMOJIS = ["☠️", "🔥", "⚡", "💀", "👀", "😈"]
INTRO_STICKER = "CAACAgUAAyEFAATsSF3GAAIO1mq_xsO-KX7xOYfxmOGkY1eihSVVAALrEgACT5m5V2aoW3AQL7nuOwQ"
INTRO_IMAGE_URL = "https://files.catbox.moe/9fo75m.jpg"
INTRO_LINES = [
    "Initializing secure channel...",
    "Decrypting hacker credentials...",
    "Welcome to the Cyber Network.",
]
INTRO_DELAY = 0.6   # optional — you can keep this, but the code above hardcodes smaller values  # seconds between animation steps

# ── Game Modes ───────────────────────────
MODES = {
    "word":   {"name": "WORD BREAKER",   "charset": "ABCDEFGHIJKLMNOPQRSTUVWXYZ"},
    "number": {"name": "NUMBER BREAKER", "charset": "0123456789"},
    "mixed":  {"name": "MIXED BREAKER",  "charset": "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"},
}

# ── Difficulty ───────────────────────────
DIFFICULTIES = {
    "easy":      {"name": "🟢 EASY",      "length": 4,  "attempts": 8, "reward": 50,  "xp": 50,  "time": 600},
    "normal":    {"name": "🔵 NORMAL",    "length": 5,  "attempts": 7, "reward": 100, "xp": 75,  "time": 600},
    "hard":      {"name": "🟣 HARD",      "length": 6,  "attempts": 6, "reward": 175, "xp": 125, "time": 600},
    "extreme":   {"name": "🔴 EXTREME",   "length": 8,  "attempts": 6, "reward": 300, "xp": 150, "time": 600},
    "nightmare": {"name": "☠️ NIGHTMARE", "length": 10, "attempts": 5, "reward": 600, "xp": 300, "time": 600},
}

# ── XP / Levels ──────────────────────────
XP_PER_LEVEL = 100

# ── Ranks (by level) ─────────────────────
RANKS = [
    (1,  "🟢 Script Kiddie"),
    (5,  "🔵 Code Runner"),
    (10, "🟣 Cyber Agent"),
    (20, "🟠 Exploit Hunter"),
    (35, "🔴 System Cracker"),
    (50, "☠️ Cyber Legend"),
    (75, "👑 Ghost in the Shell"),
]

# ── Rewards ──────────────────────────────
STREAK_BONUS_PER = 0.05
STREAK_BONUS_MAX = 0.50
SPEED_BONUS = 0.25

# ── Abilities ────────────────────────────
ABILITIES = {
    "scan":      {"name": "🔎 SCAN",      "cost": 50,  "icon": "🔎"},
    "trace":     {"name": "🧠 TRACE",     "cost": 100, "icon": "🧠"},
    "decrypt":   {"name": "🔓 DECRYPT",   "cost": 200, "icon": "🔓"},
    "overclock": {"name": "⚡ OVERCLOCK", "cost": 150, "icon": "⚡"},
}

# ── Rate limit ───────────────────────────
GUESS_COOLDOWN = 1.0