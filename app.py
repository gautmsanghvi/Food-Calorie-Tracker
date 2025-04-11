<<<<<<< HEAD
from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
import pandas as pd
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import struct

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
        else:
            food_df['Protein'] = pd.to_numeric(food_df['Protein'], errors='coerce').fillna(0)
            food_df['Fat'] = pd.to_numeric(food_df['Fat'], errors='coerce').fillna(0)
            food_df['Carbs'] = pd.to_numeric(food_df['Carbs'], errors='coerce').fillna(0)
            food_df['Calories'] = pd.to_numeric(food_df['Calories'], errors='coerce').fillna(0)
    except Exception as e:
        print("Error loading food_data.csv:", e)
        food_df = None

load_food_data()

# Initialize database
def init_db():
    conn = sqlite3.connect("food_tracker.db")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        password TEXT NOT NULL)''')

    # Add quantity column if not exists
    c.execute("PRAGMA table_info(food_logs)")
    columns = [col[1] for col in c.fetchall()]
    if 'quantity' not in columns:
        c.execute("ALTER TABLE food_logs ADD COLUMN quantity REAL DEFAULT 100")

    c.execute('''CREATE TABLE IF NOT EXISTS food_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        date TEXT,
        food_name TEXT,
        protein REAL,
        fat REAL,
        carbs REAL,
        calories REAL,
        quantity REAL DEFAULT 100,
        FOREIGN KEY(user_id) REFERENCES users(id))''')
    conn.commit()
    conn.close()

init_db()

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
    bmi_recommendation = None
    today = datetime.now().strftime('%Y-%m-%d')

    conn = sqlite3.connect("food_tracker.db")
    c = conn.cursor()

    if request.method == 'POST':
        if 'submit_food' in request.form:
            food_name = request.form['food_name']
            date = request.form['date']

            try:
                match = food_df[food_df['Name'] == food_name]
                if not match.empty:
                    food_data = match.iloc[0]
                    protein = float(food_data.get('Protein', 0))
                    fat = float(food_data.get('Fat', 0))
                    carbs = float(food_data.get('Carbs', 0))
                    calories = float(food_data.get('Calories', 0))

                    c.execute('''INSERT INTO food_logs (user_id, date, food_name, protein, fat, carbs, calories)
                                 VALUES (?, ?, ?, ?, ?, ?, ?)''',
                              (session['user_id'], date, food_name, protein, fat, carbs, calories))
                    conn.commit()
                    flash(f"{food_name} added successfully!", "success")
                else:
                    flash("Selected food not found in dataset.", "danger")
            except Exception as e:
                flash(f"Error adding food: {e}", "danger")

        elif 'weight' in request.form and 'height' in request.form:
            try:
                weight = float(request.form['weight'])
                height = float(request.form['height']) / 100
                bmi = round(weight / (height ** 2), 2)
                bmi_result = bmi
                if bmi < 18.5:
                    bmi_status = "Underweight"
                    bmi_recommendation = "You should focus on gaining weight with a healthy, calorie-rich diet. 🥗"
                elif 18.5 <= bmi < 25:
                    bmi_status = "Normal"
                    bmi_recommendation = "You're in a healthy range. Maintain your current eating and exercise habits! 💪"
                elif 25 <= bmi < 30:
                    bmi_status = "Overweight"
                    bmi_recommendation = "Try reducing calorie intake and increasing physical activity. 🚶‍♂️"
                else:
                    bmi_status = "Obese"
                    bmi_recommendation = "Consider consulting a nutritionist for a structured weight loss plan. ❤️"
            except Exception as e:
                flash(f"Invalid input for BMI: {e}", "danger")

    c.execute("SELECT * FROM food_logs WHERE user_id = ? AND date = ?", (session['user_id'], today))
    foods = c.fetchall()
    conn.close()

    total_protein = total_fat = total_carbs = total_calories = 0
    cleaned_foods = []

    for food in foods:
        food = list(food)
        try:
            for i in range(4, 8):
                if isinstance(food[i], bytes):
                    food[i] = struct.unpack('<d', food[i])[0]
                food[i] = float(food[i])
        except Exception as e:
            flash(f"Error processing food data: {e}", "danger")
            food[4:8] = [0, 0, 0, 0]
        total_protein += food[4]
        total_fat += food[5]
        total_carbs += food[6]
        total_calories += food[7]
        cleaned_foods.append(food)

    food_items = food_df['Name'].tolist() if food_df is not None else []

    return render_template('index.html',
                           foods=cleaned_foods,
                           food_items=food_items,
                           bmi_result=bmi_result,
                           bmi_status=bmi_status,
                           bmi_recommendation=bmi_recommendation,
                           date=today,
                           username=session['username'],
                           total_protein=total_protein,
                           total_fat=total_fat,
                           total_carbs=total_carbs,
                           total_calories=total_calories)


    total_protein = total_fat = total_carbs = total_calories = 0
    cleaned_foods = []

    for food in foods:
        food = list(food)
        try:
            for i in range(4, 8):
                if isinstance(food[i], bytes):
                    food[i] = struct.unpack('<d', food[i])[0]
                food[i] = float(food[i])
            quantity = float(food[8])
        except Exception as e:
            flash(f"Error processing food data: {e}", "danger")
            food[4:8] = [0, 0, 0, 0]
            quantity = 0
        total_protein += food[4]
        total_fat += food[5]
        total_carbs += food[6]
        total_calories += food[7]
        cleaned_foods.append(food + [quantity])

    food_items = food_df['Name'].tolist() if food_df is not None else []
    return render_template('index.html', foods=cleaned_foods, food_items=food_items, bmi_result=bmi_result,
                           bmi_status=bmi_status, date=today, username=session['username'],
                           total_protein=total_protein, total_fat=total_fat,
                           total_carbs=total_carbs, total_calories=total_calories)

@app.route('/daily_food')
def daily_food():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect("food_tracker.db")
    c = conn.cursor()
    c.execute("SELECT * FROM food_logs WHERE user_id = ?", (session['user_id'],))
    foods = c.fetchall()
    conn.close()

    total_protein = total_fat = total_carbs = total_calories = 0
    cleaned_foods = []

    for food in foods:
        food = list(food)
        try:
            for i in range(4, 8):
                if isinstance(food[i], bytes):
                    food[i] = struct.unpack('<d', food[i])[0]
                food[i] = float(food[i])
            quantity = float(food[8])
        except:
            food[4:8] = [0, 0, 0, 0]
            quantity = 0
        total_protein += food[4]
        total_fat += food[5]
        total_carbs += food[6]
        total_calories += food[7]
        cleaned_foods.append(food + [quantity])

    return render_template('daily_food.html', foods=cleaned_foods,
                           total_protein=total_protein, total_fat=total_fat,
                           total_carbs=total_carbs, total_calories=total_calories)

@app.route('/delete/<int:food_id>', methods=['POST'])
def delete(food_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect("food_tracker.db")
    c = conn.cursor()
    c.execute("DELETE FROM food_logs WHERE id = ? AND user_id = ?", (food_id, session['user_id']))
    conn.commit()
    conn.close()
    flash("Food item deleted.", "info")
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
=======
from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
import pandas as pd
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import struct

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
        else:
            food_df['Protein'] = pd.to_numeric(food_df['Protein'], errors='coerce').fillna(0)
            food_df['Fat'] = pd.to_numeric(food_df['Fat'], errors='coerce').fillna(0)
            food_df['Carbs'] = pd.to_numeric(food_df['Carbs'], errors='coerce').fillna(0)
            food_df['Calories'] = pd.to_numeric(food_df['Calories'], errors='coerce').fillna(0)
    except Exception as e:
        print("Error loading food_data.csv:", e)
        food_df = None

load_food_data()

# Initialize database
def init_db():
    conn = sqlite3.connect("food_tracker.db")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        password TEXT NOT NULL)''')

    # Add quantity column if not exists
    c.execute("PRAGMA table_info(food_logs)")
    columns = [col[1] for col in c.fetchall()]
    if 'quantity' not in columns:
        c.execute("ALTER TABLE food_logs ADD COLUMN quantity REAL DEFAULT 100")

    c.execute('''CREATE TABLE IF NOT EXISTS food_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        date TEXT,
        food_name TEXT,
        protein REAL,
        fat REAL,
        carbs REAL,
        calories REAL,
        quantity REAL DEFAULT 100,
        FOREIGN KEY(user_id) REFERENCES users(id))''')
    conn.commit()
    conn.close()

