from flask import Flask, redirect, render_template, session, request
from flask_session import Session
import sqlite3, random, re, werkzeug.security

# Initialize application
app = Flask(__name__)

# Define constants
USER_TYPES = ['admin', 'user']

# Configure session cookies 
app.secret_key = random.randbytes(8)
app.config['SESSION_TYPE'] = "filesystem"
app.config['SESSION_PERMANENT'] = False
Session(app)

@app.route("/")
def index():
    if session.get("user_id"):
        conn = sqlite3.connect("wwmt.db")
        curr = conn.cursor()
        record = curr.execute("SELECT * FROM users WHERE id=?", (session.get("user_id"),)).fetchone()
        user = record[4]
        username = record[1]
        return render_template("home.html", user=user, username=username)
    else:
        return render_template("landing_page.html")

@app.route("/register", methods=["POST", "GET"])
def register():
    if session.get("user_id"):
        return redirect("/")
    if request.method == "POST":
        # Ensure all fields are filled
        if '' in [request.form.get(field) for field in request.form]:
            return render_template("error.html", error='Error: Invalid input. ')
        # Ensure email is valid
        if not re.match(r'^[\w\-\.]+@([\w-]+\.)+[\w-]{2,}$', request.form.get("email")):
            return render_template("error.html", error="Error: Invalid email. ")
        if not request.form.get("account") in USER_TYPES:
            return render_template("error.html", error="Error: Invalid account type. ")
        # Connect to database and check if user already exists
        conn = sqlite3.connect("./wwmt.db")
        curr = conn.cursor()
        username_check = curr.execute("SELECT * FROM users WHERE username = ?", (request.form.get("username"),)).fetchall()
        email_check = curr.execute("SELECT * FROM users WHERE email = ?", (request.form.get("email"),)).fetchall()
        if len(username_check) != 0 or len(email_check) != 0:
            return render_template("error.html", error="An user with the same email / password already exists.")
        else:
            # Hash the password and insert the new user into the database
            hsh = werkzeug.security.generate_password_hash(request.form.get("password"))
            curr.execute("INSERT INTO users (username, email, password, account) VALUES (?, ?, ?, ?)", (request.form.get("username"), request.form.get("email"), hsh, request.form.get("account"),))
        # Set the user_id in the session and redirect to the home page
        session['user_id'] = curr.execute("SELECT id FROM users WHERE username = ?", (request.form.get("username"),)).fetchall()[0][0]
        conn.commit()
        conn.close()
        return redirect("/")
    else:
        return render_template("register.html")

@app.route("/login", methods=["POST", "GET"])
def login():
    if session.get("user_id"):
        return redirect("/")
    if request.method == "POST":
        if '' in [request.form.get(field) for field in request.form]:
            return render_template("error.html", error="Invalid input. ")
        if not re.match(r"^[\w\-\.]+@([\w-]+\.)+[\w-]{2,}$", request.form.get("email")):
            return render_template("error.html", error="Invalid email. ")
        conn = sqlite3.connect("./wwmt.db")
        curr = conn.cursor()
        records = curr.execute("SELECT * FROM users WHERE email=?", (request.form.get("email"),)).fetchall()
        if len(records) == 0:
            return render_template("error.html", error='Email not registered. ')
        password = records[0][3]
        if not werkzeug.security.check_password_hash(password, request.form.get("password")):
            return render_template("error.html", error="Incorrect password. ")
        session['user_id'] = records[0][0]
        return redirect("/")
        conn.commit()
        conn.close()
    else:
        return render_template("login.html")
