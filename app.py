from functools import wraps
from dotenv import load_dotenv
import os
from flask import Flask, redirect, render_template, session, request
from flask_session import Session
from string import ascii_lowercase
import sqlite3, re, werkzeug.security, datetime, requests, smtplib, ssl

# Initialize application
app = Flask(__name__)

# Define constants
USER_TYPES = ['admin', 'user']
load_dotenv()
OMDB_API = os.getenv("OMDB_API")
APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
GMAIL_PASSWORD = os.getenv("GMAIL_PASSWORD")
TICKET_PRICES = {'adult': 15, 'child': 10, 'senior': 10}
TICKET_TYPES = {'adult': 'adults', 'child': 'children', 'senior': 'seniors'}
TICKET_TYPES_PLURAL = {'adults': 'adult', 'children': 'child', 'seniors': 'senior'}

# Configure session cookies 
app.secret_key = b'\xc7\xf8\x8a\xa4\xb7\xa4\x90'
app.config['SESSION_TYPE'] = "filesystem"
app.config['SESSION_PERMANENT'] = False
Session(app)

@app.template_filter("capitalize")
def capitalize(word):
    return word.title()

def valid_showtime(show: list, datetime_idx: int) -> bool:
    """ Returns true if showtime is not past its date. """
    return datetime.datetime.now() < datetime.datetime.strptime(show[datetime_idx], "%Y-%m-%d %H:%M:%S")

def eliminate_invalid_showtimes(showtimes: list, datetime_idx: int) -> list:
    """ Eliminate showtimes which are past their date. """
    print(showtimes)
    new_showtimes = []
    for showtimes_ind in range(len(showtimes)):
        if valid_showtime(showtimes[showtimes_ind], datetime_idx=datetime_idx):
            new_showtimes.append(showtimes[showtimes_ind])
    return new_showtimes

def admin_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        user_id = session.get('user_id')
        if not user_id:
            return redirect("/")

        with sqlite3.connect("wwmt.db") as conn:
            record = conn.execute("SELECT account FROM users WHERE id=?", (user_id,)).fetchone()

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
        page = 1
        if request.args.get("page"):
            try:
                page = int(request.args.get("page"))
            except ValueError:
                page = 1
            if page < 0:
                page = 1
            offset = 10 * (page - 1)
        movies = curr.execute("SELECT * FROM movies LIMIT 10 OFFSET ?", (offset,)).fetchall()
        return render_template("movies.html", user=user, username=username, movies=movies, title="Home", page=page)
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
    """Clears the user session and redirects to the home page."""
    # Clear all session data to log out the user
    session.clear()
    # Redirect to home page after logout
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
        try:
            response = requests.get("http://www.omdbapi.com", params={'apikey': OMDB_API, 's': request.form.get("title"), 'type': 'movie'})
        except:
            return render_template("error.html", error="Error using external API server. Please try again later.", login=True, user=user, username=username)
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
    try:
        rating = int(round(float(response_text['Ratings'][0]['Value'].split("/")[0]), 0))
    except:
        rating = None
    if rating:
        curr.execute("INSERT INTO movies (title, overview, poster, rating, age_rating, director, release, genre, imdb_id) VALUES (?,?,?,?,?,?,?,?,?)", (response_text['Title'], response_text['Plot'], response_text['Poster'], rating, response_text['Rated'], response_text['Director'], response_text['Released'], response_text['Genre'], response_text['imdbID'],))
    else:
        curr.execute("INSERT INTO movies (title, overview, poster, age_rating, director, release, genre, imdb_id) VALUES (?,?,?,?,?,?,?,?)", (response_text['Title'], response_text['Plot'], response_text['Poster'], response_text['Rated'], response_text['Director'], response_text['Released'], response_text['Genre'], response_text['imdbID'],))
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
        if not "T" in request.form.get("datetime"):
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
        return render_template("success.html", message=f"Successfully added showtime with ID {showtime_id}.", login=True, user=user, username=username)
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
    """Allows a logged-in user to change their account password."""
    # Establish database connection
    conn = sqlite3.connect("wwmt.db")
    curr = conn.cursor()
    # Get user credentials
    credentials = get_credentials(session.get('user_id'))
    if not credentials:
        return redirect("/")
    user = credentials[0]
    username = credentials[1]
    if request.method == "POST":
        # Validate all form fields are filled
        if '' in [request.form.get(field) for field in request.form]:
            return render_template("error.html", error="Please fill out all forms.", user=user, username=username, login=True)
        # Extract old password from form
        old_password = request.form.get("old")
        # Check if new passwords match
        if request.form.get("new") != request.form.get("confirmation"):
            return render_template("error.html", error="Passwords do not match.", user=user, username=username, login=True)
        # Retrieve user's current password hash from database
        hsh = curr.execute("SELECT * FROM users WHERE id=?", (session.get("user_id"),)).fetchone()[3]
        # Verify the old password is correct
        if not werkzeug.security.check_password_hash(hsh, old_password):
            return render_template("error.html", error="Incorrect password.", user=user, username=username, login=True)
        # Hash the new password
        new_hsh = werkzeug.security.generate_password_hash(request.form.get("new"))
        # Update password in database
        curr.execute("UPDATE users SET password=? WHERE id=?", (new_hsh, session.get("user_id"),))
        conn.commit()
        conn.close()
        # Display success message
        return render_template("success.html", user=user, username=username, login=True, message="Password changed!")
    else:
        # Display password change form
        conn.commit()
        conn.close()
        return render_template("change_password.html", user=user, username=username)