init_db()

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
    bmi_recommendation = None
    today = datetime.now().strftime('%Y-%m-%d')

    conn = sqlite3.connect("food_tracker.db")
    c = conn.cursor()

    if request.method == 'POST':
        if 'submit_food' in request.form:
            food_name = request.form['food_name']
            date = request.form['date']

            try:
                match = food_df[food_df['Name'] == food_name]
                if not match.empty:
                    food_data = match.iloc[0]
                    protein = float(food_data.get('Protein', 0))
                    fat = float(food_data.get('Fat', 0))
                    carbs = float(food_data.get('Carbs', 0))
                    calories = float(food_data.get('Calories', 0))

                    c.execute('''INSERT INTO food_logs (user_id, date, food_name, protein, fat, carbs, calories)
                                 VALUES (?, ?, ?, ?, ?, ?, ?)''',
                              (session['user_id'], date, food_name, protein, fat, carbs, calories))
                    conn.commit()
                    flash(f"{food_name} added successfully!", "success")
                else:
                    flash("Selected food not found in dataset.", "danger")
            except Exception as e:
                flash(f"Error adding food: {e}", "danger")

        elif 'weight' in request.form and 'height' in request.form:
            try:
                weight = float(request.form['weight'])
                height = float(request.form['height']) / 100
                bmi = round(weight / (height ** 2), 2)
                bmi_result = bmi
                if bmi < 18.5:
                    bmi_status = "Underweight"
                    bmi_recommendation = "You should focus on gaining weight with a healthy, calorie-rich diet. 🥗"
                elif 18.5 <= bmi < 25:
                    bmi_status = "Normal"
                    bmi_recommendation = "You're in a healthy range. Maintain your current eating and exercise habits! 💪"
                elif 25 <= bmi < 30:
                    bmi_status = "Overweight"
                    bmi_recommendation = "Try reducing calorie intake and increasing physical activity. 🚶‍♂️"
                else:
                    bmi_status = "Obese"
                    bmi_recommendation = "Consider consulting a nutritionist for a structured weight loss plan. ❤️"
            except Exception as e:
                flash(f"Invalid input for BMI: {e}", "danger")

    c.execute("SELECT * FROM food_logs WHERE user_id = ? AND date = ?", (session['user_id'], today))
    foods = c.fetchall()
    conn.close()

    total_protein = total_fat = total_carbs = total_calories = 0
    cleaned_foods = []

    for food in foods:
        food = list(food)
        try:
            for i in range(4, 8):
                if isinstance(food[i], bytes):
                    food[i] = struct.unpack('<d', food[i])[0]
                food[i] = float(food[i])
        except Exception as e:
            flash(f"Error processing food data: {e}", "danger")
            food[4:8] = [0, 0, 0, 0]
        total_protein += food[4]
        total_fat += food[5]
        total_carbs += food[6]
        total_calories += food[7]
        cleaned_foods.append(food)

    food_items = food_df['Name'].tolist() if food_df is not None else []

    return render_template('index.html',
                           foods=cleaned_foods,
                           food_items=food_items,
                           bmi_result=bmi_result,
                           bmi_status=bmi_status,
                           bmi_recommendation=bmi_recommendation,
                           date=today,
                           username=session['username'],
                           total_protein=total_protein,
                           total_fat=total_fat,
                           total_carbs=total_carbs,
                           total_calories=total_calories)


    total_protein = total_fat = total_carbs = total_calories = 0
    cleaned_foods = []

    for food in foods:
        food = list(food)
        try:
            for i in range(4, 8):
                if isinstance(food[i], bytes):
                    food[i] = struct.unpack('<d', food[i])[0]
                food[i] = float(food[i])
            quantity = float(food[8])
        except Exception as e:
            flash(f"Error processing food data: {e}", "danger")
            food[4:8] = [0, 0, 0, 0]
            quantity = 0
        total_protein += food[4]
        total_fat += food[5]
        total_carbs += food[6]
        total_calories += food[7]
        cleaned_foods.append(food + [quantity])

    food_items = food_df['Name'].tolist() if food_df is not None else []
    return render_template('index.html', foods=cleaned_foods, food_items=food_items, bmi_result=bmi_result,
                           bmi_status=bmi_status, date=today, username=session['username'],
                           total_protein=total_protein, total_fat=total_fat,
                           total_carbs=total_carbs, total_calories=total_calories)

