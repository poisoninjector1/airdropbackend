from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sqlite3
import time
import requests

app = FastAPI(title="Airdrop Mining Bot Backend")

# Frontend (Mini App) কানেক্ট করার জন্য CORS অনুমতি
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration Setup
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"  # BotFather থেকে পাওয়া বটের টোকেন
ADMIN_ID = 123456789                # আপনার নিজের টেলিগ্রাম ইউজার আইডি

# Database Initialization
def init_db():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            balance REAL DEFAULT 0.0,
            mining_speed REAL DEFAULT 36000.0,
            last_updated INTEGER,
            referred_by INTEGER
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# Data Models
class UserRegister(BaseModel):
    user_id: int
    username: str = ""
    referrer_id: int = None

class BroadcastMessage(BaseModel):
    admin_id: int
    message: str

# 1. Mining & Sync Endpoint
@app.post("/api/user/sync")
def sync_user(data: UserRegister):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    current_time = int(time.time())
    
    cursor.execute("SELECT balance, mining_speed, last_updated FROM users WHERE user_id = ?", (data.user_id,))
    user = cursor.fetchone()
    
    if user:
        old_balance, speed, last_updated = user
        elapsed_seconds = current_time - last_updated
        # Speed per hour to speed per second calculation
        new_balance = old_balance + (elapsed_seconds * (speed / 3600.0))
        
        cursor.execute("UPDATE users SET balance = ?, last_updated = ? WHERE user_id = ?", 
                       (new_balance, current_time, data.user_id))
    else:
        # Default Speed: 10 Coins/Sec = 36,000 Coins/Hour
        speed = 36000.0
        
        # Referral Bonus: রেফার করা ইউজারকে +১ কয়েন/সেকেন্ড (+৩৬০০/ঘণ্টা) বোনাস
        if data.referrer_id and data.referrer_id != data.user_id:
            cursor.execute("UPDATE users SET mining_speed = mining_speed + 3600.0 WHERE user_id = ?", (data.referrer_id,))
            
        cursor.execute("INSERT INTO users (user_id, username, balance, mining_speed, last_updated, referred_by) VALUES (?, ?, ?, ?, ?, ?)",
                       (data.user_id, data.username, 0.0, speed, current_time, data.referrer_id))
        new_balance = 0.0
        
    conn.commit()
    conn.close()
    
    return {
        "status": "success",
        "user_id": data.user_id,
        "balance": round(new_balance, 2),
        "mining_speed": speed / 3600.0  # UI-তে Coins/Sec আকারে পাঠাবে
    }

# 2. Admin Announcement Broadcast Endpoint
@app.post("/api/admin/broadcast")
def broadcast_message(data: BroadcastMessage):
    if data.admin_id != ADMIN_ID:
        raise HTTPException(status_code=403, detail="Access denied! You are not the admin.")
        
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users")
    users = cursor.fetchall()
    conn.close()
    
    count = 0
    for u in users:
        user_id = u[0]
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {"chat_id": user_id, "text": data.message, "parse_mode": "HTML"}
        try:
            res = requests.post(url, json=payload)
            if res.status_code == 200:
                count += 1
        except Exception:
            continue
            
    return {"status": "success", "sent_to_users": count}
