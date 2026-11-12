
from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "travel_assistant_secret_key_2026"

DATABASE = "travel.db"


# DATABASE CONNECTION
def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


# CREATE DATABASE TABLES
def init_db():
    conn = get_db_connection()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS trips (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            destination TEXT NOT NULL,
            start_date TEXT NOT NULL,
            end_date TEXT NOT NULL,
            budget REAL NOT NULL,
            notes TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    conn.commit()
    conn.close()


# HOME PAGE
@app.route("/")
def home():
    return render_template("index.html")


# REGISTER
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["name"].strip()
        email = request.form["email"].strip().lower()
        password = request.form["password"]

        if not name or not email or not password:
            flash("Please fill in all fields.")
            return redirect(url_for("register"))

        if len(password) < 8:
            flash("Password must contain at least 8 characters.")
            return redirect(url_for("register"))

        hashed_password = generate_password_hash(password)
        conn = get_db_connection()

        try:
            conn.execute(
                "INSERT INTO users (name, email, password) VALUES (?, ?, ?)",
                (name, email, hashed_password)
            )
            conn.commit()
        except sqlite3.IntegrityError:
            flash("This email is already registered.")
            conn.close()
            return redirect(url_for("register"))

        conn.close()
        flash("Account created successfully. Please log in.")
        return redirect(url_for("login"))

    return render_template("register.html")


# LOGIN
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        password = request.form["password"]

        conn = get_db_connection()
        user = conn.execute(
            "SELECT * FROM users WHERE email = ?",
            (email,)
        ).fetchone()
        conn.close()

        if user and check_password_hash(user["password"], password):
            session.clear()
            session["user_id"] = user["id"]
            session["user_name"] = user["name"]
            return redirect(url_for("dashboard"))

        flash("Invalid email or password.")

    return render_template("login.html")


# DASHBOARD
@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))

    return render_template("dashboard.html", name=session["user_name"])


# VIEW ALL TRIPS
@app.route("/trips")
def trips():
    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db_connection()
    all_trips = conn.execute(
        "SELECT * FROM trips WHERE user_id = ? ORDER BY start_date",
        (session["user_id"],)
    ).fetchall()
    conn.close()

    return render_template("trips.html", trips=all_trips)


# ADD A NEW TRIP
@app.route("/trips/add", methods=["GET", "POST"])
def add_trip():
    if "user_id" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":
        destination = request.form["destination"].strip()
        start_date = request.form["start_date"]
        end_date = request.form["end_date"]
        budget = request.form["budget"]
        notes = request.form.get("notes", "").strip()

        if not destination or not start_date or not end_date or not budget:
            flash("Please complete all required fields.")
            return redirect(url_for("add_trip"))

        if end_date < start_date:
            flash("End date cannot be before start date.")
            return redirect(url_for("add_trip"))

        try:
            budget = float(budget)
            if budget < 0:
                raise ValueError
        except ValueError:
            flash("Please enter a valid, non-negative budget.")
            return redirect(url_for("add_trip"))

        conn = get_db_connection()
        conn.execute("""
            INSERT INTO trips
            (user_id, destination, start_date, end_date, budget, notes)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            session["user_id"], destination, start_date,
            end_date, budget, notes
        ))
        conn.commit()
        conn.close()

        flash("Your trip was added successfully!")
        return redirect(url_for("trips"))

    return render_template("trip_form.html", trip=None)


# EDIT A TRIP
@app.route("/trips/edit/<int:trip_id>", methods=["GET", "POST"])
def edit_trip(trip_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db_connection()
    trip = conn.execute(
        "SELECT * FROM trips WHERE id = ? AND user_id = ?",
        (trip_id, session["user_id"])
    ).fetchone()

    if trip is None:
        conn.close()
        return "Trip not found", 404

    if request.method == "POST":
        destination = request.form["destination"].strip()
        start_date = request.form["start_date"]
        end_date = request.form["end_date"]
        notes = request.form.get("notes", "").strip()

        try:
            budget = float(request.form["budget"])
            if not destination or not start_date or not end_date:
                raise ValueError
            if end_date < start_date or budget < 0:
                raise ValueError
        except ValueError:
            conn.close()
            flash("Please check your trip details and budget.")
            return redirect(url_for("edit_trip", trip_id=trip_id))

        conn.execute("""
            UPDATE trips
            SET destination = ?, start_date = ?, end_date = ?,
                budget = ?, notes = ?
            WHERE id = ? AND user_id = ?
        """, (
            destination, start_date, end_date, budget,
            notes, trip_id, session["user_id"]
        ))
        conn.commit()
        conn.close()

        flash("Trip updated successfully!")
        return redirect(url_for("trips"))

    conn.close()
    return render_template("trip_form.html", trip=trip)


# DELETE A TRIP
@app.route("/trips/delete/<int:trip_id>", methods=["POST"])
def delete_trip(trip_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db_connection()
    conn.execute(
        "DELETE FROM trips WHERE id = ? AND user_id = ?",
        (trip_id, session["user_id"])
    )
    conn.commit()
    conn.close()

    flash("Trip deleted.")
    return redirect(url_for("trips"))


# LOGOUT
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
