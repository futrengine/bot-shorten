import os, json, random, string
import firebase_admin
from firebase_admin import credentials, firestore
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# Env vars
BOT_TOKEN = os.getenv("BOT_TOKEN")
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")

# Firebase setup from ENV var
firebase_json = json.loads(os.getenv("FIREBASE_JSON"))
cred = credentials.Certificate(firebase_json)
firebase_admin.initialize_app(cred)
db = firestore.client()

SHORT_BASE = "https://futrengine.github.io/s/"  # your short link prefix

app = Client("bot", bot_token=BOT_TOKEN, api_id=API_ID, api_hash=API_HASH)

# DB limit functions
def get_limit(user_id):
    doc = db.collection("users").document(str(user_id)).get()
    if doc.exists:
        return doc.to_dict().get("limit", 5)
    else:
        db.collection("users").document(str(user_id)).set({"limit": 5})
        return 5

def update_limit(user_id, delta):
    ref = db.collection("users").document(str(user_id))
    current = get_limit(user_id)
    ref.update({"limit": current + delta})

@app.on_message(filters.command("start"))
async def start(client, message):
    await message.reply(
        "**👋 Welcome to FutrEngine URL Shortener**\n\n"
        "🔗 First 5 shortens are free.\n"
        "👉 To get 2 more, tap below and view ad.",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🔓 Unlock More", url="https://your-monetag-ad-url.com"),
                InlineKeyboardButton("🌐 Website", url="https://futrengine.github.io/")
            ]
        ])
    )

@app.on_message(filters.command("stats"))
async def stats(client, message):
    limit = get_limit(message.from_user.id)
    if limit > 0:
        await message.reply(f"🧮 You can shorten **{limit}** more links.")
    else:
        await message.reply(
            "❌ Limit reached. Tap below to get more!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔓 Unlock", url="https://your-monetag-ad-url.com")]
            ])
        )

@app.on_message(filters.text & filters.private & ~filters.command(["start", "stats"]))
async def shorten(client, message):
    user_id = message.from_user.id
    url = message.text.strip()
    limit = get_limit(user_id)

    if limit <= 0:
        await message.reply(
            "🚫 You have no remaining links. Tap below to unlock more.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔓 Watch Ad", url="https://your-monetag-ad-url.com")]
            ])
        )
        return

    alias = ''.join(random.choices(string.ascii_letters + string.digits, k=6))
    short_url = SHORT_BASE + alias

    # Save link to Firebase
    db.collection("short_links").document(alias).set({
        "user": user_id,
        "long_url": url,
        "created": firestore.SERVER_TIMESTAMP
    })

    update_limit(user_id, -1)

    await message.reply(
        f"✅ Your short link:\n`{short_url}`",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🌐 Open Link", url=short_url)]
        ])
    )

app.run()
