"""
Centralized Telegram Custom Emoji registry.
Fallback to Unicode emoji when ID is missing or invalid.
"""

# ═══════════════════════════════════════════════════════════
# REGISTRY — Add real Telegram custom emoji IDs here
# ═══════════════════════════════════════════════════════════
# Format:
#   "key": {"id": "<telegram_custom_emoji_id>", "fallback": "🟢"}
#
# Leave "id" empty ("") to use the fallback emoji.
# DO NOT invent IDs — leave blank until you have the real ones.

CUSTOM_EMOJIS: dict[str, dict[str, str]] = {
    # ── Core categories ──────────────────
    "terminal":    {"id": "5954090983233690091", "fallback": "☠️"},
    "game":        {"id": "6301042242450625545", "fallback": "🎮"},
    "profile":     {"id": "6264538349034281099", "fallback": "👤"},
    "leaderboard": {"id": "5226431245918942763", "fallback": "🏆"},
    "system":      {"id": "6267107057304868214", "fallback": "⚡"},

    # ── Abilities ────────────────────────
    "scan":        {"id": "5188311512791393083", "fallback": "🔎"},
    "trace":       {"id": "5237799019329105246", "fallback": "🧠"},
    "decrypt":     {"id": "5465443379917629504", "fallback": "🔓"},
    "overclock":   {"id": "6267107057304868214", "fallback": "⚡"},

    # ── Status ───────────────────────────
    "success":     {"id": "", "fallback": "✅"},
    "danger":      {"id": "", "fallback": "❌"},
    "warning":     {"id": "", "fallback": "⚠️"},
    "lock":        {"id": "", "fallback": "🔒"},
    "online":      {"id": "", "fallback": "🟢"},

    # ── Game stats ───────────────────────
    "money":       {"id": "", "fallback": "💰"},
    "xp":          {"id": "", "fallback": "⭐"},
    "time":        {"id": "", "fallback": "⏱️"},
    "difficulty":  {"id": "", "fallback": "🎯"},
    "code":        {"id": "", "fallback": "🔑"},
    "length":      {"id": "", "fallback": "🔢"},
    "attempts":    {"id": "", "fallback": "⚡"},

    # ── Modes ────────────────────────────
    "word":        {"id": "", "fallback": "🔤"},
    "number":      {"id": "", "fallback": "🔢"},
    "mixed":       {"id": "", "fallback": "🧬"},

    # ── Difficulties ─────────────────────
    "easy":        {"id": "5809949600152296075", "fallback": "🟢"},
    "normal":      {"id": "5433730264821933722", "fallback": "🔵"},
    "hard":        {"id": "5339128610785610228", "fallback": "🟣"},
    "extreme":     {"id": "5411225014148014586", "fallback": "🔴"},
    "nightmare":   {"id": "5954090983233690091", "fallback": "☠️"},

    # ── Navigation ───────────────────────
    "inventory":   {"id": "", "fallback": "🎒"},
    "back":        {"id": "", "fallback": "🔙"},
    "home":        {"id": "", "fallback": "🏠"},
    "settings":    {"id": "", "fallback": "⚙️"},
    "refresh":     {"id": "", "fallback": "🔄"},
    "start_hack":  {"id": "", "fallback": "🔐"},
    "rocket":      {"id": "", "fallback": "🚀"},
    "play_again":  {"id": "", "fallback": "🔁"},

    # ── System ───────────────────────────
    "ping":        {"id": "", "fallback": "🏓"},
    "bot":         {"id": "", "fallback": "🤖"},
    "users":       {"id": "", "fallback": "👥"},
    "database":    {"id": "", "fallback": "🗄"},
    "help":        {"id": "", "fallback": "❓"},
    "chart":       {"id": "", "fallback": "📊"},

    # ── Game result indicators (KEEP AS-IS) ──
    # These are Wordle-style semantics, not decorative emoji.
    # Leave them self-contained in ui.py — do NOT route through this registry.
}


# ═══════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════

def get_custom_emoji_id(name: str) -> str | None:
    """Return the custom emoji ID (or None if not configured)."""
    entry = CUSTOM_EMOJIS.get(name)
    if not entry:
        return None
    emoji_id = (entry.get("id") or "").strip()
    return emoji_id or None


def get_custom_emoji_fallback(name: str) -> str:
    """Return the Unicode fallback for a custom emoji key."""
    entry = CUSTOM_EMOJIS.get(name)
    if not entry:
        return ""
    return entry.get("fallback", "")


def ce(name: str) -> str:
    """
    Text-safe custom emoji representation.

    NOTE: Telegram does NOT allow arbitrary <emoji id> HTML in
    InputRichBlockParagraph text. For Rich text blocks, the only
    safe representation is the Unicode fallback.

    For custom emoji rendering in text, Telegram requires
    MessageEntity.CUSTOM_EMOJI, which is not yet exposed via
    the Rich block API in aiogram 3.x.

    So: ce() returns the fallback. Buttons use the real custom
    emoji via icon_custom_emoji_id (see _btn in ui.py).
    """
    return get_custom_emoji_fallback(name)


def ce_pair(name: str) -> tuple[str | None, str]:
    """
    Return (custom_emoji_id, fallback) for a registry key.
    Useful for button builders.
    """
    return (get_custom_emoji_id(name), get_custom_emoji_fallback(name))


def button_icon(name: str) -> str | None:
    """Return the custom emoji ID for a button icon, or None."""
    return get_custom_emoji_id(name)