"""
System module — Rich UI commands and navigation.
Commands: /ping /stats /help /restart
"""
import asyncio
import os
import sys
import time
import platform
import subprocess

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery

from database import get_db, get_user
from custom_emojis import button_icon, ce

try:
    from config import OWNER_ID
except ImportError:
    try:
        from config import OWNER_IDS as OWNER_ID
    except ImportError:
        OWNER_ID = None

from aiogram.types.input_rich_message import InputRichMessage
from aiogram.types.input_rich_block_table import InputRichBlockTable
from aiogram.types.input_rich_block_block_quotation import InputRichBlockBlockQuotation
from aiogram.types.input_rich_block_paragraph import InputRichBlockParagraph
from aiogram.types.input_rich_block_buttons import InputRichBlockButtons
from aiogram.types.rich_block_table_cell import RichBlockTableCell
from aiogram.types.rich_message_button import RichMessageButton

router = Router()

START_TIME = time.time()
VERSION = "1.0.0"


# ── Owner helpers ────────────────────────

def _is_owner(user_id: int) -> bool:
    if OWNER_ID is None:
        return False
    try:
        uid = int(user_id)
    except Exception:
        return False
    try:
        if isinstance(OWNER_ID, (list, tuple, set)):
            return any(int(x) == uid for x in OWNER_ID if x is not None)
        return int(OWNER_ID) == uid
    except Exception:
        return False


# ── Table helpers ────────────────────────

def _cell(text: str, align: str = "left", valign: str = "middle") -> RichBlockTableCell:
    return RichBlockTableCell(text=text, align=align, valign=valign)


def _table(rows: list[list[str]]) -> InputRichBlockTable:
    cells = [[_cell(c) for c in row] for row in rows]
    return InputRichBlockTable(cells=cells, is_bordered=True, is_striped=False)


def _quote(text: str) -> InputRichBlockBlockQuotation:
    return InputRichBlockBlockQuotation(blocks=[InputRichBlockParagraph(text=text)])


def _btn(
    text: str,
    callback_data: str,
    style: str = "primary",
    custom_emoji: str | None = None,
) -> RichMessageButton:
    kwargs = {
        "text": text,
        "callback_data": callback_data,
        "style": style,
    }
    if custom_emoji:
        icon_id = button_icon(custom_emoji)
        if icon_id:
            kwargs["icon_custom_emoji_id"] = icon_id
    return RichMessageButton(**kwargs)


def _btn_row(*buttons: RichMessageButton) -> InputRichBlockButtons:
    return InputRichBlockButtons(buttons=list(buttons))


# ── Edit helper ──────────────────────────

async def _edit_rich(cb: CallbackQuery, rich: InputRichMessage):
    try:
        return await cb.bot.edit_message_text(
            chat_id=cb.message.chat.id,
            message_id=cb.message.message_id,
            rich_message=rich,
        )
    except Exception as e:
        print(f"[system:edit_rich] {e}")
        return None


# ── Data collection ──────────────────────

