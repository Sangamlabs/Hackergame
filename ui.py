from aiogram.types.input_rich_message import InputRichMessage
from aiogram.types.input_rich_block_table import InputRichBlockTable
from aiogram.types.input_rich_block_block_quotation import InputRichBlockBlockQuotation
from aiogram.types.input_rich_block_paragraph import InputRichBlockParagraph
from aiogram.types.input_rich_block_buttons import InputRichBlockButtons
from aiogram.types.input_rich_block_photo import InputRichBlockPhoto
from aiogram.types.input_media_photo import InputMediaPhoto
from aiogram.types.rich_block_caption import RichBlockCaption
from aiogram.types.rich_block_table_cell import RichBlockTableCell
from aiogram.types.rich_message_button import RichMessageButton
from config import RANKS
import time
from custom_emojis import button_icon, ce

# ── Cell Helpers ─────────────────────────

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
    """
    Build a rich message button.
    If `custom_emoji` is a registry key with a valid ID, the button
    will show a Telegram custom emoji icon. Otherwise, nothing (text only).
    """
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


def display_name(user: dict) -> str:
    username = user.get("username")
    if username:
        return f"@{username}"
    first_name = user.get("first_name")
    if first_name:
        return first_name
    return "Anonymous Hacker"


def format_guess_pattern(pattern: list[str]) -> str:
    """Convert ['🟩', '⬜', '🟨'] → '🟩 ⬜ 🟨'."""
    return " ".join(pattern)


# ── Game Panel Blocks ────────────────────

def build_game_header(mode: str) -> InputRichBlockBlockQuotation:
    names = {
        "word": "🔤 WORD BREAKER",
        "number": "🔢 NUMBER BREAKER",
        "mixed": "🧬 MIXED BREAKER",
    }
    return _quote(names.get(mode, mode.upper()))


