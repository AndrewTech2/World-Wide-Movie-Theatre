from flask import Flask, redirect, render_template
from flask-session import Session
import sqlite3, random

app = Flask(__name__)
app.secret_key = random.randbytes(8)
Session(app)