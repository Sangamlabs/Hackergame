# 🕶️ Hacker Code Breaker

> A cyberpunk-themed Telegram bot where players crack encrypted codes, level up their hacker rank, duel other players, and climb the global leaderboard.

![Python](https://img.shields.io/badge/python-3.12+-blue.svg)
![aiogram](https://img.shields.io/badge/aiogram-3.x-blue.svg)
![MongoDB](https://img.shields.io/badge/MongoDB-Motor-green.svg)
![License](https://img.shields.io/badge/license-MIT-blue.svg)

---

## 📖 Table of Contents

- [About](#-about)
- [Features](#-features)
- [Tech Stack](#-tech-stack)
- [Project Structure](#-project-structure)
- [Game Modes](#-game-modes)
- [Gameplay Flow](#-gameplay-flow)
- [Installation](#-installation)
- [Configuration](#-configuration)
- [Running Locally](#-running-locally)
- [Deployment](#-deployment)
- [Bot Commands](#-bot-commands)
- [Environment Variables](#-environment-variables)
- [Custom Emoji System](#-custom-emoji-system)
- [Contributing](#-contributing)
- [License](#-license)

---

## 🎯 About

**Hacker Code Breaker** is a fully-featured Telegram game bot that combines the mechanics of Wordle with a cyberpunk hacker theme. Players act as hackers attempting to breach encrypted systems by cracking secret codes before their attempts run out.

The bot uses **Telegram's Native Rich Message API** to deliver a modern, interactive experience with:
- Native rich tables for game state
- Colored inline buttons
- Rich blockquotes for narrative
- Full dark-mode optimized cyberpunk UI

---

## ✨ Features

### 🎮 Three Game Modes
- **Word Breaker** — Crack English words
- **Number Breaker** — Crack numeric security codes
- **Mixed Breaker** — Crack alphanumeric sequences

### 🎯 Five Difficulty Levels
| Difficulty | Length | Attempts | Reward | XP |
|------------|--------|----------|--------|-----|
| 🟢 Easy | 4 | 8 | 50 | 50 |
| 🔵 Normal | 5 | 7 | 100 | 75 |
| 🟣 Hard | 6 | 6 | 175 | 125 |
| 🔴 Extreme | 8 | 6 | 300 | 150 |
| ☠️ Nightmare | 10 | 5 | 600 | 300 |

### 🏆 RPG Progression
- **XP & Levels** — Gain XP from every win
- **Ranks** — 7 ranks from Script Kiddie to Ghost in the Shell
- **Streaks** — Daily streak bonuses
- **Credits** — In-game currency for transactions

### 💰 Economy System
- **Balance tracking** — `/bal` command
- **Peer-to-peer payments** — `/pay` command with reply support
- **Inventory** — Ability slots (Scanner, Trace, Decrypt, Overclock, Firewall)
- **Transaction logs** — Full audit trail in MongoDB

### 🎨 User Interface
- **Native Rich Tables** — Telegram's native table rendering
- **Colored Buttons** — Primary / success / danger styles
- **Wordle-style Feedback** — 🟩 🟨 ⬜ for each guess
- **Cinematic `/start`** — Emoji → sticker → typing animation
- **Spoiler images** — Blurred image reveals in terminal
- **Custom Emoji support** — Telegram premium emoji IDs (configurable)

### 🔐 Security
- **Owner-only commands** — `/restart` and system stats
- **Game ownership validation** — Users can't control other players' games
- **Atomic coin transfers** — MongoDB `$inc` with `$gte` guards
- **Rate limiting** — Per-user guess cooldowns
- **HTML escaping** — Prevents injection via usernames

### 🌐 System Module
- `/ping` — Live latency + database ping
- `/stats` — Bot / users / games / database / system stats
- `/help` — Categorized command reference
- `/restart` — Owner-only graceful restart

---

## 🛠 Tech Stack

| Layer | Technology |
|-------|------------|
| Language | Python 3.12+ |
| Bot Framework | [aiogram 3.x](https://docs.aiogram.dev/) |
| Database | MongoDB via [Motor](https://motor.readthedocs.io/) |
| UI | Telegram Native Rich Message API |
| Config | python-dotenv |
| Optional | psutil (system stats) |

---

## 📁 Project Structure
hacker-code-breaker/
├── bot.py # Main entry point, dispatcher, handlers
├── ui.py # Rich message UI builders
├── system.py # /ping /stats /help /restart module
├── game.py # Pure game engine (generation, evaluation)
├── database.py # MongoDB async operations
├── custom_emojis.py # Centralized custom emoji registry
├── config.py # Configuration constants
├── requirements.txt # Python dependencies
├── Dockerfile # Container definition
├── render.yaml # Render Blueprint (optional)
├── .env.example # Environment template
├── .gitignore
├── .dockerignore
└── README.md

text

---

## 🎮 Game Modes

### Word Breaker
Guess the hidden word letter by letter. Dictionary of A-Z.
Target: MATRIX
Guess: MASTER
Result: 🟩 🟨 ⬜ 🟨 🟩 ⬜

text

### Number Breaker
Crack a numeric PIN. Digits 0-9, duplicates supported.
Target: 482931
Guess: 482761
Result: 🟩 🟩 🟩 ⬜ 🟩 🟩

text

### Mixed Breaker
The signature mode — alphanumeric sequences A-Z + 0-9.
Target: A7K92PX
Guess: A7X82PX
Result: 🟩 🟩 🟨 🟩 🟩 🟩

text

---

## 🔄 Gameplay Flow
/start
↓
Hacker Registration (auto)
↓
Cyber Terminal (main menu)
↓
🔐 START HACK
↓
Select Mode
↓
Select Difficulty
↓
Mission Preview
↓
🚀 INITIATE BREACH
↓
Active Game Panel
↓
User Sends Guess → Validation → Evaluate
↓
🟩 🟨 ⬜ Feedback
↓
├── WIN → Rewards / XP / Streak → Mission Summary
└── LOSS → Reveal Target → Retry

text

---

## 🚀 Installation

### Prerequisites

- Python 3.12 or higher
- MongoDB instance (local or Atlas)
- Telegram Bot Token from [@BotFather](https://t.me/BotFather)

### Clone the Repository

```bash
git clone https://github.com/yourusername/hacker-code-breaker.git
cd hacker-code-breaker
Create a Virtual Environment
Linux / macOS:

bash
python -m venv .venv
source .venv/bin/activate
Windows (PowerShell):

powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
Install Dependencies
bash
pip install --upgrade pip
pip install -r requirements.txt
⚙️ Configuration
Create .env
Copy .env.example to .env:

bash
cp .env.example .env
Edit .env with your values:

env
BOT_TOKEN=123456:ABC-DEF...
MONGODB_URI=mongodb+srv://user:pass@cluster.mongodb.net
MONGODB_DB=hacker_bot
OWNER_ID=123456789
Get Your Telegram User ID
Message @userinfobot on Telegram — it returns your numeric ID.

▶️ Running Locally
bash
python bot.py
Expected output:

text
[db] Connected to hacker_bot
[bot] DB: hacker_bot
Bot started — DM & Group ready.
Now open your bot on Telegram and send /start.

☁️ Deployment
Render (Recommended)
Push to GitHub:

bash
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/yourusername/hacker-code-breaker.git
git push -u origin main
Create a Background Worker:

Go to dashboard.render.com

Click New → Background Worker

Connect your repo

Render detects the Dockerfile automatically

Plan: Free

Set Environment Variables:

In the dashboard, add:

BOT_TOKEN

MONGODB_URI

MONGODB_DB

OWNER_ID

Deploy — Render builds the image and starts the bot.

Using render.yaml
If you prefer Infrastructure-as-Code, push the included render.yaml. Render will pick it up automatically:

Dashboard → New → Blueprint

Connect repo

Render creates the Background Worker with env vars prompted

Docker (Self-Hosted)
bash
docker build -t hacker-code-breaker .
docker run -d --name hacker-bot \
  --env-file .env \
  --restart unless-stopped \
  hacker-code-breaker
Why Background Worker?
The bot uses long polling (dp.start_polling()), not webhooks. Background Workers:

Don't require port binding

Don't spin down on idle

Run continuously on the free tier

🤖 Bot Commands
Public Commands
Command	Description
/start	Enter the cyber terminal
/hack	Start a new hacking mission
/profile	View your hacker profile
/leaderboard	Global leaderboard
/bal	Check your credit balance
/pay <user_id> <amount>	Send credits to another user
/ping	Check bot latency
/stats	View bot statistics
/help	Command reference
Owner-Only
Command	Description
/restart	Restart the bot process
Reply-Based Payment
Send credits by replying to a message:

text
Reply to @user's message with: /pay 100
🌍 Environment Variables
Variable	Required	Default	Description
BOT_TOKEN	✅	—	Telegram bot token
MONGODB_URI	✅	mongodb://localhost:27017	MongoDB connection string
MONGODB_DB	❌	hacker_bot	Database name
OWNER_ID	❌	0	Telegram ID of bot owner
🎨 Custom Emoji System
The bot supports Telegram Premium custom emojis via a centralized registry.

Configure
Edit custom_emojis.py:

python
CUSTOM_EMOJIS = {
    "scan": {"id": "5368324170671202286", "fallback": "🔎"},
    "decrypt": {"id": "5465443379917629504", "fallback": "🔓"},
    # ...
}
id — Telegram custom emoji ID (leave empty to use fallback)

fallback — Unicode emoji used when ID is empty

Requirements
Custom emoji button icons require aiogram ≥ 3.31.0

Bot owner account must have Telegram Premium

Emoji IDs must belong to public emoji packs

Fallback Behavior
If custom emoji IDs are missing or invalid, the bot automatically falls back to Unicode emojis — no crashes, no errors.

🤝 Contributing
Contributions are welcome. Please follow these steps:

Fork the repository

Create a feature branch: git checkout -b feature/your-feature

Commit your changes: git commit -m "Add your feature"

Push to the branch: git push origin feature/your-feature

Open a Pull Request

Code Style
Follow PEP 8

Use type hints where practical

Keep functions focused and documented

Do not modify game logic or database schema without discussion

📄 License
This project is licensed under the MIT License — see the LICENSE file for details.

🙏 Acknowledgements
aiogram — Modern Telegram bot framework

Motor — Async MongoDB driver

Telegram Bot API — Rich Message API

📬 Support
Issues: GitHub Issues

Telegram: @your_support_channel

<p align="center"> <b>🕶️ Stay sharp, hacker. The system is always watching.</b> </p> ```