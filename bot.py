import asyncio
import time
import uuid
import html
import random

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, ReplyParameters
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ChatType
from system import router as system_router

from config import (
    BOT_TOKEN, MODES, DIFFICULTIES, GUESS_COOLDOWN,
    INTRO_EMOJIS, INTRO_STICKER, INTRO_IMAGE_URL, INTRO_LINES, INTRO_DELAY,
)
from database import (
    init_db, close_db, get_user, update_user, create_game,
    get_active_game, get_owned_game, update_game,
    get_user_games, get_leaderboard, transfer_coins, db, get_db,
)
from game import generate_target, evaluate, validate_guess, calculate_rewards
from ui import (
    build_game_message, build_win_message, build_loss_message,
    build_guess_feedback_message,
    build_inventory_rich, build_balance_rich,
    build_pay_confirm_rich, build_pay_result_rich,
    terminal_table, profile_table, leaderboard_table,
    mode_select_rich, difficulty_rich, preview_rich, get_rank,
    _quote, _table,
)
from aiogram.types.input_rich_message import InputRichMessage

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()

cooldowns: dict[tuple[int, int], float] = {}
_bg_tasks: set[asyncio.Task] = set()
_start_tasks: dict[int, asyncio.Task] = {}


def spawn_bg(coro) -> asyncio.Task:
    task = asyncio.create_task(coro)
    _bg_tasks.add(task)

    def _done(t: asyncio.Task):
        _bg_tasks.discard(t)
        if t.cancelled():
            return
        try:
            t.result()
        except Exception as e:
            print(f"[bg task] {e}")

    task.add_done_callback(_done)
    return task


# ── Rich Message Helpers ─────────────────

async def send_rich(chat_id: int, rich_message: InputRichMessage, reply_to: int | None = None):
    """Send a native Rich message. Falls back to plain text ONLY if rich send totally fails."""
    kwargs = {"chat_id": chat_id, "rich_message": rich_message}
    if reply_to:
        kwargs["reply_parameters"] = ReplyParameters(message_id=reply_to)
    try:
        return await bot.send_rich_message(**kwargs)
    except Exception as e:
        print(f"[send_rich] failed: {e!r}")
        text = _blocks_to_text(rich_message)
        kwargs = {"chat_id": chat_id, "text": text or "(no content)"}
        if reply_to:
            kwargs["reply_parameters"] = ReplyParameters(message_id=reply_to)
        return await bot.send_message(**kwargs)


async def edit_rich(chat_id: int, message_id: int, rich_message: InputRichMessage):
    """Edit with rich content. Benign errors are silently skipped."""
    try:
        return await bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            rich_message=rich_message,
        )
    except Exception as e:
        msg = str(e)
        # Benign — ignore these
        if "not modified" in msg or "canceled by new edit" in msg:
            print(f"[edit_rich] benign skip: {msg}")
            return None
        print(f"[edit_rich] failed: {e!r}")
        # Fallback: send fresh rich message
        try:
            return await send_rich(chat_id, rich_message)
        except Exception as e2:
            print(f"[edit_rich] send fallback failed: {e2!r}")
            return None


def _blocks_to_text(rich: InputRichMessage) -> str:
    if not rich.blocks:
        return ""
    lines = []
    for b in rich.blocks:
        if hasattr(b, "text"):
            lines.append(str(b.text))
        elif hasattr(b, "blocks"):
            for inner in b.blocks:
                if hasattr(inner, "text"):
                    lines.append(str(inner.text))
        elif hasattr(b, "cells"):
            for row in b.cells:
                lines.append(" | ".join(c.text or "" for c in row))
    return "\n".join(lines)


# ── Intro + Final UI ─────────────────────

async def _safe_delete_message(chat_id: int, message_id: int):
    try:
        await bot.delete_message(chat_id, message_id)
    except Exception:
        pass


async def send_final_start_ui(msg: Message):
    user = await get_user(
        msg.from_user.id,
        username=msg.from_user.username or "",
        first_name=msg.from_user.first_name or "",
    )
    rich = terminal_table(user, photo_url=INTRO_IMAGE_URL)
    await send_rich(msg.chat.id, rich, reply_to=msg.message_id)