@app.route("/movie", methods=['GET'])
@login_required
def movie():
    # Get user credentials
    conn = sqlite3.connect("wwmt.db")
    curr = conn.cursor()
    credentials = get_credentials(session.get('user_id'))
    if not credentials:
        return redirect("/")
    user = credentials[0]
    username = credentials[1]
    if not request.args.get("id"):
        return render_template("error.html", error="No ID supplied.", user=user, username=username, login=True)
    movie = curr.execute("SELECT * FROM movies WHERE id=?", (request.args.get("id"),)).fetchone()
    if not movie:
        return render_template("error.html", error="Movie not found.", user=user, username=username, login=True)
    showtimes = curr.execute("SELECT * FROM showtimes, movies WHERE movie_id=? AND movie_id = movies.id", (movie[0],)).fetchall()
    new_showtimes = eliminate_invalid_showtimes(showtimes, 3)
    conn.commit()
    conn.close()
    return render_template("movie.html", movie=movie, user=user, username=username, showtimes=new_showtimes)

@login_required
@app.route("/search", methods=['GET'])
def search():
    """Searches for movies by title and/or genre with pagination support."""
    # Get user credentials
    credentials = get_credentials(session.get('user_id'))
    if not credentials:
        return redirect("/")
    user = credentials[0]
    username = credentials[1]
    # Initialize pagination variables
    page = 1
    redirect_bool = False
    # Attempt to parse page number from query parameters
    try:
        page = int(request.args.get("page"))
    except:
        redirect_bool = True
    # Validate page number
    if page < 1:
        redirect_bool = True
    # Calculate database offset for pagination (10 results per page)
    offset = 10 * (page - 1)
    # Establish database connection
    conn = sqlite3.connect("wwmt.db")
    curr = conn.cursor()
    # Extract search query and genre filter from parameters
    query = request.args.get("query")
    genre = request.args.get("genre")
    # Redirect if invalid page number provided
    if redirect_bool:
        return redirect(f"/search?page=1&query={'' if not query else query}&genre={'' if not genre else genre}")
    # Execute database query based on search filters
    if genre and query:
        # Search by both title and genre
        movies = curr.execute("SELECT * FROM movies WHERE title LIKE ? AND genre LIKE ? LIMIT 10 OFFSET ?", ("%" + query + "%", "%" + genre + "%", offset,)).fetchall()
    elif genre:
        # Search by genre only
        movies = curr.execute("SELECT * FROM movies WHERE genre LIKE ? LIMIT 10 OFFSET ?", ("%" + genre + "%", offset,)).fetchall()
    elif query:
        # Search by title only
        movies = curr.execute("SELECT * FROM movies WHERE title LIKE ? LIMIT 10 OFFSET ?", ("%" + query + "%", offset,)).fetchall()
    else:
        # No filters, return all movies
        movies = curr.execute("SELECT * FROM movies LIMIT 10 OFFSET ?", (offset, )).fetchall()
    conn.commit()
    conn.close()
    # Render search results page with pagination and filter information
    return render_template("movies.html", user=user, username=username, movies=movies, title="Search", page=page, query=query, genre=genre)

