from flask import Flask, redirect, render_template, session, request
from flask_session import Session
import sqlite3, random, re, werkzeug.security, datetime, requests

# Initialize application
app = Flask(__name__)

# Define constants
USER_TYPES = ['admin', 'user']
OMDB_API = "d220b5ff"

# Configure session cookies 
app.secret_key = random.randbytes(8)
app.config['SESSION_TYPE'] = "filesystem"
app.config['SESSION_PERMANENT'] = False
Session(app)

@app.template_filter('limit')
def limit(description):
    if len(description) > 400:
        return description[:401] + "..."
    return description

@app.route("/", methods=['GET'])
def index():
    if session.get("user_id"):
        offset = 0
        conn = sqlite3.connect("wwmt.db")
        curr = conn.cursor()
        record = curr.execute("SELECT * FROM users WHERE id=?", (session.get("user_id"),)).fetchone()
        if not record:
            session.clear()
            return render_template("error.html", error="Invalid user ID. Please log in again.")
        # Get user type and username
        user = record[4]
        username = record[1]
        # Define offset
        offset = 0
        if request.args.get("page"):
            try:
                page = int(request.args.get("page"))
            except ValueError:
                page = 0
            if page < 0:
                page = 0
            offset = 10 * page
        movies = curr.execute("SELECT * FROM movies LIMIT 10 OFFSET ?", (offset,)).fetchall()
        
        return render_template("home.html", user=user, username=username, movies=movies)
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
    # If user is not logged in, redirect
    if session.get("user_id"):
        return redirect("/")
    if request.method == "POST":
        # Check for invalid input
        if '' in [request.form.get(field) for field in request.form]:
            return render_template("error.html", error="Invalid input. ")
        if not re.match(r"^[\w\-\.]+@([\w-]+\.)+[\w-]{2,}$", request.form.get("email")):
            return render_template("error.html", error="Invalid email. ")
        # Connect to database
        conn = sqlite3.connect("./wwmt.db")
        curr = conn.cursor()
        # Check if user exists
        records = curr.execute("SELECT * FROM users WHERE email=?", (request.form.get("email"),)).fetchall()
        if len(records) == 0:
            return render_template("error.html", error='Email not registered. ')
        # Check password validity
        password = records[0][3]
        if not werkzeug.security.check_password_hash(password, request.form.get("password")):
            return render_template("error.html", error="Incorrect password. ")
        session['user_id'] = records[0][0]
        return redirect("/")
        conn.commit()
        conn.close()
    else:
        return render_template("login.html")