async def run_dm_start_flow(chat_id: int, msg: Message):
    try:
        try:
            emoji = random.choice(INTRO_EMOJIS)
            m = await bot.send_message(chat_id, emoji)
            await asyncio.sleep(1.0)
            await _safe_delete_message(chat_id, m.message_id)
        except Exception as e:
            print(f"[intro emoji] {e}")

        try:
            m = await bot.send_sticker(chat_id, INTRO_STICKER)
            await asyncio.sleep(1.0)
            await _safe_delete_message(chat_id, m.message_id)
        except Exception as e:
            print(f"[intro sticker] {e}")

        for line in INTRO_LINES[:3]:
            try:
                await bot.send_chat_action(chat_id, "typing")
                m = await bot.send_message(chat_id, f"<i>{line}</i>")
                await asyncio.sleep(0.6)
                await _safe_delete_message(chat_id, m.message_id)
            except Exception as e:
                print(f"[intro line] {e}")

        await send_final_start_ui(msg)

    except asyncio.CancelledError:
        raise
    except Exception as e:
        print(f"[intro fatal] {e}")


def schedule_dm_start_flow(msg: Message):
    chat_id = msg.chat.id
    old = _start_tasks.get(chat_id)
    if old and not old.done():
        old.cancel()
    task = spawn_bg(run_dm_start_flow(chat_id, msg))
    _start_tasks[chat_id] = task
    task.add_done_callback(lambda _t: _start_tasks.pop(chat_id, None))


# ── Guess Detection ──────────────────────

def looks_like_guess(text: str, game: dict) -> bool:
    text = text.strip().upper()
    if len(text) != game["length"]:
        return False
    mode = game["mode"]
    if mode == "number":
        return text.isdigit()
    if mode == "word":
        return text.isalpha()
    if mode == "mixed":
        return text.isalnum()
    return False


# ── /start ────────────────────────────────

@dp.message(Command("start"))
async def cmd_start(msg: Message):
    if msg.chat.type == ChatType.PRIVATE:
        schedule_dm_start_flow(msg)
    else:
        await send_final_start_ui(msg)


@dp.message(Command("hack"))
async def cmd_hack(msg: Message):
    await get_user(
        msg.from_user.id,
        username=msg.from_user.username or "",
        first_name=msg.from_user.first_name or "",
    )
    rich = mode_select_rich()
    await send_rich(msg.chat.id, rich, reply_to=msg.message_id)


@dp.message(Command("profile"))
async def cmd_profile(msg: Message):
    user = await get_user(
        msg.from_user.id,
        username=msg.from_user.username or "",
        first_name=msg.from_user.first_name or "",
    )
    rich = profile_table(user)
    await send_rich(msg.chat.id, rich, reply_to=msg.message_id)


@dp.message(Command("leaderboard"))
async def cmd_leaderboard(msg: Message):
    users = await get_leaderboard("level", 10)
    rich = leaderboard_table(users)
    await send_rich(msg.chat.id, rich, reply_to=msg.message_id)


# ── /bal ─────────────────────────────────

@dp.message(Command("bal"))
async def cmd_bal(msg: Message):
    user = await get_user(
        msg.from_user.id,
        username=msg.from_user.username or "",
        first_name=msg.from_user.first_name or "",
    )
    rich = build_balance_rich(user)
    await send_rich(msg.chat.id, rich, reply_to=msg.message_id)


# ── /pay ─────────────────────────────────

