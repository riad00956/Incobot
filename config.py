import os
from dotenv import load_dotenv

load_dotenv()

# --- বটের প্রধান কনফিগারেশন ---
API_TOKEN = "YOUR_BOT_TOKEN" # @BotFather থেকে প্রাপ্ত টোকেন
MONGO_URI = "YOUR_MONGODB_URI" # MongoDB Atlas থেকে প্রাপ্ত লিঙ্ক
ADMIN_IDS = [12345678, 87654321] # আপনার আইডি

# চ্যানেল ভেরিফিকেশন (বটকে চ্যানেলে এডমিন করতে হবে)
CHANNELS = ["@YourChannel1", "@YourChannel2"] 

# রিওয়ার্ড সেটিংস
AD_REWARD = 0.50
SPIN_COOLDOWN = 3600 # ১ ঘণ্টা (সেকেন্ডে)
MIN_WITHDRAW = 50.0
