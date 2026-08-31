from flask import Flask, redirect, render_template, session
from flask_session import Session
import sqlite3, random

# Initialize application
app = Flask(__name__)

# Configure session cookies 
app.secret_key = random.randbytes(8)
app.config['SESSION_TYPE'] = "filesystem"
app.config['SESSION_PERMANENT'] = False
Session(app)

@app.route("/")
def index():
    if session.get("user_id"):
        return render_template("home.html")
    else:
        return render_template("landing_page.html")

