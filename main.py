from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sqlite3
import time

app = FastAPI()

# Frontend (Mini App) কানেক্ট করার জন্য CORS অনুমতি
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database Initialization
def init_db():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            balance REAL DEFAULT 0.0,
            mining_speed REAL DEFAULT 1.0,
            last_updated INTEGER,
            referred_by INTEGER
        )
    ''')
    conn.commit()
    conn.close()

init_db()

class UserRegister(BaseModel):
    user_id: int
    username: str = ""
    referrer_id: int = None

@app.post("/api/user/sync")
def sync_user(data: UserRegister):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    current_time = int(time.time())
    
    cursor.execute("SELECT balance, mining_speed, last_updated FROM users WHERE user_id = ?", (data.user_id,))
    user = cursor.fetchone()
    
    if user:
        # পুরনো ইউজার: সময় অনুযায়ী পয়েন্ট আপডেট
        old_balance, speed, last_updated = user
        elapsed_hours = (current_time - last_updated) / 3600.0
        new_balance = old_balance + (speed * elapsed_hours)
        
        cursor.execute("UPDATE users SET balance = ?, last_updated = ? WHERE user_id = ?", 
                       (new_balance, current_time, data.user_id))
    else:
        # নতুন ইউজার
        speed = 1.0
        # রেফার করে থাকলে রিকম্যান্ডেড ইউজারকে +১০% স্পিড বোনাস
        if data.referrer_id and data.referrer_id != data.user_id:
            cursor.execute("UPDATE users SET mining_speed = mining_speed + 0.10 WHERE user_id = ?", (data.referrer_id,))
            
        cursor.execute("INSERT INTO users (user_id, username, balance, mining_speed, last_updated, referred_by) VALUES (?, ?, ?, ?, ?, ?)",
                       (data.user_id, data.username, 0.0, speed, current_time, data.referrer_id))
        new_balance = 0.0
        
    conn.commit()
    conn.close()
    
    return {
        "status": "success",
        "user_id": data.user_id,
        "balance": round(new_balance, 4),
        "mining_speed": speed
    }