def _fmt_uptime(seconds: float) -> str:
    d = int(seconds // 86400)
    h = int((seconds % 86400) // 3600)
    m = int((seconds % 3600) // 60)
    if d:
        return f"{d}d {h}h"
    if h:
        return f"{h}h {m}m"
    return f"{m}m"


async def _db_ping() -> tuple[bool, float]:
    try:
        t0 = time.perf_counter()
        await get_db().command("ping")
        return True, (time.perf_counter() - t0) * 1000
    except Exception as e:
        print(f"[system:_db_ping] {e}")
        return False, 0.0


async def get_bot_stats() -> dict:
    return {
        "status": "ONLINE",
        "uptime": _fmt_uptime(time.time() - START_TIME),
        "version": VERSION,
        "python": platform.python_version(),
        "aiogram": "3.x",
        "pid": os.getpid(),
    }


async def get_user_stats() -> dict:
    try:
        db = get_db()
        total = await db.users.count_documents({})
        with_uname = await db.users.count_documents({"username": {"$ne": ""}})
        return {
            "total": total,
            "with_username": with_uname,
            "without_username": total - with_uname,
        }
    except Exception as e:
        print(f"[system:get_user_stats] {e}")
        return {"total": "N/A", "with_username": "N/A", "without_username": "N/A"}


async def get_game_stats() -> dict:
    try:
        db = get_db()
        total = await db.games.count_documents({})
        active = await db.games.count_documents({"status": "ACTIVE"})
        won = await db.games.count_documents({"status": "WON"})
        lost = await db.games.count_documents({"status": "LOST"})
        cancelled = await db.games.count_documents({"status": "CANCELLED"})
        return {
            "total": total, "active": active,
            "completed": won + lost,
            "wins": won, "losses": lost,
            "cancelled": cancelled,
        }
    except Exception as e:
        print(f"[system:get_game_stats] {e}")
        return {k: "N/A" for k in ("total", "active", "completed", "wins", "losses", "cancelled")}


async def get_database_stats() -> dict:
    connected, latency = await _db_ping()
    if not connected:
        return {"status": "OFFLINE", "latency": "N/A", "users": "N/A", "games": "N/A", "name": "N/A"}
    try:
        db = get_db()
        users = await db.users.count_documents({})
        games = await db.games.count_documents({})
        return {
            "status": "CONNECTED",
            "latency": f"{latency:.0f} ms",
            "users": users,
            "games": games,
            "name": db.name,
        }
    except Exception as e:
        print(f"[system:get_database_stats] {e}")
        return {"status": "CONNECTED", "latency": f"{latency:.0f} ms", "users": "N/A", "games": "N/A", "name": "N/A"}


async def get_system_stats() -> dict:
    if not HAS_PSUTIL:
        return {k: "N/A" for k in ("cpu", "ram", "ram_total", "disk", "os", "arch")}
    try:
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        return {
            "cpu": f"{psutil.cpu_percent(interval=None)}%",
            "ram": f"{mem.percent}%",
            "ram_total": f"{mem.total / (1024**3):.1f} GB",
            "disk": f"{disk.percent}%",
            "os": platform.system(),
            "arch": platform.machine(),
        }
    except Exception as e:
        print(f"[system:get_system_stats] {e}")
        return {k: "N/A" for k in ("cpu", "ram", "ram_total", "disk", "os", "arch")}


# ── UI builders ──────────────────────────

def build_ping_rich(latency_ms: float, db_ok: bool) -> InputRichMessage:
    return InputRichMessage(blocks=[
        _quote(f"{ce('ping')} PING STATUS"),
        _table([
            ["Metric", "Value"],
            ["Bot", "ONLINE"],
            ["Latency", f"{latency_ms:.0f} ms"],
            ["API", "ONLINE"],
            ["Database", "ONLINE" if db_ok else "OFFLINE"],
            ["Process", "RUNNING"],
        ]),
        _btn_row(
            _btn("REFRESH", "system:ping", "primary", custom_emoji="refresh"),
            _btn("STATS", "system:stats", "primary", custom_emoji="chart"),
        ),
        _btn_row(_btn("HOME", "system:home", "success", custom_emoji="home")),
    ])


def build_stats_rich(bot_s: dict, user_s: dict, game_s: dict) -> InputRichMessage:
    return InputRichMessage(blocks=[
        _quote(f"{ce('chart')} SYSTEM STATISTICS"),
        _table([
            [f"{ce('bot')} BOT", "VALUE"],
            ["Status", bot_s["status"]],
            ["Uptime", bot_s["uptime"]],
            ["Version", bot_s["version"]],
            ["Python", bot_s["python"]],
        ]),
        _table([
            [f"{ce('users')} USERS", "VALUE"],
            ["Total", str(user_s["total"])],
            ["With Username", str(user_s["with_username"])],
            ["Without", str(user_s["without_username"])],
        ]),
        _table([
            [f"{ce('game')} GAMES", "VALUE"],
            ["Total", str(game_s["total"])],
            ["Active", str(game_s["active"])],
            ["Wins", str(game_s["wins"])],
            ["Losses", str(game_s["losses"])],
        ]),
        _btn_row(
            _btn("BOT", "stats:bot", "primary", custom_emoji="bot"),
            _btn("USERS", "stats:users", "primary", custom_emoji="users"),
        ),
        _btn_row(
            _btn("GAMES", "stats:games", "primary", custom_emoji="game"),
            _btn("DB", "stats:database", "primary", custom_emoji="database"),
        ),
        _btn_row(
            _btn("SYSTEM", "stats:system", "primary", custom_emoji="system"),
            _btn("REFRESH", "stats:refresh", "success", custom_emoji="refresh"),
        ),
        _btn_row(_btn("HOME", "system:home", "success", custom_emoji="home")),
    ])


def build_bot_stats_rich(s: dict) -> InputRichMessage:
    return InputRichMessage(blocks=[
        _quote(f"{ce('bot')} BOT STATISTICS"),
        _table([
            ["Metric", "Value"],
            ["Status", s["status"]],
            ["Uptime", s["uptime"]],
            ["Version", s["version"]],
            ["Python", s["python"]],
            ["aiogram", s["aiogram"]],
            ["PID", str(s["pid"])],
        ]),
        _btn_row(
            _btn("BACK", "system:stats", "primary", custom_emoji="back"),
            _btn("REFRESH", "stats:bot", "success", custom_emoji="refresh"),
        ),
        _btn_row(_btn("HOME", "system:home", "success", custom_emoji="home")),
    ])


def build_user_stats_rich(s: dict) -> InputRichMessage:
    return InputRichMessage(blocks=[
        _quote(f"{ce('users')} USER STATISTICS"),
        _table([
            ["Metric", "Value"],
            ["Total Users", str(s["total"])],
            ["With Username", str(s["with_username"])],
            ["Without Username", str(s["without_username"])],
        ]),
        _btn_row(
            _btn("BACK", "system:stats", "primary", custom_emoji="back"),
            _btn("REFRESH", "stats:users", "success", custom_emoji="refresh"),
        ),
        _btn_row(_btn("HOME", "system:home", "success", custom_emoji="home")),
    ])


def build_game_stats_rich(s: dict) -> InputRichMessage:
    return InputRichMessage(blocks=[
        _quote(f"{ce('game')} GAME STATISTICS"),
        _table([
            ["Metric", "Value"],
            ["Total Games", str(s["total"])],
            ["Active Games", str(s["active"])],
            ["Completed", str(s["completed"])],
            ["Wins", str(s["wins"])],
            ["Losses", str(s["losses"])],
            ["Cancelled", str(s["cancelled"])],
        ]),
        _btn_row(
            _btn("BACK", "system:stats", "primary", custom_emoji="back"),
            _btn("REFRESH", "stats:games", "success", custom_emoji="refresh"),
        ),
        _btn_row(_btn("HOME", "system:home", "success", custom_emoji="home")),
    ])


def build_database_stats_rich(s: dict) -> InputRichMessage:
    return InputRichMessage(blocks=[
        _quote(f"{ce('database')} DATABASE STATISTICS"),
        _table([
            ["Metric", "Value"],
            ["Status", s["status"]],
            ["Latency", s["latency"]],
            ["Database", s["name"]],
            ["Users", str(s["users"])],
            ["Games", str(s["games"])],
        ]),
        _btn_row(
            _btn("BACK", "system:stats", "primary", custom_emoji="back"),
            _btn("REFRESH", "stats:database", "success", custom_emoji="refresh"),
        ),
        _btn_row(_btn("HOME", "system:home", "success", custom_emoji="home")),
    ])


def build_system_stats_rich(s: dict) -> InputRichMessage:
    return InputRichMessage(blocks=[
        _quote(f"{ce('system')} SYSTEM STATISTICS"),
        _table([
            ["Metric", "Value"],
            ["CPU", s["cpu"]],
            ["RAM", s["ram"]],
            ["Total RAM", s["ram_total"]],
            ["Disk", s["disk"]],
            ["OS", s["os"]],
            ["Arch", s["arch"]],
        ]),
        _btn_row(
            _btn("BACK", "system:stats", "primary", custom_emoji="back"),
            _btn("REFRESH", "stats:system", "success", custom_emoji="refresh"),
        ),
        _btn_row(_btn("HOME", "system:home", "success", custom_emoji="home")),
    ])


def build_help_rich() -> InputRichMessage:
    return InputRichMessage(blocks=[
        _quote(f"{ce('help')} HELP — HACKER CODE BREAKER"),
        _table([
            ["Category", "Commands"],
            ["Game", "/hack /profile"],
            ["Account", "/start /profile"],
            ["Info", "/ping /stats"],
        ]),
        _btn_row(
            _btn("GAME", "help:game", "primary", custom_emoji="game"),
            _btn("ACCOUNT", "help:account", "primary", custom_emoji="profile"),
        ),
        _btn_row(
            _btn("INFO", "help:info", "primary", custom_emoji="chart"),
            _btn("SYSTEM", "help:system", "danger", custom_emoji="settings"),
        ),
        _btn_row(_btn("HOME", "system:home", "success", custom_emoji="home")),
    ])


def build_help_game_rich() -> InputRichMessage:
    return InputRichMessage(blocks=[
        _quote(f"{ce('game')} GAME COMMANDS"),
        _table([
            ["Command", "Description"],
            ["/hack", "Start hacking challenge"],
            ["/profile", "View your profile"],
            ["/leaderboard", "View leaderboard"],
        ]),
        _btn_row(
            _btn("BACK", "system:help", "primary", custom_emoji="back"),
            _btn("HOME", "system:home", "success", custom_emoji="home"),
        ),
    ])


def build_help_account_rich() -> InputRichMessage:
    return InputRichMessage(blocks=[
        _quote(f"{ce('profile')} ACCOUNT COMMANDS"),
        _table([
            ["Command", "Description"],
            ["/start", "Open main interface"],
            ["/profile", "View your profile"],
        ]),
        _btn_row(
            _btn("BACK", "system:help", "primary", custom_emoji="back"),
            _btn("HOME", "system:home", "success", custom_emoji="home"),
        ),
    ])


def build_help_info_rich() -> InputRichMessage:
    return InputRichMessage(blocks=[
        _quote(f"{ce('chart')} INFORMATION COMMANDS"),
        _table([
            ["Command", "Description"],
            ["/ping", "Check bot latency"],
            ["/stats", "View bot statistics"],
        ]),
        _btn_row(
            _btn("BACK", "system:help", "primary", custom_emoji="back"),
            _btn("HOME", "system:home", "success", custom_emoji="home"),
        ),
    ])


def build_help_system_rich(user_id: int) -> InputRichMessage:
    if _is_owner(user_id):
        rows = [
            ["Command", "Description"],
            ["/restart", "Restart bot (owner)"],
            ["/stats", "System statistics"],
        ]
    else:
        rows = [
            ["Command", "Description"],
            ["N/A", "No system commands available"],
        ]
    return InputRichMessage(blocks=[
        _quote(f"{ce('settings')} SYSTEM COMMANDS"),
        _table(rows),
        _btn_row(
            _btn("BACK", "system:help", "primary", custom_emoji="back"),
            _btn("HOME", "system:home", "success", custom_emoji="home"),
        ),
    ])


def build_restart_confirm_rich() -> InputRichMessage:
    return InputRichMessage(blocks=[
        _quote(f"{ce('refresh')} SYSTEM RESTART"),
        _table([
            ["Property", "Value"],
            ["Status", "READY"],
            ["Process", "CURRENT"],
            ["Action", "RESTART"],
        ]),
        _btn_row(_btn("CONFIRM", "system:restart:confirm", "danger", custom_emoji="success")),
        _btn_row(_btn("CANCEL", "system:restart:cancel", "primary", custom_emoji="danger")),
    ])


# ── Command handlers ─────────────────────

@router.message(Command("ping"))
async def cmd_ping(msg: Message):
    t0 = time.perf_counter()
    try:
        await msg.bot.get_me()
        latency = (time.perf_counter() - t0) * 1000
    except Exception as e:
        print(f"[system:ping] {e}")
        latency = 0.0
    db_ok, _ = await _db_ping()
    rich = build_ping_rich(latency, db_ok)
    try:
        await msg.bot.send_rich_message(chat_id=msg.chat.id, rich_message=rich)
    except Exception as e:
        print(f"[system:ping send] {e}")
        await msg.answer("🏓 PONG")


@router.message(Command("stats"))
async def cmd_stats(msg: Message):
    bot_s = await get_bot_stats()
    user_s = await get_user_stats()
    game_s = await get_game_stats()
    rich = build_stats_rich(bot_s, user_s, game_s)
    try:
        await msg.bot.send_rich_message(chat_id=msg.chat.id, rich_message=rich)
    except Exception as e:
        print(f"[system:stats send] {e}")
        await msg.answer("📊 Stats temporarily unavailable.")


@router.message(Command("help"))
async def cmd_help(msg: Message):
    rich = build_help_rich()
    try:
        await msg.bot.send_rich_message(chat_id=msg.chat.id, rich_message=rich)
    except Exception as e:
        print(f"[system:help send] {e}")
        await msg.answer("❓ Help temporarily unavailable.")


@router.message(Command("restart"))
async def cmd_restart(msg: Message):
    if not _is_owner(msg.from_user.id):
        await msg.reply("🚫 Access denied.")
        return
    rich = build_restart_confirm_rich()
    try:
        await msg.bot.send_rich_message(chat_id=msg.chat.id, rich_message=rich)
    except Exception as e:
        print(f"[system:restart send] {e}")
        await msg.answer("⚠️ Restart confirmation failed.")


# ── Callback handlers ────────────────────

@router.callback_query(F.data == "system:home")
async def cb_home(cb: CallbackQuery):
    try:
        from ui import terminal_table
        user = await get_user(
            cb.from_user.id,
            username=cb.from_user.username or "",
            first_name=cb.from_user.first_name or "",
        )
        rich = terminal_table(user)
    except Exception as e:
        print(f"[system:home build] {e}")
        rich = InputRichMessage(blocks=[_quote("🏠 HOME")])
    await _edit_rich(cb, rich)
    await cb.answer()


@router.callback_query(F.data == "system:ping")
async def cb_ping(cb: CallbackQuery):
    t0 = time.perf_counter()
    try:
        await cb.bot.get_me()
        latency = (time.perf_counter() - t0) * 1000
    except Exception as e:
        print(f"[system:cb_ping] {e}")
        latency = 0.0
    db_ok, _ = await _db_ping()
    rich = build_ping_rich(latency, db_ok)
    await _edit_rich(cb, rich)
    await cb.answer("Refreshed")


@router.callback_query(F.data == "system:stats")
async def cb_stats(cb: CallbackQuery):
    bot_s = await get_bot_stats()
    user_s = await get_user_stats()
    game_s = await get_game_stats()
    rich = build_stats_rich(bot_s, user_s, game_s)
    await _edit_rich(cb, rich)
    await cb.answer()


@router.callback_query(F.data == "system:help")
async def cb_help_home(cb: CallbackQuery):
    rich = build_help_rich()
    await _edit_rich(cb, rich)
    await cb.answer()


@router.callback_query(F.data.startswith("stats:"))
async def cb_stats_nav(cb: CallbackQuery):
    action = cb.data.split(":", 1)[1]

    if action == "bot":
        rich = build_bot_stats_rich(await get_bot_stats())
    elif action == "users":
        rich = build_user_stats_rich(await get_user_stats())
    elif action == "games":
        rich = build_game_stats_rich(await get_game_stats())
    elif action == "database":
        if not _is_owner(cb.from_user.id):
            await cb.answer("🚫 Access denied.", show_alert=True)
            return
        rich = build_database_stats_rich(await get_database_stats())
    elif action == "system":
        if not _is_owner(cb.from_user.id):
            await cb.answer("🚫 Access denied.", show_alert=True)
            return
        rich = build_system_stats_rich(await get_system_stats())
    elif action == "refresh":
        bot_s = await get_bot_stats()
        user_s = await get_user_stats()
        game_s = await get_game_stats()
        rich = build_stats_rich(bot_s, user_s, game_s)
    else:
        await cb.answer("Unknown action.")
        return

    await _edit_rich(cb, rich)
    await cb.answer()


@router.callback_query(F.data.startswith("help:"))
async def cb_help_nav(cb: CallbackQuery):
    action = cb.data.split(":", 1)[1]
    if action == "game":
        rich = build_help_game_rich()
    elif action == "account":
        rich = build_help_account_rich()
    elif action == "info":
        rich = build_help_info_rich()
    elif action == "system":
        rich = build_help_system_rich(cb.from_user.id)
    else:
        rich = build_help_rich()
    await _edit_rich(cb, rich)
    await cb.answer()


@router.callback_query(F.data == "system:restart:cancel")
async def cb_restart_cancel(cb: CallbackQuery):
    rich = build_help_rich()
    await _edit_rich(cb, rich)
    await cb.answer("Cancelled")


@router.callback_query(F.data == "system:restart:confirm")
async def cb_restart_confirm(cb: CallbackQuery):
    if not _is_owner(cb.from_user.id):
        await cb.answer("🚫 Access denied.", show_alert=True)
        return

    try:
        await cb.bot.edit_message_text(
            chat_id=cb.message.chat.id,
            message_id=cb.message.message_id,
            rich_message=InputRichMessage(blocks=[_quote("🔄 RESTARTING...")]),
        )
    except Exception as e:
        print(f"[system:restart edit] {e}")

    await cb.answer("Restarting...")
    await asyncio.sleep(1.0)

    try:
        if os.name == "nt":
            subprocess.Popen(
                [sys.executable, sys.argv[0]] + sys.argv[1:],
                creationflags=subprocess.CREATE_NEW_CONSOLE,
                close_fds=True,
            )
            sys.exit(0)
        else:
            os.execv(sys.executable, [sys.executable, sys.argv[0]] + sys.argv[1:])
    except Exception as e:
        print(f"[system:restart] failed: {e}")