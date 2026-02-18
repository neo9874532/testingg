# bot.py
# -*- coding: utf-8 -*-
# النسخة المصلحة (v12.1 Fixed) بواسطة Manus
# الإصلاحات: نظام البحث (الاسم ثم السيرفر)، تصنيفات EgyDead كاملة، إصلاح جلب النتائج
import os
import time
import uuid
import sqlite3
import json
import urllib.parse
import requests
import telebot
from telebot import types
from datetime import datetime
from typing import Dict, List, Any, Optional

# ====== CONFIG ======
API_TOKEN = "7154244438:AAEqpUIHaa1-4MuNRX_apmaDwC6hiu2rVnc"
OWNER_ID = 5742480036
bot = telebot.TeleBot(API_TOKEN, parse_mode="HTML")

# API Endpoints
API_ALO_SEARCH = "https://api.dfkz.xo.je/alooy/?search="
API_ALO_DETAILS = "https://api.dfkz.xo.je/alooy/?url="
API_FUS_SEARCH = "https://api.dfkz.xo.je/fushaar/?q="
API_FUS_DETAILS = "https://api.dfkz.xo.je/fushaar/?link="
API_RIVO_SEARCH = "https://api.x7m.site/Rivo/?q="
API_RIVO_DETAILS = "https://api.x7m.site/Rivo/?id="
API_EGY_SEARCH = "https://api.dfkz.xo.je/egydead/?q="
API_EGY_DETAILS = "https://api.dfkz.xo.je/egydead/link.php?link="
API_EGY_MOVIES = "https://api.dfkz.xo.je/egydead/movie.php?type="
API_EGY_SERIES = "https://api.dfkz.xo.je/egydead/series.php?type="

START_PHOTO = "https://t.me/VIP_TOJE/6"
DEV_URL = "https://t.me/Xj_CD"
DB_FILE = "ghost_cinema_v12.db"

ICONS = {"egydead": "💀", "rivo": "🌐", "fushaar": "🎬", "alooy": "📺"}

# ====== DB HELPERS ======
def init_db():
    con = sqlite3.connect(DB_FILE)
    cur = con.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, first_name TEXT, username TEXT, joined_at INTEGER)")
    cur.execute("CREATE TABLE IF NOT EXISTS admins (user_id INTEGER PRIMARY KEY)")
    cur.execute("CREATE TABLE IF NOT EXISTS banned (user_id INTEGER PRIMARY KEY)")
    cur.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)")
    cur.execute("CREATE TABLE IF NOT EXISTS channels (id INTEGER PRIMARY KEY AUTOINCREMENT, channel_id TEXT, channel_url TEXT)")
    cur.execute("CREATE TABLE IF NOT EXISTS tokens (token TEXT PRIMARY KEY, user_id INTEGER, link TEXT, title TEXT, image TEXT, source TEXT, created_at INTEGER)")
    cur.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('bot_active', 'True')")
    cur.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('forced_sub', 'True')")
    cur.execute("INSERT OR IGNORE INTO admins (user_id) VALUES (?)", (OWNER_ID,))
    con.commit()
    con.close()

def db_execute(query: str, params: tuple = (), commit: bool = False):
    con = sqlite3.connect(DB_FILE)
    cur = con.cursor()
    try:
        cur.execute(query, params)
        if commit: con.commit(); return None
        return cur.fetchall()
    finally: con.close()

def is_admin(user_id: int) -> bool:
    return bool(db_execute("SELECT 1 FROM admins WHERE user_id=?", (user_id,))) or user_id == OWNER_ID

def is_banned(user_id: int) -> bool:
    return bool(db_execute("SELECT 1 FROM banned WHERE user_id=?", (user_id,)))

def get_setting(key: str, default: str = "") -> str:
    rows = db_execute("SELECT value FROM settings WHERE key=?", (key,))
    return rows[0][0] if rows else default

def set_setting(key: str, value: str):
    db_execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value), commit=True)

def get_channels():
    return db_execute("SELECT id, channel_id, channel_url FROM channels LIMIT 5")

# ====== API HELPERS ======
def http_get_json(url: str) -> Any:
    try:
        r = requests.get(url, timeout=15, headers={"User-Agent":"Mozilla/5.0"})
        text = r.text
        if "{" in text: text = text[text.find("{"):]
        elif "[" in text: text = text[text.find("["):]
        if "}" in text: text = text[:text.rfind("}")+1]
        if "]" in text: text = text[:text.rfind("]")+1]
        return json.loads(text)
    except: return {}

