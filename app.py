from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import psycopg2
from datetime import datetime
from collections import defaultdict
from itsdangerous import URLSafeTimedSerializer as Serializer

app = Flask(__name__)
app.secret_key = 'supersecretkey2025'  # Replace this in production!

# PostgreSQL connection
conn = psycopg2.connect(
    host="localhost",
    database="income_data",
    user="postgres",
    password="Postgres2025"
)

cur = conn.cursor()

# Create tables if they don't exist
cur.execute("""
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL
);
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS income_data (
    id SERIAL PRIMARY KEY,
    date DATE,
    income NUMERIC,
    hours_worked NUMERIC,
    user_id INTEGER REFERENCES users(id)
);
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS expense_data (
    id SERIAL PRIMARY KEY,
    date DATE,
    category TEXT,
    description TEXT,
    amount NUMERIC,
    payment_method TEXT,
    user_id INTEGER REFERENCES users(id)
);
""")

conn.commit()

# --- Decorator to require login ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# --- Password Reset Logic ---
SECRET_KEY = "supersecretkey2025"
serializer = Serializer(SECRET_KEY, salt="reset-password")

def generate_reset_token(username):
    return serializer.dumps(username)

def verify_reset_token(token, expiration=3600):
    try:
        username = serializer.loads(token, max_age=expiration)
    except Exception:
        return None
    return username

# --- ROUTES ---

@app.route('/')
def home():
    return redirect(url_for('form'))  # All roads lead to form (if logged in)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = generate_password_hash(request.form['password'])

        try:
            cur.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (username, password))
            conn.commit()
            return redirect(url_for('login'))
        except psycopg2.errors.UniqueViolation:
            conn.rollback()
            return "Username already exists!"

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        cur.execute("SELECT id, password FROM users WHERE username = %s", (username,))
        user = cur.fetchone()

        if user and check_password_hash(user[1], password):
            session['user_id'] = user[0]
            session['username'] = username
            return redirect(url_for('form'))
        else:
            error = "Invalid username or password!"  # Error message for invalid credentials
            return render_template('login.html', error=error)  # Pass error message to the template

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/form')
@login_required
def form():
    return render_template('form.html', username=session['username'])

@app.route('/submit', methods=['POST'])
@login_required
def submit():
    date = request.form['date']
    income = float(request.form['income'])
    hours = float(request.form['hours'])

    user_id = session['user_id']
    cur.execute("INSERT INTO income_data (date, income, hours_worked, user_id) VALUES (%s, %s, %s, %s)",
                (date, income, hours, user_id))
    conn.commit()

    return redirect(url_for('dashboard'))

@app.route('/add_expense', methods=['POST'])
@login_required
def add_expense():
    date = request.form['date']
    category = request.form['category']
    description = request.form['description']
    amount = float(request.form['amount'])
    payment_method = request.form['payment_method']

    user_id = session['user_id']
    cur.execute("""
        INSERT INTO expense_data (date, category, description, amount, payment_method, user_id)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (date, category, description, amount, payment_method, user_id))
    conn.commit()

    return redirect(url_for('dashboard'))

@app.route('/dashboard')
@login_required
def dashboard():
    user_id = session['user_id']
    cur.execute("SELECT date, income, hours_worked FROM income_data WHERE user_id = %s ORDER BY date ASC", (user_id,))
    income_rows = cur.fetchall()

    cur.execute("SELECT date, category, description, amount, payment_method FROM expense_data WHERE user_id = %s ORDER BY date ASC", (user_id,))
    expense_rows = cur.fetchall()

    income_by_week = defaultdict(float)
    income_by_fortnight = defaultdict(float)
    income_by_month = defaultdict(float)
    total_income = 0
    total_hours = 0

    for date, income, hours in income_rows:
        week = date.strftime('%Y-W%U')
        fortnight = f"{date.strftime('%Y')}-F{(date.day - 1) // 14 + 1}"
        month = date.strftime('%Y-%m')

        income_by_week[week] += float(income)
        income_by_fortnight[fortnight] += float(income)
        income_by_month[month] += float(income)

        total_income += float(income)
        total_hours += float(hours)

    avg_hourly_rate = round(total_income / total_hours, 2) if total_hours else 0

    expenses_by_category = defaultdict(float)
    total_expenses = 0

    for date, category, description, amount, payment_method in expense_rows:
        expenses_by_category[category] += float(amount)
        total_expenses += float(amount)

    return render_template('dashboard.html',
                           username=session['username'],
                           income_by_week=income_by_week,
                           income_by_fortnight=income_by_fortnight,
                           income_by_month=income_by_month,
                           avg_hourly_rate=avg_hourly_rate,
                           expenses_by_category=expenses_by_category,
                           total_income=total_income,
                           total_expenses=total_expenses,
                           total_hours=total_hours)

# Forgot Password Route
@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        username = request.form['username']
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cur.fetchone()
        cur.close()

        if user:
            token = generate_reset_token(username)
            reset_link = url_for('reset_password', token=token, _external=True)
            print(f"Send this reset link: {reset_link}")  # In a real app, email it to the user
            flash("Reset link has been sent (check console in dev mode).", "info")
        else:
            flash("Username not found.", "danger")
    return render_template("forgot_password.html")

# Reset Password Route
@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    username = verify_reset_token(token)
    if not username:
        flash("Invalid or expired token.", "danger")
        return redirect(url_for("login"))

    if request.method == 'POST':
        new_password = request.form['password']
        hashed = generate_password_hash(new_password)

        # Update password in the database
        cur = conn.cursor()
        cur.execute("UPDATE users SET password = %s WHERE username = %s", (hashed, username))
        conn.commit()
        cur.close()

        flash("Password reset successful. Please login.", "success")
        return redirect(url_for("login"))

    return render_template("reset_password.html")

if __name__ == '__main__':
    app.run(debug=True)