@app.route('/daily_food')
def daily_food():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect("food_tracker.db")
    c = conn.cursor()
    c.execute("SELECT * FROM food_logs WHERE user_id = ?", (session['user_id'],))
    foods = c.fetchall()
    conn.close()

    total_protein = total_fat = total_carbs = total_calories = 0
    cleaned_foods = []

    for food in foods:
        food = list(food)
        try:
            for i in range(4, 8):
                if isinstance(food[i], bytes):
                    food[i] = struct.unpack('<d', food[i])[0]
                food[i] = float(food[i])
            quantity = float(food[8])
        except:
            food[4:8] = [0, 0, 0, 0]
            quantity = 0
        total_protein += food[4]
        total_fat += food[5]
        total_carbs += food[6]
        total_calories += food[7]
        cleaned_foods.append(food + [quantity])

    return render_template('daily_food.html', foods=cleaned_foods,
                           total_protein=total_protein, total_fat=total_fat,
                           total_carbs=total_carbs, total_calories=total_calories)

@app.route('/delete/<int:food_id>', methods=['POST'])
def delete(food_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect("food_tracker.db")
    c = conn.cursor()
    c.execute("DELETE FROM food_logs WHERE id = ? AND user_id = ?", (food_id, session['user_id']))
    conn.commit()
    conn.close()
    flash("Food item deleted.", "info")
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
>>>>>>> 95a0c2a087098772523d351c358d844c06bcd256