@login_required
@app.route("/buy", methods=['POST', 'GET'])
def buy():
    """Handles ticket purchasing for a movie showtime, including seat selection and payment processing."""
    # Establish database connection
    conn = sqlite3.connect("wwmt.db")
    curr = conn.cursor()
    # Get user credentials
    credentials = get_credentials(session.get('user_id'))
    if not credentials:
        return redirect("/")
    user = credentials[0]
    username = credentials[1]
    if request.method == "POST":
        # Validate all form fields are filled
        if '' in [request.form.get(field) for field in request.form]:
            return render_template("error.html", error="Please ensure you fill out all fields.", login=True, user=user, username=username)
        # Parse ticket counts from form (adults, children, seniors)
        try:
            tickets = [{'type': field, 'number': int(request.form.get(field))} for field in list(dict(request.form).keys())[:3]]
        except:
            return render_template("error.html", error="Please ensure number fields contain a number.", login=True, user=user, username=username)
        # Verify at least one ticket is being purchased
        ok = False
        for ticket in tickets:
            if ticket['number'] != 0:
                ok = True
                break
        if not ok:
            return render_template("error.html", error="Please purchase a ticket at the bare minimum.", login=True, user=user, username=username)
        # Convert ticket list to dictionary format for easier lookup
        tickets_dict = {}
        for ticket in tickets:
            tickets_dict[ticket['type']] = ticket['number']
        # Validate showtime ID is provided
        if not request.form.get("showtime_id"):
            return render_template('error.html', error="Please do not interfere with the pre-established hidden form fields.", login=True, user=user, username=username)
        # Extract seat selections from form (seats_row_column format)
        seats = []
        ok = False
        for field in dict(request.form).keys():
            if field.split("_")[0] == "seats":
                ok = True
                field_dict = {}
                # Parse row and column from field name
                field_dict['row'] = int(field.split("_")[1])
                field_dict['seat'] = int(field.split("_")[2])
                seats.append(field_dict)
        # Verify user selected at least one seat
        if not ok:
            return render_template("error.html", error="Please select your spots within the movie theatre.", login=True, user=user, username=username)
        # Count total number of tickets purchased
        tickets_total = 0
        for ticket in tickets:
            tickets_total += ticket['number']
        # Ensure number of tickets matches number of seats selected
        if tickets_total != len(seats):
            return render_template("error.html", error="Number of tickets does not match number of seats booked.", login=True, user=user, username=username)
        # Retrieve showtime details from database
        record = curr.execute("SELECT * FROM showtimes WHERE showtimes.id=?", (request.form.get("showtime_id"),)).fetchall()
        # Filter out invalid (past) showtimes
        record = eliminate_invalid_showtimes(record, 3)
        if not record:
            return render_template("error.html", error="Invalid showtime ID.", login=True, user=user, username=username)
        # Check if user already has tickets for this showtime and enforce max 10 ticket limit per user
        user_ticket_count = curr.execute("SELECT count(id) FROM tickets WHERE user_id=? AND showtime_id=?", (session.get("user_id"),request.form.get("showtime_id"),)).fetchone()
        if int(user_ticket_count[0]) + len(seats) > 10:
            return render_template("error.html", error="Too many tickets (> 10) booked on a single user ID.", login=True, user=user, username=username)
        # Extract current revenue and capacity from showtime
        revenue = int(record[0][5])
        capacity = int(record[0][6])
        # Calculate new revenue by adding price for each ticket type purchased
        for ticket_type in TICKET_PRICES.keys():
            print(ticket_type)
            revenue += TICKET_PRICES[ticket_type] * tickets_dict[TICKET_TYPES[ticket_type]]
        # Update available capacity by subtracting purchased tickets
        capacity -= tickets_total
        # Update the showtime record with new revenue and capacity
        curr.execute("UPDATE showtimes SET revenue=?, capacity=? WHERE id=?", (revenue, capacity, request.form.get("showtime_id"),))
        # Insert individual tickets into database for each seat purchased
        seats_idx = 0
        for ticket_type in tickets_dict.keys():
            no = tickets_dict[ticket_type]
            # Create a ticket entry for each seat of this ticket type
            for _ in range(no):
                seat = seats[seats_idx]
                curr.execute("INSERT INTO tickets (user_id, showtime_id, price, column, seat, type) VALUES (?, ?, ?, ?, ?, ?)", (session.get("user_id"), request.form.get("showtime_id"), TICKET_PRICES[TICKET_TYPES_PLURAL[ticket_type]], seat['row'], seat['seat'], TICKET_TYPES_PLURAL[ticket_type],))
                seats_idx += 1
        # Commit all database changes
        conn.commit()
        conn.close()
        # Redirect to home page after successful purchase
        return redirect("/")
    else:
        # GET request: Display the ticket purchase form
        # Validate showtime ID is provided
        if not request.args.get("id"):
            return render_template("error.html", error="No showtime ID provided.", user=user, username=username, login=True)
        # Retrieve showtime and movie details from database
        record = curr.execute("SELECT * FROM showtimes, movies WHERE showtimes.id=? AND showtimes.movie_id = movies.id", (request.args.get("id"),)).fetchone()
        # Verify the showtime is still valid (not in the past)
        if not valid_showtime(record, 3):
            return render_template("error.html", error="Invalid showtime ID.", user=user, username=username, login=True)
        # Double-check record exists
        if not record:
            return render_template("error.html", error="Invalid showtime ID.", user=user, username=username, login=True)
        # Retrieve all tickets already booked for this showtime
        tickets = curr.execute("SELECT * FROM tickets WHERE showtime_id=?", (request.args.get("id"),)).fetchall()
        # Initialize seating chart: 5 rows x 10 seats per row, all unoccupied initially
        seating = [[{'seat': seat, 'row': row, 'occupied': 0} for seat in range(1, 11)] for row in range(1, 6)]
        # Mark booked seats as occupied
        for ticket in tickets:
            seating[ticket[4]-1][ticket[5]-1]['occupied'] = 1
        conn.commit()
        conn.close()
        # Render purchase form with seating chart and showtime details
        return render_template("buy.html", user=user, username=username, showtime=record, seating=seating, capacity=record[6], showtime_id = record[0])

