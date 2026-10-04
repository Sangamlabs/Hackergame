import time
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient
from config import MONGODB_URI, MONGODB_DB
from pymongo.errors import DuplicateKeyError

client: AsyncIOMotorClient = None
db = None


def get_db():
    """Safe DB accessor. Raises if init_db() not called."""
    if db is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    return db


async def init_db():
    global client, db
    client = AsyncIOMotorClient(MONGODB_URI)
    db = client[MONGODB_DB]
    await client.admin.command("ping")
    await db.users.create_index("user_id", unique=True)
    await db.games.create_index([("chat_id", 1), ("user_id", 1), ("status", 1)])
    await db.games.create_index("game_id", unique=True)
    await db.transactions.create_index([("from_user_id", 1), ("ts", -1)])
    print(f"[db] Connected to {db.name}")


async def close_db():
    global client
    if client:
        client.close()


# ── Users ────────────────────────────────

async def get_user(user_id: int, **defaults):
    """Fetch or auto-create a user. Always syncs username/first_name."""
    user = await db.users.find_one({"user_id": user_id})

    if user:
        updates = {}
        if "username" in defaults and user.get("username") != (defaults["username"] or ""):
            updates["username"] = defaults["username"] or ""
        if "first_name" in defaults and user.get("first_name") != (defaults["first_name"] or ""):
            updates["first_name"] = defaults["first_name"] or ""
        if updates:
            await db.users.update_one({"user_id": user_id}, {"$set": updates})
            user.update(updates)
        return user

    now = datetime.now(timezone.utc)
    new_user = {
        "user_id": user_id,
        "username": defaults.get("username", "") or "",
        "first_name": defaults.get("first_name", "") or "",
        "coins": 100, "xp": 0, "level": 1,
        "wins": 0, "losses": 0, "streak": 0,
        "best_streak": 0, "best_time": None,
        "created_at": now,
    }
    try:
        await db.users.insert_one(new_user)
        return new_user
    except DuplicateKeyError:
        return await db.users.find_one({"user_id": user_id})


async def update_user(user_id: int, updates: dict):
    await db.users.update_one({"user_id": user_id}, {"$set": updates})


# ── Games ────────────────────────────────

async def create_game(doc: dict):
    await db.games.insert_one(doc)


async def get_active_game(chat_id: int, user_id: int):
    return await db.games.find_one({
        "chat_id": chat_id,
        "user_id": user_id,
        "status": "ACTIVE",
    })


async def get_owned_game(game_id: str, user_id: int):
    """Ownership-safe game fetch."""
    return await db.games.find_one({
        "game_id": game_id,
        "user_id": user_id,
    })


async def update_game(game_id: str, updates: dict):
    await db.games.update_one({"game_id": game_id}, {"$set": updates})


async def get_user_games(user_id: int, limit: int = 10):
    cursor = db.games.find(
        {"user_id": user_id, "status": {"$in": ["WON", "LOST", "EXPIRED"]}}
    ).sort("completed_at", -1).limit(limit)
    return await cursor.to_list(length=limit)


async def get_leaderboard(sort_field: str, limit: int = 10):
    cursor = db.users.find().sort(sort_field, -1).limit(limit)
    return await cursor.to_list(length=limit)


async def get_user_rank(sort_field: str, user_id: int):
    total = await db.users.count_documents({})
    if total == 0:
        return 0, 0
    user = await db.users.find_one({"user_id": user_id})
    if not user:
        return 0, total
    val = user.get(sort_field, 0) or 0
    better = await db.users.count_documents({sort_field: {"$gt": val}})
    return better + 1, total


async def transfer_coins(from_user_id: int, to_user_id: int, amount: int) -> dict:
    """Transfer coins between users safely."""
    if amount <= 0:
        return {"ok": False, "reason": "Amount must be positive"}
    if from_user_id == to_user_id:
        return {"ok": False, "reason": "Cannot pay yourself"}

    sender = await db.users.find_one({"user_id": from_user_id})
    if not sender:
        return {"ok": False, "reason": "Sender not found"}

    receiver = await db.users.find_one({"user_id": to_user_id})
    if not receiver:
        return {"ok": False, "reason": "Receiver not found — they must /start the bot first"}

    sender_balance = sender.get("coins", 0)
    if sender_balance < amount:
        return {
            "ok": False,
            "reason": f"Insufficient balance (you have {sender_balance})",
            "from_balance": sender_balance,
        }

    try:
        await db.users.update_one(
            {"user_id": from_user_id, "coins": {"$gte": amount}},
            {"$inc": {"coins": -amount}},
        )
        await db.users.update_one(
            {"user_id": to_user_id},
            {"$inc": {"coins": amount}},
        )
    except Exception as e:
        print(f"[transfer_coins] {e!r}")
        return {"ok": False, "reason": "Database error"}

    new_sender = await db.users.find_one({"user_id": from_user_id}) or {}
    new_receiver = await db.users.find_one({"user_id": to_user_id}) or {}

    try:
        await db.transactions.insert_one({
            "from_user_id": from_user_id,
            "to_user_id": to_user_id,
            "amount": amount,
            "ts": datetime.now(timezone.utc),
        })
    except Exception:
        pass

    return {
        "ok": True,
        "reason": "Success",
        "from_balance": new_sender.get("coins", 0),
        "to_balance": new_receiver.get("coins", 0),
    }