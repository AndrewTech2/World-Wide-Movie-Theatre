from functools import wraps
from dotenv import load_dotenv
import os
from flask import Flask, redirect, render_template, session, request
from flask_session import Session
import sqlite3, re, werkzeug.security, datetime, requests, smtplib, ssl

# Initialize application
app = Flask(__name__)

# Define constants
USER_TYPES = ['admin', 'user']
load_dotenv()
OMDB_API = os.getenv("OMDB_API")
APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
GMAIL_PASSWORD = os.getenv("GMAIL_PASSWORD")

# Configure session cookies 
app.secret_key = b'\xc7\xf8E\x8a\xa4\xb7\xa4\x90'
app.config['SESSION_TYPE'] = "filesystem"
app.config['SESSION_PERMANENT'] = False
Session(app)

def admin_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        user_id = session.get('user_id')
        if not user_id:
            return redirect("/")

        with sqlite3.connect("wwmt.db") as conn:
            record = conn.execute(
                "SELECT account FROM users WHERE id=?", (user_id,)
            ).fetchone()

        if not record or record[0] != "admin":
            return redirect("/")
        return func(*args, **kwargs)

    return wrapper

def login_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not session.get("user_id"):
            return redirect("/")
        return func(*args, **kwargs)

    return wrapper

def get_credentials(id):
    """ Returns the user type and the username of user with specified ID. """
    conn = sqlite3.connect("wwmt.db")
    curr = conn.cursor()
    record = curr.execute("SELECT * FROM users WHERE id=?", (id,)).fetchone()
    if not record:
        return None
    return (record[4], record[1])

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
        credentials = get_credentials(session.get('user_id'))
        if not credentials:
            return redirect("/")
        user = credentials[0]
        username = credentials[1]
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
        
        return render_template("movies.html", user=user, username=username, movies=movies, title="Home")
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
            return render_template("error.html", error="A user with the same email / user already exists.")
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
    # If user is logged in, redirect
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
        conn.commit()
        conn.close()
        return redirect("/")
    else:
        return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    session.clear()
    return redirect('/')

@app.route("/add", methods=['GET', 'POST'])
@login_required
@admin_required
def add():
    # Get user credentials
    credentials = get_credentials(session.get('user_id'))
    if not credentials:
        return redirect("/")
    user = credentials[0]
    username = credentials[1]
    if request.method == "POST":
        if '' in [request.form.get(field) for field in request.form]:
            return render_template("error.html", error="Invalid input.", login=True, user=user, username=username)
        # Use OMDb API to get movie details
        response = requests.get("http://www.omdbapi.com", params={'apikey': OMDB_API, 's': request.form.get("title"), 'type': 'movie'})
        # If GET request is unsuccessful, return error
        if response.status_code != 200:
            return render_template("error.html", error="Error using external API server. Please try again later.", login=True, user=user, username=username)
        # Convert the response to a json format
        response_dict = response.json()
        # If no movies have been found, return error
        if response_dict['Response'] == "False":
            return render_template("error.html", error="Movie does not exist!", login=True, user=user, username=username)
        movies = response_dict['Search']
        # Display results
        return render_template("movies.html", user=user, username=username, movies=movies, title="Add")
    else:
        return render_template("add.html", user=user, username=username)

@login_required
@admin_required
@app.route("/add_movie", methods=['POST'])
def add_movie():
    # Get user credentials
    credentials = get_credentials(session.get('user_id'))
    if not credentials:
        return redirect("/")
    user = credentials[0]
    username = credentials[1]
    if not request.form.get("imdb_id"):
        return render_template("error.html", error="No ID supplied.", login=True, user=user, username=username)
    response = requests.get("http://www.omdbapi.com", params={"apikey": OMDB_API, 'i': request.form.get("imdb_id"), 'type': 'movie'})
    if response.status_code != 200:
        return render_template("error.html", error="External API service currently unavailable. Please try again later.", login=True, user=user, username=username)
    response_text = response.json()
    if response_text['Response'] == "False":
        return render_template("error.html", error="Invalid IMDb ID.", login=True, user=user, username=username)
    conn = sqlite3.connect("wwmt.db")
    curr = conn.cursor()
    # Insert new movie details into database
    record = curr.execute("SELECT * FROM movies WHERE imdb_id=?", (request.form.get("imdb_id"),)).fetchone()
    if record:
        return render_template("error.html", error=f"Movie already exists!", login=True, user=user, username=username)
    curr.execute("INSERT INTO movies (title, overview, poster, rating, age_rating, director, release, genre, imdb_id) VALUES (?,?,?,?,?,?,?,?,?)", (response_text['Title'], response_text['Plot'], response_text['Poster'], int(float(response_text['Ratings'][0]['Value'].split("/")[0])), response_text['Rated'], response_text['Director'], response_text['Released'], response_text['Genre'], response_text['imdbID'],))
    wwmt_id = curr.execute("SELECT * FROM movies WHERE imdb_id=?", (response_text['imdbID'],)).fetchone()[0]
    conn.commit()
    conn.close()
    return redirect(f"/movie?id={wwmt_id}")

