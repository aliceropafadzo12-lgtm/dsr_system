from flask import Flask, render_template, request, redirect, session
import sqlite3
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'secret123'

# ===== FILE UPLOAD CONFIG =====
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'pdf'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# ===== LOGIN =====
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
        user = cursor.fetchone()

        conn.close()

        if user:
            session['user'] = username
            return redirect('/')
        else:
            return "Invalid credentials"

    return render_template('login.html')


# ===== LOGOUT =====
@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect('/login')


# ===== HOME =====
@app.route('/')
def home():
    if 'user' not in session:
        return redirect('/login')
    return render_template('index.html')

# ===== ADD SALES =====
@app.route('/add-sales', methods=['GET', 'POST'])
def add_sales():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    if request.method == 'POST':
        branch = request.form['branch']
        date = request.form['date']
        cash = float(request.form['cash'])
        swipe = float(request.form['swipe'])
        mobile = float(request.form['mobile'])

        total = cash + swipe + mobile

        cursor.execute('''
        INSERT INTO sales (branch, date, cash, swipe, mobile, total)
        VALUES (?, ?, ?, ?, ?, ?)
        ''', (branch, date, cash, swipe, mobile, total))

        conn.commit()

    cursor.execute("SELECT name FROM branches")
    branches = cursor.fetchall()

    conn.close()

    return render_template('add_sales.html', branches=branches)

# ===== DASHBOARD =====
@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect('/login')

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    cursor.execute("SELECT SUM(total) FROM sales")
    total_sales = cursor.fetchone()[0] or 0

    cursor.execute("SELECT COUNT(*) FROM sales")
    total_transactions = cursor.fetchone()[0]

    cursor.execute("SELECT SUM(variance) FROM reconciliation")
    total_variance = cursor.fetchone()[0] or 0

    cursor.execute("SELECT branch, SUM(total) FROM sales GROUP BY branch")
    branch_data = cursor.fetchall()

    conn.close()

    return render_template(
        'dashboard.html',
        total_sales=total_sales,
        total_transactions=total_transactions,
        total_variance=total_variance,
        branch_data=branch_data
    )

# ===== REPORT =====
@app.route('/report')
def report():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM sales")
    data = cursor.fetchall()

    conn.close()

    return render_template('report.html', sales=data)

# ===== RECONCILE =====
@app.route('/reconcile', methods=['GET', 'POST'])
def reconcile():
    result = None

    if request.method == 'POST':
        date = request.form['date']
        expected = float(request.form['expected'])
        actual_amount = float(request.form['actual_amount'])

        file = request.files['actual_pdf']

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
        else:
            return "Upload a valid PDF file"

        variance = actual_amount - expected

        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()

        cursor.execute('''
        INSERT INTO reconciliation (date, expected, actual, variance)
        VALUES (?, ?, ?, ?)
        ''', (date, expected, filepath, variance))

        conn.commit()
        conn.close()

        result = variance

    return render_template('reconcile.html', result=result)


# ===== RECONCILE REPORT =====
@app.route('/reconcile-report')
def reconcile_report():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    # Get file path first (so we can delete the PDF too)
    cursor.execute("SELECT actual FROM reconciliation WHERE id=?", (id,))
    file = cursor.fetchone()

    if file:
        filepath = file[0]
        if filepath and os.path.exists(filepath):
            os.remove(filepath)

    # Delete record
    cursor.execute("DELETE FROM reconciliation WHERE id=?", (id,))
    conn.commit()
    conn.close()

    return redirect('/reconcile-report')


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)