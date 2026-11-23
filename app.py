from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import datetime, timedelta
import sqlite3, os, random

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-secret-key-for-production")
DB_PATH = os.path.join(os.path.dirname(__file__), "food_rescue.db")

def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with db() as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL, email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL, role TEXT NOT NULL,
            city TEXT NOT NULL, phone TEXT
        );
        CREATE TABLE IF NOT EXISTS donations(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            donor_id INTEGER NOT NULL,
            food_name TEXT NOT NULL, category TEXT NOT NULL,
            quantity_kg REAL NOT NULL, servings INTEGER NOT NULL,
            city TEXT NOT NULL, prepared_at TEXT NOT NULL,
            safe_until TEXT NOT NULL, notes TEXT,
            status TEXT NOT NULL DEFAULT 'Available',
            ngo_id INTEGER, created_at TEXT NOT NULL,
            FOREIGN KEY(donor_id) REFERENCES users(id),
            FOREIGN KEY(ngo_id) REFERENCES users(id)
        );
        CREATE TABLE IF NOT EXISTS activity(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            donation_id INTEGER NOT NULL, user_id INTEGER NOT NULL,
            action TEXT NOT NULL, created_at TEXT NOT NULL
        );
        """)
        # Demo accounts make the prototype easy to demonstrate.
        demos = [
            ("Demo Restaurant", "donor@example.com", "donor", "Chennai", "9000000001"),
            ("Hope Food NGO", "ngo@example.com", "ngo", "Chennai", "9000000002"),
            ("Demo Volunteer", "volunteer@example.com", "volunteer", "Chennai", "9000000003"),
        ]
        for name, email, role, city, phone in demos:
            exists = con.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone()
            if not exists:
                con.execute(
                    "INSERT INTO users(name,email,password,role,city,phone) VALUES(?,?,?,?,?,?)",
                    (name, email, generate_password_hash("Demo@123"), role, city, phone)
                )

def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to continue.", "warning")
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapper

def current_user():
    if "user_id" not in session:
        return None
    with db() as con:
        return con.execute("SELECT * FROM users WHERE id=?", (session["user_id"],)).fetchone()

def estimate_surplus(prepared_meals, expected_customers, event_day):
    """Demo ML model: RandomForest trained on synthetic sample data.
    Replace synthetic examples with real, consented historical kitchen data for deployment.
    """
    try:
        from sklearn.ensemble import RandomForestRegressor
        rng = random.Random(42)
        X, y = [], []
        for _ in range(500):
            prepared = rng.randint(20, 800)
            expected = rng.randint(10, 800)
            event = rng.randint(0, 1)
            # Synthetic teaching data: demand varies around expected customers.
            actual_demand = max(0, int(expected * rng.uniform(0.82, 1.18) + event * rng.randint(-10, 80)))
            X.append([prepared, expected, event])
            y.append(max(0, prepared - actual_demand))
        model = RandomForestRegressor(n_estimators=60, random_state=42, max_depth=8)
        model.fit(X, y)
        prediction = model.predict([[prepared_meals, expected_customers, event_day]])[0]
        return max(0, round(float(prediction)))
    except Exception:
        # Simple fallback if scikit-learn is not installed.
        demand = expected_customers * (1.10 if event_day else 1.0)
        return max(0, round(prepared_meals - demand))

@app.context_processor
def inject_globals():
    return {"logged_user": current_user(), "now": datetime.now()}

@app.route("/")
def index():
    with db() as con:
        stats = {
            "donations": con.execute("SELECT COUNT(*) FROM donations").fetchone()[0],
            "available": con.execute("SELECT COUNT(*) FROM donations WHERE status='Available'").fetchone()[0],
            "meals": con.execute("SELECT COALESCE(SUM(servings),0) FROM donations WHERE status IN ('Accepted','Delivered')").fetchone()[0]
        }
    return render_template("index.html", stats=stats)

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        role = request.form.get("role", "")
        city = request.form.get("city", "").strip()
        phone = request.form.get("phone", "").strip()
        if not all([name, email, password, city]) or role not in ["donor", "ngo", "volunteer"]:
            flash("Please complete all required fields.", "danger")
            return render_template("register.html")
        if len(password) < 6:
            flash("Password must contain at least 6 characters.", "danger")
            return render_template("register.html")
        try:
            with db() as con:
                con.execute("INSERT INTO users(name,email,password,role,city,phone) VALUES(?,?,?,?,?,?)",
                    (name, email, generate_password_hash(password), role, city, phone))
            flash("Account created. Please log in.", "success")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("This email is already registered.", "danger")
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        with db() as con:
            user = con.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        if user and check_password_hash(user["password"], password):
            session.clear()
            session["user_id"] = user["id"]
            flash(f"Welcome, {user['name']}!", "success")
            return redirect(url_for("dashboard"))
        flash("Invalid email or password.", "danger")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("index"))

@app.route("/dashboard")
@login_required
def dashboard():
    user = current_user()
    with db() as con:
        if user["role"] == "donor":
            rows = con.execute("""SELECT d.*, u.name AS ngo_name FROM donations d
                LEFT JOIN users u ON d.ngo_id=u.id WHERE d.donor_id=? ORDER BY d.id DESC""",
                (user["id"],)).fetchall()
        elif user["role"] == "ngo":
            rows = con.execute("""SELECT d.*, u.name AS donor_name FROM donations d
                JOIN users u ON d.donor_id=u.id
                WHERE d.status='Available' OR d.ngo_id=? ORDER BY d.id DESC""",
                (user["id"],)).fetchall()
        else:
            rows = con.execute("""SELECT d.*, u.name AS donor_name FROM donations d
                JOIN users u ON d.donor_id=u.id
                WHERE d.status='Available' OR d.status='Accepted' ORDER BY d.id DESC""").fetchall()
        totals = {
            "all": con.execute("SELECT COUNT(*) FROM donations").fetchone()[0],
            "available": con.execute("SELECT COUNT(*) FROM donations WHERE status='Available'").fetchone()[0],
            "delivered_meals": con.execute("SELECT COALESCE(SUM(servings),0) FROM donations WHERE status='Delivered'").fetchone()[0]
        }
    return render_template("dashboard.html", rows=rows, totals=totals, user=user)

@app.route("/donate", methods=["GET", "POST"])
@login_required
def donate():
    user = current_user()
    if user["role"] != "donor":
        flash("Only donor accounts can add food donations.", "warning")
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        try:
            food = request.form["food_name"].strip()
            category = request.form["category"]
            kg = float(request.form["quantity_kg"])
            servings = int(request.form["servings"])
            city = request.form["city"].strip()
            prepared = datetime.fromisoformat(request.form["prepared_at"])
            safe_until = datetime.fromisoformat(request.form["safe_until"])
            notes = request.form.get("notes", "").strip()
            if not food or kg <= 0 or servings <= 0 or safe_until <= prepared or safe_until <= datetime.now():
                raise ValueError()
            with db() as con:
                con.execute("""INSERT INTO donations
                    (donor_id,food_name,category,quantity_kg,servings,city,prepared_at,safe_until,notes,created_at)
                    VALUES(?,?,?,?,?,?,?,?,?,?)""",
                    (user["id"], food, category, kg, servings, city, prepared.isoformat(timespec="minutes"),
                     safe_until.isoformat(timespec="minutes"), notes, datetime.now().isoformat(timespec="minutes")))
            flash("Food donation posted successfully.", "success")
            return redirect(url_for("dashboard"))
        except (ValueError, KeyError):
            flash("Check the quantity, servings and date/time fields. Collection deadline must be in the future.", "danger")
    return render_template("donate.html", user=user)

@app.route("/matching")
@login_required
def matching():
    user = current_user()
    with db() as con:
        rows = con.execute("""SELECT d.*, u.name AS donor_name, u.phone AS donor_phone
            FROM donations d JOIN users u ON d.donor_id=u.id
            WHERE d.status='Available' ORDER BY
            CASE WHEN LOWER(d.city)=LOWER(?) THEN 0 ELSE 1 END, d.safe_until ASC""",
            (user["city"],)).fetchall()
    return render_template("matching.html", rows=rows, user=user)

@app.route("/claim/<int:donation_id>", methods=["POST"])
@login_required
def claim(donation_id):
    user = current_user()
    if user["role"] not in ["ngo", "volunteer"]:
        flash("Only an NGO or volunteer account can request a collection.", "warning")
        return redirect(url_for("dashboard"))
    with db() as con:
        row = con.execute("SELECT * FROM donations WHERE id=?", (donation_id,)).fetchone()
        if not row or row["status"] != "Available":
            flash("This donation is no longer available.", "warning")
        elif datetime.fromisoformat(row["safe_until"]) <= datetime.now():
            con.execute("UPDATE donations SET status='Expired' WHERE id=?", (donation_id,))
            flash("The collection deadline has passed.", "danger")
        else:
            con.execute("UPDATE donations SET status='Accepted', ngo_id=? WHERE id=?", (user["id"], donation_id))
            con.execute("INSERT INTO activity(donation_id,user_id,action,created_at) VALUES(?,?,?,?)",
                (donation_id, user["id"], "Accepted for collection", datetime.now().isoformat(timespec="minutes")))
            flash("Donation accepted. Contact the donor to coordinate safe collection.", "success")
    return redirect(url_for("dashboard"))

@app.route("/delivered/<int:donation_id>", methods=["POST"])
@login_required
def delivered(donation_id):
    user = current_user()
    with db() as con:
        row = con.execute("SELECT * FROM donations WHERE id=?", (donation_id,)).fetchone()
        if row and row["ngo_id"] == user["id"] and row["status"] == "Accepted":
            con.execute("UPDATE donations SET status='Delivered' WHERE id=?", (donation_id,))
            con.execute("INSERT INTO activity(donation_id,user_id,action,created_at) VALUES(?,?,?,?)",
                (donation_id, user["id"], "Delivery confirmed", datetime.now().isoformat(timespec="minutes")))
            flash("Delivery marked as completed.", "success")
        else:
            flash("Only the accepting organization can confirm delivery.", "danger")
    return redirect(url_for("dashboard"))

@app.route("/predict", methods=["GET", "POST"])
@login_required
def predict():
    prediction = None
    if request.method == "POST":
        try:
            prepared = int(request.form["prepared"])
            expected = int(request.form["expected"])
            event = 1 if request.form.get("event") == "yes" else 0
            if prepared < 0 or expected < 0:
                raise ValueError()
            prediction = estimate_surplus(prepared, expected, event)
        except (ValueError, KeyError):
            flash("Enter valid non-negative numbers.", "danger")
    return render_template("predict.html", prediction=prediction)

@app.route("/about")
def about():
    return render_template("about.html")

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
