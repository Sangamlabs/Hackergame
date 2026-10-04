import secrets
import time
from datetime import datetime, timezone
from config import MODES, DIFFICULTIES, STREAK_BONUS_PER, STREAK_BONUS_MAX, SPEED_BONUS


def generate_target(mode: str, length: int) -> str:
    charset = MODES[mode]["charset"]
    return "".join(secrets.choice(charset) for _ in range(length))


def evaluate(guess: str, target: str) -> list[str]:
    """Return list of '🟩', '🟨', '⬜' — duplicate-aware."""
    n = len(target)
    result = ["⬜"] * n
    target_pool = list(target)

    # Pass 1: exact matches
    for i in range(n):
        if guess[i] == target[i]:
            result[i] = "🟩"
            target_pool[i] = None  # consumed

    # Pass 2: wrong position
    for i in range(n):
        if result[i] == "🟩":
            continue
        if guess[i] in target_pool:
            result[i] = "🟨"
            target_pool[target_pool.index(guess[i])] = None

    return result


def validate_guess(guess: str, mode: str, expected_len: int) -> str | None:
    """Return error string or None if valid."""
    if len(guess) != expected_len:
        return f"Expected length: {expected_len}\nYour input: {len(guess)} characters"
    charset = MODES[mode]["charset"]
    allowed = set(charset)
    if not all(c in allowed for c in guess):
        return f"{MODES[mode]['name']} accepts: {charset[:26]}..." if mode != "number" else "0-9"
    return None


def calculate_rewards(difficulty: str, streak: int, duration: float, max_time: int) -> dict:
    cfg = DIFFICULTIES[difficulty]
    base = cfg["reward"]
    xp = cfg["xp"]

    # streak bonus
    streak_mult = min(streak * STREAK_BONUS_PER, STREAK_BONUS_MAX)
    streak_bonus = int(base * streak_mult)

    # speed bonus
    speed_bonus = 0
    if duration < max_time * 0.3:
        speed_bonus = int(base * SPEED_BONUS)

    total = base + streak_bonus + speed_bonus
    return {
        "base": base,
        "streak_bonus": streak_bonus,
        "speed_bonus": speed_bonus,
        "total": total,
        "xp": xp,
    }