@dp.message(Command("pay"))
async def cmd_pay(msg: Message):
    """
    Send coins.
      /pay <amount>              (reply to a message)
      /pay <user_id> <amount>    (direct)
    """
    sender = await get_user(
        msg.from_user.id,
        username=msg.from_user.username or "",
        first_name=msg.from_user.first_name or "",
    )

    parts = (msg.text or "").split()

    receiver_id = None
    amount = None

    # Priority 1: reply to a user
    if msg.reply_to_message and msg.reply_to_message.from_user:
        ru = msg.reply_to_message.from_user

        if ru.is_bot:
            await msg.reply("🚫 You cannot pay a bot.")
            return

        if ru.id != msg.from_user.id:
            await get_user(
                ru.id,
                username=ru.username or "",
                first_name=ru.first_name or "",
            )

        receiver_id = ru.id

        if len(parts) >= 2:
            try:
                amount = int(parts[1])
            except ValueError:
                pass

    # Priority 2: /pay <user_id> <amount>
    elif len(parts) >= 3:
        try:
            receiver_id = int(parts[1])
            amount = int(parts[2])
        except ValueError:
            pass

    if receiver_id is None or amount is None:
        help_rich = InputRichMessage(blocks=[
            _quote("💸 HOW TO SEND COINS"),
            _table([
                ["Method", "Example"],
                ["By Reply", "Reply to their message → /pay 100"],
                ["By ID", "/pay 123456789 100"],
            ]),
        ])
        await send_rich(msg.chat.id, help_rich, reply_to=msg.message_id)
        return

    if receiver_id == msg.from_user.id:
        await msg.reply("🚫 You cannot pay yourself.")
        return

    if amount <= 0:
        await msg.reply("🚫 Amount must be positive.")
        return

    sender_balance = sender.get("coins", 0)
    if sender_balance < amount:
        await msg.reply(
            f"🚫 Insufficient balance.\n"
            f"You have: <b>{sender_balance:,}</b> coins"
        )
        return

    # Safe DB access
    db_conn = get_db()
    receiver = await db_conn.users.find_one({"user_id": receiver_id})
    if not receiver:
        await msg.reply("🚫 Receiver not found in database.")
        return

    receiver_name = receiver.get("username") or receiver.get("first_name") or "Anonymous Hacker"
    if receiver.get("username"):
        receiver_name = f"@{receiver['username']}"

    rich = build_pay_confirm_rich(
        receiver_id=receiver_id,
        receiver_name=receiver_name,
        amount=amount,
        sender_balance=sender_balance,
    )
    await send_rich(msg.chat.id, rich, reply_to=msg.message_id)


# ── Callbacks ────────────────────────────

@dp.callback_query(F.data == "terminal")
async def cb_terminal(cb: CallbackQuery):
    await cb.answer()
    user = await get_user(
        cb.from_user.id,
        username=cb.from_user.username or "",
        first_name=cb.from_user.first_name or "",
    )
    rich = terminal_table(user)
    await edit_rich(cb.message.chat.id, cb.message.message_id, rich)


@dp.callback_query(F.data == "profile")
async def cb_profile(cb: CallbackQuery):
    await cb.answer()
    user = await get_user(
        cb.from_user.id,
        username=cb.from_user.username or "",
        first_name=cb.from_user.first_name or "",
    )
    rich = profile_table(user)
    await edit_rich(cb.message.chat.id, cb.message.message_id, rich)


@dp.callback_query(F.data == "stats")
async def cb_stats(cb: CallbackQuery):
    await cb.answer()
    user = await get_user(
        cb.from_user.id,
        username=cb.from_user.username or "",
        first_name=cb.from_user.first_name or "",
    )
    rich = profile_table(user)
    await edit_rich(cb.message.chat.id, cb.message.message_id, rich)


@dp.callback_query(F.data == "start_hack")
async def cb_start_hack(cb: CallbackQuery):
    await cb.answer()
    rich = mode_select_rich()
    await edit_rich(cb.message.chat.id, cb.message.message_id, rich)


@dp.callback_query(F.data.startswith("mode:"))
async def cb_mode(cb: CallbackQuery):
    await cb.answer()
    mode = cb.data.split(":")[1]
    rich = difficulty_rich(mode)
    await edit_rich(cb.message.chat.id, cb.message.message_id, rich)


