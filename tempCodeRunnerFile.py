from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
import pandas as pd
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'supersecretkey'

# Load food data
food_df = None
def load_food_data():
    global food_df
    try:
        food_df = pd.read_csv("static/food_data.csv")
        if 'Name' not in food_df.columns:
            print("❌ ERROR: 'Name' column missing in food_data.csv!")
            food_df = None
    except Exception as e:
        print("Error loading food_data.csv:", e)
        food_df = None
load_food_data()

# Initialize database
def init_db():
    conn = sqlite3.connect("food_tracker.db")
    c = conn.cursor()

    # Drop food_logs table if it already exists
    c.execute("DROP TABLE IF EXISTS food_logs")

    # Recreate both tables
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        password TEXT NOT NULL)''')

    c.execute('''CREATE TABLE IF NOT EXISTS food_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        date TEXT,
        food_name TEXT,
        protein REAL,
        fat REAL,
        carbs REAL,
        calories REAL,
        FOREIGN KEY(user_id) REFERENCES users(id))''')

    conn.commit()
    conn.close()


@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['login_username']
        password = request.form['login_password']

        conn = sqlite3.connect("food_tracker.db")
        c = conn.cursor()
        c.execute("SELECT id, password FROM users WHERE username = ?", (username,))
        user = c.fetchone()
        conn.close()

        if user and check_password_hash(user[1], password):
            session['user_id'] = user[0]
            session['username'] = username
            return redirect(url_for('index'))
        else:
            flash('Invalid credentials', 'danger')
            return redirect(url_for('login'))
    return render_template('login.html')

@app.route('/register', methods=['POST'])
def register():
    username = request.form['register_username']
    password = generate_password_hash(request.form['register_password'])

    conn = sqlite3.connect("food_tracker.db")
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
        conn.commit()
        flash('Registration successful! Please login.', 'success')
    except sqlite3.IntegrityError:
        flash('Username already exists!', 'danger')
    conn.close()
    return redirect(url_for('login'))

@app.route('/logout')
def logout():
    session.clear()
    flash("Logged out successfully.", "info")
    return redirect(url_for('login'))

@app.route('/index', methods=['GET', 'POST'])
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    bmi_result = None
    bmi_status = None
    today = datetime.now().strftime('%Y-%m-%d')

    conn = sqlite3.connect("food_tracker.db")
    c = conn.cursor()

    if request.method == 'POST':
        if 'food_name' in request.form:
            food_name = request.form['food_name']
            date = request.form['date']

            food_data = food_df[food_df['Name'] == food_name].iloc[0]
            protein = food_data['Protein']
            fat = food_data['Fat']
            carbs = food_data['Carbs']
            calories = food_data['Calories']

            c.execute('''INSERT INTO food_logs (user_id, date, food_name, protein, fat, carbs, calories)
                         VALUES (?, ?, ?, ?, ?, ?, ?)''',
                      (session['user_id'], date, food_name, protein, fat, carbs, calories))
            conn.commit()

        elif 'weight' in request.form and 'height' in request.form:
            weight = float(request.form['weight'])
            height = float(request.form['height']) / 100
            bmi = round(weight / (height ** 2), 2)
            bmi_result = bmi
            if bmi < 18.5:
                bmi_status = "Underweight"
            elif 18.5 <= bmi < 24.9:
                bmi_status = "Normal"
            elif 25 <= bmi < 29.9:
                bmi_status = "Overweight"
            else:
                bmi_status = "Obese"

    c.execute("SELECT * FROM food_logs WHERE user_id = ?", (session['user_id'],))
    foods = c.fetchall()
    conn.close()

    food_items = food_df['Name'].tolist() if food_df is not None else []
    return render_template('index.html', foods=foods, food_items=food_items, bmi_result=bmi_result,
                           bmi_status=bmi_status, date=today, username=session['username'])

@app.route('/daily_food', methods=['GET', 'POST'])
def daily_food():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect("food_tracker.db")
    c = conn.cursor()
    c.execute("SELECT * FROM food_logs WHERE user_id = ?", (session['user_id'],))
    foods = c.fetchall()
    conn.close()
    return render_template('daily_food.html', foods=foods)

@app.route('/delete/<int:food_id>', methods=['POST'])
def delete(food_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect("food_tracker.db")
    c = conn.cursor()
    c.execute("DELETE FROM food_logs WHERE id = ? AND user_id = ?", (food_id, session['user_id']))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
