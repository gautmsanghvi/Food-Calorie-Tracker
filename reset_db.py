import sqlite3
import os
from werkzeug.security import generate_password_hash

DB_FILE = 'food_tracker.db'

# 🚫 Delete the old database if it exists
if os.path.exists(DB_FILE):
    os.remove(DB_FILE)
    print(f"✅ Deleted old database: {DB_FILE}")

# 📦 Connect to the new database
conn = sqlite3.connect(DB_FILE)
c = conn.cursor()

# 👤 Create users table
c.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        password TEXT NOT NULL
    )
''')

# 🍽️ Create food_logs table with correct schema
c.execute('''
    CREATE TABLE IF NOT EXISTS food_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        date TEXT,
        food_name TEXT,
        protein REAL,
        fat REAL,
        carbs REAL,
        calories REAL,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )
''')

# 👨‍🔬 Insert a test user for login testing
username = 'testuser'
password = generate_password_hash('testpass')

try:
    c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
    print("✅ Test user added: testuser / testpass")
except sqlite3.IntegrityError:
    print("ℹ️ Test user already exists.")

# ✅ Commit and close connection
conn.commit()
conn.close()

print("✅ New database initialized successfully.")