@dp.callback_query(F.data.startswith("diff:"))
async def cb_diff(cb: CallbackQuery):
    await cb.answer()
    _, mode, diff = cb.data.split(":")
    cfg = DIFFICULTIES[diff]
    rich = preview_rich(mode, diff, cfg)
    await edit_rich(cb.message.chat.id, cb.message.message_id, rich)


@dp.callback_query(F.data.startswith("play:"))
async def cb_play(cb: CallbackQuery):
    await cb.answer("Breach initiated.")
    _, mode, diff = cb.data.split(":")
    cfg = DIFFICULTIES[diff]

    await get_user(
        cb.from_user.id,
        username=cb.from_user.username or "",
        first_name=cb.from_user.first_name or "",
    )

    existing = await get_active_game(cb.message.chat.id, cb.from_user.id)
    if existing:
        await update_game(existing["game_id"], {"status": "CANCELLED", "completed_at": time.time()})

    target = generate_target(mode, cfg["length"])
    game_id = uuid.uuid4().hex[:8]

    doc = {
        "game_id": game_id,
        "user_id": cb.from_user.id,
        "chat_id": cb.message.chat.id,
        "mode": mode,
        "difficulty": diff,
        "target": target,
        "length": cfg["length"],
        "max_attempts": cfg["attempts"],
        "attempts_used": 0,
        "started_at": time.time(),
        "max_time": cfg["time"],
        "status": "ACTIVE",
        "history": [],
        "panel_message_id": cb.message.message_id,
    }
    await create_game(doc)

    rich = build_game_message(doc)
    await edit_rich(cb.message.chat.id, cb.message.message_id, rich)


@dp.callback_query(F.data.startswith("abort:"))
async def cb_abort(cb: CallbackQuery):
    game_id = cb.data.split(":", 1)[1]

    game = await get_owned_game(game_id, cb.from_user.id)
    if not game:
        await cb.answer("🚫 This is not your mission.", show_alert=True)
        return
    if game.get("status") != "ACTIVE":
        await cb.answer("⚠️ This mission is no longer active.", show_alert=True)
        return

    await cb.answer()

    from aiogram.types.input_rich_block_buttons import InputRichBlockButtons
    from aiogram.types.rich_message_button import RichMessageButton
    from aiogram.types.input_rich_block_block_quotation import InputRichBlockBlockQuotation
    from aiogram.types.input_rich_block_paragraph import InputRichBlockParagraph

    rich = InputRichMessage(blocks=[
        InputRichBlockBlockQuotation(blocks=[
            InputRichBlockParagraph(text="⚠️ ABORT MISSION?\n\nAll progress will be lost.")
        ]),
        InputRichBlockButtons(buttons=[
            RichMessageButton(text="☠️ CONFIRM ABORT", callback_data=f"confirm_abort:{game_id}", style="danger"),
        ]),
        InputRichBlockButtons(buttons=[
            RichMessageButton(text="🔙 CONTINUE", callback_data="terminal", style="primary"),
        ]),
    ])
    await edit_rich(cb.message.chat.id, cb.message.message_id, rich)


@dp.callback_query(F.data.startswith("confirm_abort:"))
async def cb_confirm_abort(cb: CallbackQuery):
    game_id = cb.data.split(":", 1)[1]

    game = await get_owned_game(game_id, cb.from_user.id)
    if not game:
        await cb.answer("🚫 This is not your mission.", show_alert=True)
        return
    if game.get("status") != "ACTIVE":
        await cb.answer("⚠️ This mission is no longer active.", show_alert=True)
        return

    await update_game(game_id, {"status": "CANCELLED", "completed_at": time.time()})
    await cb.answer()

    from aiogram.types.input_rich_block_block_quotation import InputRichBlockBlockQuotation
    from aiogram.types.input_rich_block_paragraph import InputRichBlockParagraph
    rich = InputRichMessage(blocks=[
        InputRichBlockBlockQuotation(blocks=[
            InputRichBlockParagraph(text="☠️ Mission aborted. No reward.")
        ]),
    ])
    await edit_rich(cb.message.chat.id, cb.message.message_id, rich)