def build_game_status_table(game: dict) -> InputRichBlockTable:
    elapsed = time.time() - game["started_at"]
    remain = max(0, game["max_time"] - elapsed)
    mm = int(remain // 60)
    ss = int(remain % 60)
    return _table([
        ["Property", "Value"],
        ["🔢 Length", str(game["length"])],
        ["🎯 Difficulty", game["difficulty"].upper()],
        ["⚡ Attempts", f"{game['attempts_used']} / {game['max_attempts']}"],
        ["⏱️ Time", f"{mm:02d}:{ss:02d}"],
        ["🎯 Status", game["status"]],
    ])


def build_attempt_history(history: list[dict]) -> InputRichBlockTable:
    if not history:
        return _table([["#", "Guess", "Result"]])
    rows = [["#", "Guess", "Result"]]
    for i, h in enumerate(history[-8:], 1):
        rows.append([str(i), h["guess"], format_guess_pattern(h["pattern"])])
    return _table(rows)


def build_game_button_blocks(game_id: str) -> list[InputRichBlockButtons]:
    return [
        _btn_row(
            _btn("🔎 SCAN", f"ability:scan:{game_id}", "primary"),
            _btn("🧠 TRACE", f"ability:trace:{game_id}", "primary"),
        ),
        _btn_row(
            _btn("🔓 DECRYPT", f"ability:decrypt:{game_id}", "success"),
            _btn("⚡ OVERCLOCK", f"ability:overclock:{game_id}", "success"),
        ),
        _btn_row(_btn("❌ ABORT", f"abort:{game_id}", "danger")),
    ]


# ── Full Game Message ────────────────────

def build_game_message(game: dict) -> InputRichMessage:
    blocks = [
        build_game_header(game["mode"]),
        build_game_status_table(game),
    ]
    if game.get("history"):
        blocks.append(build_attempt_history(game["history"]))
        last = game["history"][-1]
        pattern_str = format_guess_pattern(last["pattern"])
        blocks.append(_quote(f"{last['guess']}\n\n{pattern_str}"))
    remaining = game["max_attempts"] - game["attempts_used"]
    blocks.append(InputRichBlockParagraph(
        text=f"Attempts remaining: {remaining}\n\nSend your next code."
    ))
    blocks.extend(build_game_button_blocks(game["game_id"]))
    return InputRichMessage(blocks=blocks)


def build_guess_feedback_message(
    game: dict,
    guess: str,
    pattern: list[str],
    attempt_number: int,
    remaining: int,
) -> InputRichMessage:
    """Wordle-style feedback Rich message for ONE valid guess."""
    pattern_str = format_guess_pattern(pattern)
    used = attempt_number
    max_attempts = game.get("max_attempts", 0)
    return InputRichMessage(blocks=[
        _quote("🎯 CODE ANALYSIS"),
        _table([
            ["Property", "Value"],
            ["Attempt", f"{used} / {max_attempts}"],
            ["Your Code", guess],
            ["Feedback", pattern_str],
            ["Used", str(used)],
            ["Remaining", str(remaining)],
        ]),
        _quote("🔍 SCAN COMPLETE\nSequence analyzed successfully."),
    ])


def build_win_message(game: dict, rewards: dict, duration: float) -> InputRichMessage:
    return InputRichMessage(blocks=[
        _quote("🔓 SYSTEM BREACHED"),
        _table([
            ["Mission Result", "Value"],
            ["🎮 Mode", game["mode"].upper()],
            ["🎯 Difficulty", game["difficulty"].upper()],
            ["🔑 Code", game["target"]],
            ["⚡ Attempts", f"{game['attempts_used']} / {game['max_attempts']}"],
            ["⏱️ Time", f"{duration:.1f}s"],
            ["💰 Reward", f"+{rewards['total']}"],
            ["⭐ XP", f"+{rewards['xp']}"],
        ]),
        _quote("🗡️𓆩꯭𝙰꯭꯭𝙲꯭꯭𝙲꯭꯭𝙴꯭꯭𝚂꯭꯭𝚂꯭꯭ ꯭꯭𝙶꯭꯭𝚁꯭꯭𝙰꯭꯭𝙽꯭꯭𝚃꯭꯭𝙴꯭꯭𝙳꯭꯭꯭𓆪🗡️ ⇾\n\nSecurity system breached."),
        _btn_row(_btn("🔁 PLAY AGAIN", f"play:{game['mode']}:{game['difficulty']}", "success")),
        _btn_row(
            _btn("👤 PROFILE", "profile", "primary"),
            _btn("🏆 LEADERBOARD", "leaderboard:level:0", "primary"),
        ),
    ])


def build_loss_message(game: dict) -> InputRichMessage:
    return InputRichMessage(blocks=[
        _quote("☠️ SYSTEM LOCKED"),
        _table([
            ["Mission Result", "Value"],
            ["🎮 Mode", game["mode"].upper()],
            ["🎯 Difficulty", game["difficulty"].upper()],
            ["🔑 Code", game["target"]],
            ["⚡ Attempts", f"{game['attempts_used']} / {game['max_attempts']}"],
            ["💰 Reward", "0"],
            ["⭐ XP", "0"],
        ]),
        _quote(" 𝐀⃨ᴄᴄ𝛆꯭᪳ss ᴅ𝛆꯭᪳ηᛧ𝛆꯭᪳ᴅ 𓂃𑪏〪♡\n\nThe encryption key was revealed above."),
        _btn_row(_btn("🔁 TRY AGAIN", f"play:{game['mode']}:{game['difficulty']}", "primary")),
        _btn_row(_btn("🏠 TERMINAL", "terminal", "primary")),
    ])


# ── Terminal / Profile / Leaderboard ─────

def terminal_table(user: dict, photo_url: str = "", photo_caption: str = "") -> InputRichMessage:
    blocks = []
    if photo_url:
        blocks.append(InputRichBlockPhoto(
            photo=InputMediaPhoto(media=photo_url),
            has_spoiler=True,
        ))
    blocks.extend([
        _quote("☠️ CYBER TERMINAL"),
        _table([
            ["Property", "Value"],
            ["🟢 Status", "ONLINE"],
            ["👤 Hacker", display_name(user)],
            ["🎖️ Rank", get_rank(user.get("level", 1))],
            ["⭐ Level", str(user.get("level", 1))],
            ["💰 Credits", f"{user.get('coins', 100):,}"],
            ["🔥 Streak", str(user.get("streak", 0))],
        ]),
        _btn_row(_btn("🔐 START HACK", "start_hack", "success")),
        _btn_row(
            _btn("🔢 NUMBER", "mode:number", "primary"),
            _btn("🔤 WORD", "mode:word", "primary"),
        ),
        _btn_row(_btn("🧬 MIXED CODE", "mode:mixed", "primary")),
        _btn_row(
            _btn("👤 PROFILE", "profile", "primary"),
            _btn("🏆 LEADERBOARD", "leaderboard:level:0", "primary"),
        ),
    ])
    return InputRichMessage(blocks=blocks)


def profile_table(user: dict) -> InputRichMessage:
    wins = user.get("wins", 0)
    losses = user.get("losses", 0)
    total = wins + losses
    wr = (wins / total * 100) if total else 0
    bt = user.get("best_time")
    bt_str = f"{bt:.2f}s" if bt else "—"
    return InputRichMessage(blocks=[
        _quote("👤 HACKER PROFILE"),
        _table([
            ["Property", "Value"],
            ["🕶️ Hacker", display_name(user)],
            ["🎖️ Rank", get_rank(user.get("level", 1))],
            ["⭐ Level", str(user.get("level", 1))],
            ["💰 Credits", f"{user.get('coins', 100):,}"],
            ["🔥 Streak", str(user.get("streak", 0))],
            ["🏆 Best Streak", str(user.get("best_streak", 0))],
            ["🔓 Solved", str(wins)],
            ["☠️ Failed", str(losses)],
            ["📊 Win Rate", f"{wr:.1f}%"],
            ["⚡ Best Time", bt_str],
        ]),
        _btn_row(
            _btn("🎒 INVENTORY", "inventory", "primary"),
            _btn("📊 STATS", "stats", "primary"),
        ),
        _btn_row(_btn("🔙 BACK", "terminal", "primary")),
    ])


def leaderboard_table(users: list[dict]) -> InputRichMessage:
    rows = [["#", "Hacker", "Level", "XP"]]
    for i, u in enumerate(users, 1):
        rows.append([
            str(i),
            display_name(u),
            str(u.get("level", 1)),
            f"{u.get('xp', 0):,}",
        ])
    return InputRichMessage(blocks=[
        _table(rows),
        _btn_row(_btn("🔙 BACK", "terminal", "primary")),
    ])


# ── Mode / Difficulty Selectors ──────────

def mode_select_rich() -> InputRichMessage:
    return InputRichMessage(blocks=[
        _quote("☠️ SELECT ATTACK VECTOR"),
        _btn_row(_btn("🔤 WORD BREAKER", "mode:word", "primary")),
        _btn_row(_btn("🔢 NUMBER BREAKER", "mode:number", "primary")),
        _btn_row(_btn("🧬 MIXED BREAKER", "mode:mixed", "primary")),
        _btn_row(_btn("🔙 BACK", "terminal", "danger")),
    ])


def difficulty_rich(mode: str) -> InputRichMessage:
    name = {"word": "🔤 WORD BREAKER", "number": "🔢 NUMBER BREAKER", "mixed": "🧬 MIXED BREAKER"}[mode]
    return InputRichMessage(blocks=[
        _quote(f"{name}\n\nChoose security level:"),
        _btn_row(_btn("🟢 EASY", f"diff:{mode}:easy", "success")),
        _btn_row(_btn("🔵 NORMAL", f"diff:{mode}:normal", "primary")),
        _btn_row(_btn("🟣 HARD", f"diff:{mode}:hard", "primary")),
        _btn_row(_btn("🔴 EXTREME", f"diff:{mode}:extreme", "danger")),
        _btn_row(_btn("☠️ NIGHTMARE", f"diff:{mode}:nightmare", "danger")),
        _btn_row(_btn("🔙 BACK", "start_hack", "primary")),
    ])


def preview_rich(mode: str, diff: str, cfg: dict) -> InputRichMessage:
    return InputRichMessage(blocks=[
        _quote("MISSION PREVIEW"),
        _table([
            ["Property", "Value"],
            ["🧬 Mode", mode.upper()],
            ["🎯 Security", cfg["name"]],
            ["🔢 Length", str(cfg["length"])],
            ["⚡ Attempts", str(cfg["attempts"])],
            ["⏱️ Time", f"{cfg['time'] // 60} min"],
            ["💰 Reward", str(cfg["reward"])],
            ["⭐ XP", str(cfg["xp"])],
        ]),
        _btn_row(_btn("🚀 INITIATE BREACH", f"play:{mode}:{diff}", "success")),
        _btn_row(_btn("🔙 CHANGE SETTINGS", f"mode:{mode}", "primary")),
    ])


def get_rank(level: int) -> str:
    rank = RANKS[0][1]
    for lvl, name in RANKS:
        if level >= lvl:
            rank = name
    return rank

# ── Inventory / Balance / Pay ────────────

def build_inventory_rich(user: dict) -> InputRichMessage:
    """Inventory UI — currently shows owned coins and future ability slots."""
    coins = user.get("coins", 0)
    return InputRichMessage(blocks=[
        _quote("🎒 HACKER INVENTORY"),
        _table([
            ["Item", "Owned"],
            ["💰 Credits", f"{coins:,}"],
            ["🔎 Scanner", "0"],
            ["🧠 Trace", "0"],
            ["🔓 Decrypt", "0"],
            ["⚡ Overclock", "0"],
            ["🛡️ Firewall", "0"],
        ]),
        _btn_row(
            _btn("💳 BALANCE", "balance", "primary"),
            _btn("📊 STATS", "stats", "primary"),
        ),
        _btn_row(_btn("🔙 BACK", "terminal", "primary")),
    ])


def build_balance_rich(user: dict) -> InputRichMessage:
    """Show user's coin balance and quick actions."""
    coins = user.get("coins", 0)
    return InputRichMessage(blocks=[
        _quote("💳 YOUR BALANCE"),
        _table([
            ["Property", "Value"],
            ["💰 Credits", f"{coins:,}"],
            ["⭐ Level", str(user.get("level", 1))],
            ["🔥 Streak", str(user.get("streak", 0))],
        ]),
        _quote("Send coins with: /pay <user_id> <amount>"),
        _btn_row(
            _btn("🎒 INVENTORY", "inventory", "primary"),
            _btn("🏆 LEADERBOARD", "leaderboard:credits:0", "primary"),
        ),
        _btn_row(_btn("🏠 HOME", "terminal", "success")),
    ])


def build_pay_confirm_rich(
    receiver_id: int,
    receiver_name: str,
    amount: int,
    sender_balance: int,
) -> InputRichMessage:
    """Confirmation UI before executing a coin transfer."""
    return InputRichMessage(blocks=[
        _quote("💸 CONFIRM TRANSFER"),
        _table([
            ["Property", "Value"],
            ["👤 To", receiver_name],
            ["🆔 Receiver ID", str(receiver_id)],
            ["💰 Amount", f"{amount:,}"],
            ["💳 Your Balance", f"{sender_balance:,}"],
            ["💳 After Transfer", f"{sender_balance - amount:,}"],
        ]),
        _btn_row(
            _btn("✅ CONFIRM", f"pay_confirm:{receiver_id}:{amount}", "success"),
            _btn("❌ CANCEL", "balance", "danger"),
        ),
    ])


def build_pay_result_rich(
    receiver_id: int,
    receiver_name: str,
    amount: int,
    new_balance: int,
) -> InputRichMessage:
    """Success UI after transfer."""
    return InputRichMessage(blocks=[
        _quote("✅ TRANSFER COMPLETE"),
        _table([
            ["Property", "Value"],
            ["👤 To", receiver_name],
            ["🆔 Receiver ID", str(receiver_id)],
            ["💰 Sent", f"{amount:,}"],
            ["💳 New Balance", f"{new_balance:,}"],
        ]),
        _btn_row(_btn("💳 BALANCE", "balance", "primary")),
        _btn_row(_btn("🏠 HOME", "terminal", "success")),
    ])