def create_token(user_id: int, link: str, title: str, image: str, source: str) -> str:
    t = uuid.uuid4().hex[:12]
    db_execute("INSERT OR REPLACE INTO tokens (token,user_id,link,title,image,source,created_at) VALUES (?,?,?,?,?,?,?)",
               (t, user_id, str(link), title, image, source, int(time.time())), commit=True)
    return t

def get_token(token: str):
    rows = db_execute("SELECT token,user_id,link,title,image,source FROM tokens WHERE token=?", (token,))
    return {"token": rows[0][0], "user_id": rows[0][1], "link": rows[0][2], "title": rows[0][3], "image": rows[0][4], "source": rows[0][5]} if rows else None

# ====== KEYBOARDS ======
def main_kb():
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(types.InlineKeyboardButton(f"{ICONS['egydead']} EgyDead", callback_data="p_egy"),
           types.InlineKeyboardButton(f"{ICONS['rivo']} Rivo", callback_data="p_rivo"))
    kb.add(types.InlineKeyboardButton(f"{ICONS['fushaar']} Fushaar", callback_data="p_fus"),
           types.InlineKeyboardButton(f"{ICONS['alooy']} ALOOYTV", callback_data="p_alo"))
    kb.row(types.InlineKeyboardButton("🔍 بحث", callback_data="m_search"))
    kb.row(types.InlineKeyboardButton("👨‍💻 المطور", url=DEV_URL))
    return kb

def egy_main_kb():
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(types.InlineKeyboardButton("🎬 الأفلام", callback_data="egy_cat_movies"),
           types.InlineKeyboardButton("📺 المسلسلات", callback_data="egy_cat_series"))
    kb.add(types.InlineKeyboardButton("👺 الأنمي", callback_data="egy_cat_anime"),
           types.InlineKeyboardButton("🎙️ المدبلج", callback_data="egy_cat_dubbed"))
    kb.add(types.InlineKeyboardButton("🎭 منوعات", callback_data="egy_cat_extra"))
    kb.add(types.InlineKeyboardButton("⬅️ رجوع", callback_data="home"))
    return kb

EGY_CATS = {
    "movies": [("أجنبي", "agnbi"), ("عربي", "arabic"), ("هندي", "indian"), ("تركي", "turkish"), ("كرتون", "cartoon"), ("أسيوية", "asian"), ("وثائقية", "doc")],
    "series": [("أجنبي", "agnbi"), ("عربي", "arabic"), ("تركي", "turkish"), ("آسيوي", "asian"), ("لاتيني", "latin"), ("أفريقي", "african")],
    "anime": [("مسلسلات أنمي", "anime"), ("أفلام أنمي", "anime_movies"), ("أنمي مدبلج", "anime_dubbed")],
    "dubbed": [("أفلام مدبلجة", "dubbed"), ("ديزني مصري", "disney"), ("كرتون مدبلج", "cartoon_dubbed")],
    "extra": [("برامج تلفزيونية", "tv_shows"), ("مسرحيات", "plays"), ("وثائقي", "documentary"), ("إسلام الجيزاوي", "islam")]
}

def build_cat_kb(cat_key, back="p_egy"):
    kb = types.InlineKeyboardMarkup(row_width=2)
    for name, slug in EGY_CATS[cat_key]:
        prefix = "egy_m" if cat_key == "movies" else "egy_s"
        kb.add(types.InlineKeyboardButton(name, callback_data=f"{prefix}|{slug}|page=1"))
    kb.add(types.InlineKeyboardButton("⬅️ رجوع", callback_data=back))
    return kb

# ====== HANDLERS ======
@bot.message_handler(commands=['start'])
def start(m: types.Message):
    init_db()
    user_id = m.chat.id
    if is_banned(user_id): return
    if not db_execute("SELECT 1 FROM users WHERE user_id=?", (user_id,)):
        db_execute("INSERT INTO users VALUES (?,?,?,?)", (user_id, m.from_user.first_name, m.from_user.username, int(time.time())), commit=True)
        notify_admins(f"👤 مستخدم جديد: {m.from_user.first_name} (@{m.from_user.username})")
    
    not_joined = check_sub(user_id)
    if not_joined:
        kb = types.InlineKeyboardMarkup(row_width=1)
        for c in not_joined: kb.add(types.InlineKeyboardButton(f"📢 اشترك: {c[1]}", url=c[2]))
        kb.add(types.InlineKeyboardButton("✅ تم الاشتراك", callback_data="check_sub"))
        bot.send_message(user_id, "⚠️ يجب الاشتراك في القنوات أولاً:", reply_markup=kb)
        return
    bot.send_photo(user_id, START_PHOTO, caption=f"مرحباً {m.from_user.first_name} في <b>Ghost Cinema</b>\nاختر المصدر:", reply_markup=main_kb())