@dp.callback_query(F.data.startswith("ability:"))
async def cb_ability(cb: CallbackQuery):
    _, ability, game_id = cb.data.split(":", 2)

    game = await get_owned_game(game_id, cb.from_user.id)
    if not game:
        await cb.answer("🚫 This is not your mission.", show_alert=True)
        return
    if game.get("status") != "ACTIVE":
        await cb.answer("⚠️ Mission is no longer active.", show_alert=True)
        return

    ability_names = {
        "scan": "SCAN", "trace": "TRACE",
        "decrypt": "DECRYPT", "overclock": "OVERCLOCK",
    }
    await cb.answer(f"{ability_names.get(ability, ability)} ready.", show_alert=False)


# ── Guess Handler ────────────────────────

@dp.message(F.text, ~F.text.startswith("/"))
async def handle_guess(msg: Message):
    game = await get_active_game(msg.chat.id, msg.from_user.id)
    if not game:
        return

    guess = msg.text.strip().upper()
    if not looks_like_guess(guess, game):
        return

    key = (msg.chat.id, msg.from_user.id)
    now = time.time()
    if now - cooldowns.get(key, 0) < GUESS_COOLDOWN:
        await msg.reply("⚡ <b>THROTTLED</b>\n\nSlow down, hacker.")
        return
    cooldowns[key] = now

    await get_user(
        msg.from_user.id,
        username=msg.from_user.username or "",
        first_name=msg.from_user.first_name or "",
    )

    game_id = game["game_id"]
    target = game["target"]
    mode = game["mode"]

    err = validate_guess(guess, mode, game["length"])
    if err:
        await msg.reply(f"⚠️ <b>INVALID SEQUENCE</b>\n\n{err}\n\n<b>Attempt NOT consumed.</b>")
        return

    pattern = evaluate(guess, target)
    attempts = game["attempts_used"] + 1
    history = game.get("history", [])
    history.append({"guess": guess, "pattern": pattern})

    max_attempts = game["max_attempts"]
    remaining = max(0, max_attempts - attempts)

    # ── WIN ──
    if guess == target:
        duration = time.time() - game["started_at"]
        user = await get_user(msg.from_user.id)
        rewards = calculate_rewards(game["difficulty"], user.get("streak", 0), duration, game["max_time"])

        new_xp = user.get("xp", 0) + rewards["xp"]
        new_level = new_xp // 100 + 1
        new_streak = user.get("streak", 0) + 1
        best_streak = max(user.get("best_streak", 0), new_streak)
        prev_bt = user.get("best_time")
        best_time = duration if prev_bt is None else min(prev_bt, duration)

        await update_game(game_id, {
            "status": "WON", "attempts_used": attempts, "history": history,
            "completed_at": time.time(), "duration": duration,
            "reward": rewards["total"], "xp": rewards["xp"],
        })
        await update_user(msg.from_user.id, {
            "coins": user.get("coins", 100) + rewards["total"],
            "xp": new_xp, "level": new_level,
            "wins": user.get("wins", 0) + 1, "streak": new_streak,
            "best_streak": best_streak, "best_time": best_time,
        })

        feedback = build_guess_feedback_message(game, guess, pattern, attempts, remaining)
        await send_rich(msg.chat.id, feedback)

        game["attempts_used"] = attempts
        game["history"] = history
        win_rich = build_win_message(game, rewards, duration)
        await send_rich(msg.chat.id, win_rich)
        return

    # ── LOSS ──
    if attempts >= max_attempts:
        await update_game(game_id, {
            "status": "LOST", "attempts_used": attempts,
            "history": history, "completed_at": time.time(),
        })
        user = await get_user(msg.from_user.id)
        await update_user(msg.from_user.id, {
            "losses": user.get("losses", 0) + 1, "streak": 0,
        })
        game["attempts_used"] = attempts
        game["history"] = history

        feedback = build_guess_feedback_message(game, guess, pattern, attempts, remaining)
        await send_rich(msg.chat.id, feedback)

        loss_rich = build_loss_message(game)
        await send_rich(msg.chat.id, loss_rich)
        return

    # ── CONTINUE ──
    await update_game(game_id, {"attempts_used": attempts, "history": history})
    game["attempts_used"] = attempts
    game["history"] = history

    feedback = build_guess_feedback_message(game, guess, pattern, attempts, remaining)
    await send_rich(msg.chat.id, feedback)

    game_rich = build_game_message(game)
    panel_id = game.get("panel_message_id")
    if panel_id:
        await edit_rich(msg.chat.id, panel_id, game_rich)
    else:
        await send_rich(msg.chat.id, game_rich)


