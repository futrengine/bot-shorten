import os
import firebase_admin
from firebase_admin import credentials, firestore
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# --- Config ---
API_ID = YOUR_API_ID
API_HASH = "YOUR_API_HASH"
BOT_TOKEN = "YOUR_BOT_TOKEN"
FIREBASE_JSON = "firebase-cred.json"

# --- Init ---
app = Client("shortener_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
cred = credentials.Certificate(FIREBASE_JSON)
firebase_admin.initialize_app(cred)
db = firestore.client()

SHORTENER_URL = "https://futrengine.github.io/s/"  # Change if needed

# --- Utils ---
def get_user_limit(user_id):
    user_ref = db.collection("users").document(str(user_id))
    doc = user_ref.get()
    if doc.exists:
        return doc.to_dict().get("limit", 0)
    else:
        user_ref.set({"limit": 5})
        return 5

def update_user_limit(user_id, add=0, reset=False):
    user_ref = db.collection("users").document(str(user_id))
    if reset:
        user_ref.set({"limit": 5})
    else:
        current = get_user_limit(user_id)
        user_ref.update({"limit": current + add})

# --- Commands ---
@app.on_message(filters.command("start"))
async def start(_, msg):
    await msg.reply(
        "**👋 Welcome to FutrEngine Shortener Bot**\n\n"
        "🔗 Shorten and customize big URLs.\n"
        "🎁 5 links free. Tap below to unlock more:\n\n"
        "_Use /stats to check remaining links._",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔓 Unlock Links", url="https://your-monetag-miniapp.com")],
            [InlineKeyboardButton("🌐 Visit Site", url="https://futrengine.github.io/")]
        ])
    )

@app.on_message(filters.command("stats"))
async def stats(_, msg):
    limit = get_user_limit(msg.from_user.id)
    if limit <= 0:
        await msg.reply("❌ You've used all 5 free links. Tap below to unlock 2 more:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔓 Watch Ad", url="https://your-monetag-miniapp.com")]
            ])
        )
    else:
        await msg.reply(f"🔢 You have **{limit}** links left to shorten.")

@app.on_message(filters.text & filters.private & ~filters.command(["start", "stats"]))
async def handle_url(_, msg):
    user_id = msg.from_user.id
    limit = get_user_limit(user_id)

    if limit <= 0:
        await msg.reply("❌ No links left. Tap below to unlock:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔓 Unlock Now", url="https://your-monetag-miniapp.com")]
            ])
        )
        return

    long_url = msg.text.strip()
    await msg.reply("✏️ Do you want a custom alias?",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("❌ No Alias", callback_data=f"alias:|{long_url}")]
        ])
    )

@app.on_callback_query(filters.regex("^alias:"))
async def alias_step(_, callback):
    alias, long_url = callback.data.replace("alias:", "").split("|", 1)
    if not alias:
        await callback.message.reply("🔒 Do you want to set a password?",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("❌ No Password", callback_data=f"final:{long_url}|None|None")]
            ])
        )
    else:
        await callback.message.reply("✏️ Please type your alias:")

@app.on_message(filters.text & filters.private)
async def alias_or_password_input(_, msg):
    text = msg.text.strip()
    if "alias" in msg.reply_to_message.text.lower():
        alias = text
        await msg.reply("🔐 Send password or tap skip.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("❌ No Password", callback_data=f"final:{msg.reply_to_message.text}|{alias}|None")]
            ])
        )
    elif "password" in msg.reply_to_message.text.lower():
        password = text
        long_url = msg.reply_to_message.text.split("|")[1]  # extract properly
        alias = msg.reply_to_message.text.split("|")[2]
        await create_short_and_reply(msg.chat.id, long_url, alias, password)

@app.on_callback_query(filters.regex("^final:"))
async def final_step(_, callback):
    long_url, alias, password = callback.data.replace("final:", "").split("|")
    await create_short_and_reply(callback.from_user.id, long_url, alias, password)

# --- Shortener Logic ---
async def create_short_and_reply(chat_id, long_url, alias, password):
    user_id = chat_id
    update_user_limit(user_id, add=-1)
    
    # Normally you'd create the link via Firebase Function or encode it yourself
    import random, string
    suffix = alias or ''.join(random.choices(string.ascii_letters + string.digits, k=6))
    short_url = SHORTENER_URL + suffix

    # Optionally store link in Firebase
    db.collection("short_links").document(suffix).set({
        "original": long_url,
        "user": user_id,
        "password": password or "",
        "created": firestore.SERVER_TIMESTAMP
    })

    await app.send_message(chat_id,
        f"✅ Your Short Link:\n`{short_url}`",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🌐 Open", url=short_url)]
        ])
    )

app.run()
