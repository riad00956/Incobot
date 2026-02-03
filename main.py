import asyncio
import time
import uuid
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandObject
from aiogram.utils.keyboard import InlineKeyboardBuilder
from motor.motor_asyncio import AsyncIOMotorClient
from fastapi import FastAPI
import uvicorn
from threading import Thread

from config import API_TOKEN, MONGO_URI, ADMIN_IDS, AD_REWARD, MIN_WITHDRAW
from locales import TEXTS

# --- বানিজ্যিক গ্রেড ডাটাবেস কানেকশন ---
db_client = AsyncIOMotorClient(MONGO_URI)
db = db_client['income_bot_v2']
users_col = db['users']
ads_col = db['ads']

bot = Bot(token=API_TOKEN)
dp = Dispatcher()
ad_timers = {} # Anti-fraud timer storage

# --- ইউটিলিটি ফাংশন ---
async def get_user(user_id):
    return await users_col.find_one({"user_id": user_id})

def get_lang(user_doc):
    return user_doc.get('lang', 'en')

# --- ডায়নামিক কীবোর্ড ---
def main_menu_kb(lang, is_admin=False):
    kb = InlineKeyboardBuilder()
    t = TEXTS[lang]
    kb.row(types.InlineKeyboardButton(text=t['watch_ads'], callback_data="ads_menu"))
    kb.row(
        types.InlineKeyboardButton(text="🎰 Spin", callback_data="spin_game"),
        types.InlineKeyboardButton(text=t['refer'], callback_data="refer_menu")
    )
    kb.row(types.InlineKeyboardButton(text=t['wallet'], callback_data="wallet_menu"))
    if is_admin:
        kb.row(types.InlineKeyboardButton(text="⚙️ Admin Dashboard", callback_data="admin_home"))
    return kb.as_markup()

# --- হ্যান্ডলারসমূহ ---
@dp.message(Command("start"))
async def start_cmd(message: types.Message, command: CommandObject):
    user_id = message.from_id
    user = await get_user(user_id)
    
    # রেফারেল ট্র্যাকিং
    ref_id = None
    if command.args and command.args.isdigit():
        ref_id = int(command.args)

    if not user:
        new_user = {
            "user_id": user_id,
            "full_name": message.from_user.full_name,
            "balance": 0.0,
            "lang": "en",
            "is_vip": False,
            "ref_by": ref_id if ref_id != user_id else None,
            "joined": time.time()
        }
        await users_col.insert_one(new_user)
        if ref_id:
            await users_col.update_one({"user_id": ref_id}, {"$inc": {"balance": 1.0}}) # জয়েন বোনাস

    user = await get_user(user_id)
    lang = get_lang(user)
    text = TEXTS[lang]['welcome'].format(
        name=message.from_user.first_name,
        status="💎 VIP" if user['is_vip'] else "🆓 Basic",
        balance=round(user['balance'], 2)
    )
    await message.answer(text, reply_markup=main_menu_kb(lang, user_id in ADMIN_IDS), parse_mode="Markdown")

# --- অ্যাড ওয়াচিং সিস্টেম (Server-side Secure) ---
@dp.callback_query(F.data == "ads_menu")
async def ads_menu(call: types.CallbackQuery):
    token = str(uuid.uuid4())[:8]
    ad_timers[call.from_user.id] = {"time": time.time(), "token": token}
    
    kb = InlineKeyboardBuilder()
    kb.row(types.InlineKeyboardButton(text="🔗 Open Video Ad", url="https://google.com")) # এখানে ডাইনামিক লিঙ্ক হবে
    kb.row(types.InlineKeyboardButton(text="✅ Verify Reward", callback_data=f"v_{token}"))
    
    await call.message.edit_text("📺 *Watching Ad...*\nKeep the link open for 15 seconds to earn.", 
                                 reply_markup=kb.as_markup(), parse_mode="Markdown")

@dp.callback_query(F.data.startswith("v_"))
async def verify_ad(call: types.CallbackQuery):
    user_id = call.from_user.id
    token = call.data.split("_")[1]
    
    session = ad_timers.get(user_id)
    if not session or session['token'] != token:
        return await call.answer("❌ Invalid Ad Session!", show_alert=True)
    
    elapsed = time.time() - session['time']
    if elapsed < 15:
        return await call.answer(f"⏳ Wait {int(15-elapsed)}s more!", show_alert=True)
    
    # রিওয়ার্ড প্রদান
    await users_col.update_one({"user_id": user_id}, {"$inc": {"balance": AD_REWARD}})
    del ad_timers[user_id]
    
    user = await get_user(user_id)
    lang = get_lang(user)
    await call.message.edit_text(f"✅ {AD_REWARD} BDT added!", reply_markup=main_menu_kb(lang, user_id in ADMIN_IDS))

# --- অ্যাডমিন প্যানেল ---
@dp.callback_query(F.data == "admin_home")
async def admin_home(call: types.CallbackQuery):
    if call.from_user.id not in ADMIN_IDS: return
    
    total_users = await users_col.count_documents({})
    kb = InlineKeyboardBuilder()
    kb.row(types.InlineKeyboardButton(text="📊 Stats", callback_data="adm_stats"))
    kb.row(types.InlineKeyboardButton(text="📢 Broadcast", callback_data="adm_bc"))
    kb.row(types.InlineKeyboardButton(text="❌ Close", callback_data="close"))
    
    await call.message.edit_text(f"🛠 *ADMIN PANEL*\nTotal Users: {total_users}", 
                                 reply_markup=kb.as_markup(), parse_mode="Markdown")

# --- ওয়েব সার্ভার (Render Keep-Alive) ---
app = FastAPI()

@app.get("/")
def home():
    return {"status": "Bot is alive and running!"}

def run_fastapi():
    uvicorn.run(app, host="0.0.0.0", port=8000)

async def main():
    Thread(target=run_fastapi, daemon=True).start()
    print("🚀 Nexus Bot Started...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