# ── Leaderboard ──────────────────────────

@dp.callback_query(F.data.startswith("leaderboard:"))
async def cb_leaderboard(cb: CallbackQuery):
    await cb.answer()
    parts = cb.data.split(":")
    tab = parts[1] if len(parts) > 1 else "level"
    page = int(parts[2]) if len(parts) > 2 else 0
    field_map = {
        "level": "level", "xp": "xp", "solved": "wins",
        "streak": "streak", "speed": "best_time", "credits": "coins",
    }
    sort_field = field_map.get(tab, "level")

    if sort_field == "best_time":
        users = await db.users.find({"best_time": {"$ne": None}}) \
            .sort("best_time", 1).skip(page * 10).limit(10).to_list(10)
    else:
        users = await get_leaderboard(sort_field, 10)

    rich = leaderboard_table(users)
    await edit_rich(cb.message.chat.id, cb.message.message_id, rich)


# ── Inventory / Balance callbacks ────────

@dp.callback_query(F.data == "inventory")
async def cb_inventory(cb: CallbackQuery):
    await cb.answer()
    user = await get_user(
        cb.from_user.id,
        username=cb.from_user.username or "",
        first_name=cb.from_user.first_name or "",
    )
    rich = build_inventory_rich(user)
    await edit_rich(cb.message.chat.id, cb.message.message_id, rich)


@dp.callback_query(F.data == "balance")
async def cb_balance(cb: CallbackQuery):
    await cb.answer()
    user = await get_user(
        cb.from_user.id,
        username=cb.from_user.username or "",
        first_name=cb.from_user.first_name or "",
    )
    rich = build_balance_rich(user)
    await edit_rich(cb.message.chat.id, cb.message.message_id, rich)


# ── Pay confirm callback ─────────────────

@dp.callback_query(F.data.startswith("pay_confirm:"))
async def cb_pay_confirm(cb: CallbackQuery):
    try:
        _, receiver_id_str, amount_str = cb.data.split(":")
        receiver_id = int(receiver_id_str)
        amount = int(amount_str)
    except Exception:
        await cb.answer("⚠️ Invalid payment data.", show_alert=True)
        return

    await cb.answer()  # Answer early to avoid "query too old"

    result = await transfer_coins(cb.from_user.id, receiver_id, amount)

    if not result["ok"]:
        await cb.answer(f"🚫 {result['reason']}", show_alert=True)
        return

    db_conn = get_db()
    receiver = await db_conn.users.find_one({"user_id": receiver_id}) or {}
    receiver_name = receiver.get("username") or receiver.get("first_name") or "Anonymous Hacker"
    if receiver.get("username"):
        receiver_name = f"@{receiver['username']}"

    rich = build_pay_result_rich(
        receiver_id=receiver_id,
        receiver_name=receiver_name,
        amount=amount,
        new_balance=result["from_balance"],
    )
    await edit_rich(cb.message.chat.id, cb.message.message_id, rich)


# ── Lifecycle ────────────────────────────

async def main():
    await init_db()

    # Sanity check
    try:
        from database import db as _db
        if _db is None:
            print("[FATAL] DB is None after init_db()")
            return
        print(f"[bot] DB: {_db.name}")
    except Exception as e:
        print(f"[bot] DB check failed: {e}")
        return

    dp.include_router(system_router)
    print("Bot started — DM & Group ready.")
    try:
        await dp.start_polling(bot)
    finally:
        await close_db()


if __name__ == "__main__":
    asyncio.run(main())