def check_sub(user_id):
    if is_admin(user_id) or get_setting("forced_sub") != "True": return []
    channels = get_channels()
    not_joined = []
    for c in channels:
        try:
            s = bot.get_chat_member(c[1], user_id).status
            if s not in ['member', 'administrator', 'creator']: not_joined.append(c)
        except: continue
    return not_joined

def notify_admins(text):
    for admin in db_execute("SELECT user_id FROM admins"):
        try: bot.send_message(admin[0], f"🔔 <b>إشعار:</b>\n{text}")
        except: continue

@bot.callback_query_handler(func=lambda c: c.data == "home")
def home_cb(c: types.CallbackQuery):
    bot.edit_message_media(chat_id=c.message.chat.id, message_id=c.message.message_id, media=types.InputMediaPhoto(media=START_PHOTO, caption="اختر المصدر:"), reply_markup=main_kb())

@bot.callback_query_handler(func=lambda c: c.data == "p_egy")
def egy_main_cb(c: types.CallbackQuery):
    bot.edit_message_caption(chat_id=c.message.chat.id, message_id=c.message.message_id, caption=f"{ICONS['egydead']} واجهة <b>EgyDead</b>:", reply_markup=egy_main_kb())

@bot.callback_query_handler(func=lambda c: c.data.startswith("egy_cat_"))
def egy_cat_cb(c: types.CallbackQuery):
    key = c.data.replace("egy_cat_", "")
    bot.edit_message_caption(chat_id=c.message.chat.id, message_id=c.message.message_id, caption=f"📂 تصنيفات {key}:", reply_markup=build_cat_kb(key))

@bot.callback_query_handler(func=lambda c: c.data == "m_search")
def search_init(c: types.CallbackQuery):
    bot.edit_message_caption(chat_id=c.message.chat.id, message_id=c.message.message_id, caption="🔎 أرسل اسم الفيلم أو المسلسل للبحث عنه:")
    bot.register_next_step_handler(c.message, ask_search_source)

def ask_search_source(m: types.Message):
    query = m.text.strip()
    if query.startswith('/'): return
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(types.InlineKeyboardButton(f"{ICONS['egydead']} EgyDead", callback_data=f"do_s|egy|{query}"),
           types.InlineKeyboardButton(f"{ICONS['rivo']} Rivo", callback_data=f"do_s|rivo|{query}"))
    kb.add(types.InlineKeyboardButton(f"{ICONS['fushaar']} Fushaar", callback_data=f"do_s|fus|{query}"),
           types.InlineKeyboardButton(f"{ICONS['alooy']} ALOOYTV", callback_data=f"do_s|alo|{query}"))
    kb.row(types.InlineKeyboardButton("🌀 البحث في الكل", callback_data=f"do_s|all|{query}"))
    kb.row(types.InlineKeyboardButton("🏠 القائمة", callback_data="home"))
    bot.send_message(m.chat.id, f"🔍 اختر مصدر البحث لـ: <b>{query}</b>", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("do_s|"))
def process_search(c: types.CallbackQuery):
    bot.answer_callback_query(c.id, "جاري البحث...")
    parts = c.data.split("|")
    source, query = parts[1], parts[2]
    
    results = []
    if source in ("egy", "all"):
        res = http_get_json(API_EGY_SEARCH + urllib.parse.quote(query))
        for it in res.get("results", [])[:6]:
            token = create_token(c.from_user.id, it['link'], it['title'], it.get('image',''), "egydead")
            results.append(types.InlineKeyboardButton(f"{ICONS['egydead']} {it['title']}", callback_data=f"show|{token}"))
    
    if source in ("rivo", "all"):
        res = http_get_json(API_RIVO_SEARCH + urllib.parse.quote(query))
        if isinstance(res, list):
            for it in res[:6]:
                token = create_token(c.from_user.id, str(it['id']), it['title'], it.get('portrait',''), "rivo")
                results.append(types.InlineKeyboardButton(f"{ICONS['rivo']} {it['title']}", callback_data=f"show|{token}"))

    if source in ("fus", "all"):
        res = http_get_json(API_FUS_SEARCH + urllib.parse.quote(query))
        for it in res.get("results", [])[:6]:
            token = create_token(c.from_user.id, it['link'], it['title'], it.get('image',''), "fushaar")
            results.append(types.InlineKeyboardButton(f"{ICONS['fushaar']} {it['title']}", callback_data=f"show|{token}"))

    if source in ("alo", "all"):
        res = http_get_json(API_ALO_SEARCH + urllib.parse.quote(query))
        if isinstance(res, list):
            for it in res[:6]:
                token = create_token(c.from_user.id, it['url'], it['title'], it.get('portrait',''), "alooy")
                results.append(types.InlineKeyboardButton(f"{ICONS['alooy']} {it['title']}", callback_data=f"show|{token}"))

    kb = types.InlineKeyboardMarkup(row_width=1)
    for btn in results: kb.add(btn)
    kb.add(types.InlineKeyboardButton("🏠 القائمة", callback_data="home"))
    
    if not results:
        bot.edit_message_text(f"❌ لم يتم العثور على نتائج لـ: {query}", c.message.chat.id, c.message.message_id, reply_markup=kb)
    else:
        bot.edit_message_text(f"✅ نتائج البحث عن: <b>{query}</b>", c.message.chat.id, c.message.message_id, reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("show|"))