@login_required
@admin_required
@app.route("/showtimes", methods=['GET', 'POST'])
def showtimes():
    # Get user credentials
    credentials = get_credentials(session.get('user_id'))
    if not credentials:
        return redirect("/")
    user = credentials[0]
    username = credentials[1]
    if request.method == "POST":
        # Validate the submitted showtime before writing it to the database.
        if '' in [request.form.get(field) for field in request.form]:
            return render_template("error.html", error="Please fill out all fields.", user=user, username=username, login=True)
        if "T" not in request.form.get("datetime"):
            return render_template("error.html", error="Error whilst processing datetime field.", user=user, username=username, login=True)
        today = datetime.datetime.now()
        try:
            datetime_input = datetime.datetime.strptime(request.form.get("datetime").replace("T", " "), "%Y-%m-%d %H:%M")
        except:
            return render_template("error.html", error="Error whilst processing datetime field.", user=user, username=username, login=True)
        if today > datetime_input:
            return render_template("error.html", error="Please ensure the movie runs in the future.", user=user, username=username, login=True)
        conn = sqlite3.connect("wwmt.db")
        curr = conn.cursor()
        # Confirm that the selected movie exists before creating its showtime.
        record = curr.execute("SELECT * FROM movies WHERE id=?", (request.form.get("movie_id"),)).fetchone()
        if not record:
            return render_template("error.html", error="Movie does not exist!", user=user, username=username, login=True)
        runtime = datetime.datetime.strftime(datetime_input, "%Y-%m-%d %H:%M:00")
        # Store the new showtime and redirect to its detail page.
        curr.execute("INSERT INTO showtimes (movie_id, user_id, runtime, location) VALUES (?, ?, ?, ?)", (request.form.get("movie_id"), session.get("user_id"), runtime, request.form.get("location"),))
        showtime_id = curr.execute("SELECT * FROM showtimes WHERE user_id=? ORDER BY id DESC", (session.get('user_id'),)).fetchall()[0][0]
        conn.commit()
        conn.close()
        return redirect(f'/showtime?id={showtime_id}')
    else:
        # Load the signed-in user's showtimes together with their movie details.
        conn = sqlite3.connect("wwmt.db")
        curr = conn.cursor()
        all_showtimes = curr.execute("SELECT * FROM showtimes, movies WHERE showtimes.user_id=? AND movie_id = movies.id ORDER BY showtimes.id DESC", (session.get("user_id"),)).fetchall()
        conn.commit()
        conn.close()
        return render_template("showtimes.html", user=user, username=username, all_showtimes=all_showtimes)

@login_required
@app.route("/change_password", methods=['GET', 'POST'])
def reset_password():
    # Get user credentials
    conn = sqlite3.connect("wwmt.db")
    curr = conn.cursor()
    credentials = get_credentials(session.get('user_id'))
    if not credentials:
        return redirect("/")
    user = credentials[0]
    username = credentials[1]
    if request.method == "POST":
        if '' in [request.form.get(field) for field in request.form]:
            return render_template("error.html", error="Please fill out all forms.", user=user, username=username, login=True)
        old_password = request.form.get("old")
        if request.form.get("new") != request.form.get("confirmation"):
            return render_template("error.html", error="Passwords do not match.", user=user, username=username, login=True)
        hsh = curr.execute("SELECT * FROM users WHERE id=?", (session.get("user_id"),)).fetchone()[3]
        if not werkzeug.security.check_password_hash(hsh, old_password):
            return render_template("error.html", error="Incorrect password.", user=user, username=username, login=True)
        new_hsh = werkzeug.security.generate_password_hash(request.form.get("new"))
        curr.execute("UPDATE users SET password=? WHERE id=?", (new_hsh, session.get("user_id"),))
        conn.commit()
        conn.close()
        return render_template("success.html", user=user, username=username, login=True, message="Password changed!")
    else:
        return render_template("change_password.html", user=user, username=username)