@login_required
@app.route("/tickets", methods=['GET'])
def tickets():
    """Displays all tickets purchased by the logged-in user."""
    # Establish database connection
    conn = sqlite3.connect("wwmt.db")
    curr = conn.cursor()
    # Get user credentials
    credentials = get_credentials(session.get('user_id'))
    if not credentials:
        return redirect("/")
    user = credentials[0]
    username = credentials[1]
    # Retrieve all tickets for the user with associated showtime and movie details
    tickets = curr.execute("SELECT * FROM tickets, showtimes, movies, users WHERE tickets.user_id=? AND tickets.showtime_id = showtimes.id AND showtimes.movie_id = movies.id AND tickets.user_id = users.id ORDER BY tickets.id DESC", (session.get("user_id"),)).fetchall()
    # Get current date to determine if tickets are still valid
    current_date = datetime.datetime.now()
    tickets = list(tickets)
    # Add a flag to each ticket indicating whether it's still valid (not past its showtime)
    for ticket_idx in range(len(tickets)):
        ticket_list = list(tickets[ticket_idx])
        ticket_list.append(True)  # Default to valid
        # Check if showtime has already passed
        if current_date > datetime.datetime.strptime(ticket_list[10], "%Y-%m-%d %H:%M:%S"):
            ticket_list[-1] = False  # Mark as invalid if past showtime
        tickets[ticket_idx] = ticket_list
    conn.commit()
    conn.close()
    # Render tickets page with user's tickets
    return render_template("tickets.html", user=user, username=username, tickets=tickets)

@login_required
@app.route("/refund", methods=['POST'])
def refund():
    """Processes a ticket refund for a user's purchased ticket."""
    # Establish database connection
    conn = sqlite3.connect("wwmt.db")
    curr = conn.cursor()
    # Get user credentials
    credentials = get_credentials(session.get('user_id'))
    if not credentials:
        return redirect("/")
    user = credentials[0]
    username = credentials[1]
    if request.method == "POST":
        # Validate ticket ID is provided
        if not request.form.get("ticket_id"):
            return render_template("error.html", error="No ticket ID provided!", user=user, login=True, username=username)
        # Retrieve ticket details from database
        ticket = curr.execute("SELECT * FROM tickets, showtimes, movies, users WHERE tickets.id=? AND tickets.showtime_id = showtimes.id AND showtimes.movie_id = movies.id AND tickets.user_id = users.id", (request.form.get("ticket_id"),)).fetchone()
        # Verify ticket exists
        if not ticket:
            return render_template("error.html", error="Invalid ticket ID.", user=user, login=True, username=username)
        # Ensure ticket belongs to the logged-in user
        if ticket[1] != session.get("user_id"):
            return render_template("error.html", error="Ticket ID does not match user ID.", user=user, login=True, username=username)
        # Verify the showtime is still valid (refund only allowed before showtime)
        if not valid_showtime(ticket, 10):
            return render_template("error.html", error="Invalid showtime.", user=user, username=username, login=True)
        # Extract ticket price and showtime revenue/capacity
        price = int(ticket[3])
        revenue = int(ticket[12])
        capacity = int(ticket[13])
        # Update showtime statistics: increase available seats and decrease revenue
        capacity += 1
        revenue -= price
        # Update the showtime record with new revenue and capacity
        curr.execute("UPDATE showtimes SET revenue=?, capacity=? WHERE showtimes.id=?", (revenue, capacity, ticket[2]))
        # Remove the ticket from the database
        curr.execute("DELETE FROM tickets WHERE id=?", (request.form.get("ticket_id"),))
        conn.commit()
        conn.close()
        # Display success message with refund amount
        return render_template("success.html", message=f"Successfully refunded ${price}.", login=True, user=user, username=username)