def show_details(c: types.CallbackQuery):
    token = c.data.split("|")[1]
    info = get_token(token)
    if not info: return
    bot.answer_callback_query(c.id, "جاري جلب التفاصيل...")
    
    source, link = info['source'], info['link']
    details = {"title": info['title'], "story": "لا يوجد وصف.", "year": "?", "rate": "?", "genres": "", "image": info['image']}
    has_eps = False
    
    if source == "egydead":
        data = http_get_json(API_EGY_DETAILS + urllib.parse.quote_plus(link))
        details.update({"title": data.get("title", info['title']), "story": data.get("story", "لا يوجد وصف."), "year": data.get("السنه", "?"), "rate": data.get("views", "?"), "genres": data.get("النوع", ""), "image": data.get("image", info['image'])})
        if "series" in link or "episode" in link: has_eps = True
    elif source == "rivo":
        data = http_get_json(API_RIVO_DETAILS + link)
        det = data.get("details", {})
        details.update({"title": det.get("name", info['title']), "story": det.get("overview", "لا يوجد وصف."), "genres": det.get("kind", ""), "image": det.get("portrait", info['image'])})
        if len(data.get("epiks", [])) > 1: has_eps = True

    caption = f"{ICONS[source]} <b>{details['title']}</b>\n\n📅 السنة: {details['year']}\n⭐ التقييم: {details['rate']}\n🎭 التصنيف: {details['genres']}\n\n📖 القصة:\n{details['story'][:600]}..."
    kb = types.InlineKeyboardMarkup(row_width=1)
    if has_eps: kb.add(types.InlineKeyboardButton("📺 عرض الحلقات", callback_data=f"eps|{token}"))
    else: kb.add(types.InlineKeyboardButton("▶️ مشاهدة مباشرة", callback_data=f"watch|{token}"))
    kb.add(types.InlineKeyboardButton("🏠 القائمة", callback_data="home"))
    
    try: bot.edit_message_media(chat_id=c.message.chat.id, message_id=c.message.message_id, media=types.InputMediaPhoto(media=details['image'] or START_PHOTO, caption=caption), reply_markup=kb)
    except: bot.send_photo(c.message.chat.id, details['image'] or START_PHOTO, caption=caption, reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("watch|"))
def watch_cb(c: types.CallbackQuery):
    token = c.data.split("|")[1]
    info = get_token(token)
    kb = types.InlineKeyboardMarkup(row_width=1)
    if info['source'] == "egydead":
        data = http_get_json(API_EGY_DETAILS + urllib.parse.quote_plus(info['link']))
        for s in data.get("servers", []): kb.add(types.InlineKeyboardButton(f"🚀 {s['name']}", url=s['link']))
    elif info['source'] == "rivo":
        data = http_get_json(API_RIVO_DETAILS + info['link'])
        for ep in data.get("epiks", []):
            kb.add(types.InlineKeyboardButton("🚀 سيرفر المشاهدة", url=ep['file']))
            break
    kb.add(types.InlineKeyboardButton("⬅️ رجوع", callback_data=f"show|{token}"))
    bot.edit_message_caption(chat_id=c.message.chat.id, message_id=c.message.message_id, caption=f"🎬 روابط المشاهدة لـ <b>{info['title']}</b>:", reply_markup=kb)

if __name__ == "__main__":
    init_db()
    print("Ghost Cinema v12.1 Fixed is running...")
    bot.infinity_polling()
