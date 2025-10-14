import os
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager,
    UserMixin,
    login_user,
    logout_user,
    login_required,
    current_user,
)
from flask import Flask, render_template, request, redirect, url_for, jsonify, g
from datetime import datetime, timezone

# --- 1. APPLICATION SETUP (NO DB CONFIG HERE) ---
app = Flask(__name__)

app.config["SECRET_KEY"] = "cklm"  # Your secret key
REPORTER_PASSWORD = "easy"

# --- 2. LAZY DATABASE INITIALIZATION ---
# Initialize the DB object globally, but don't bind it to the app yet.
db = SQLAlchemy()


class Location(db.Model):
    __tablename__ = "locations"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    status_color = db.Column(db.String(10), nullable=False)
    last_updated_time = db.Column(db.DateTime, nullable=False)


# --- 3. DATABASE CONFIGURATION FUNCTION ---
def configure_database(app):
    """
    Configures and binds the application to the database URL.
    This function is run BEFORE the app starts serving requests.
    """
    # Get the URL securely from the Render environment variable
    DATABASE_URL_RAW = "postgresql://neondb_owner:npg_iZ7IEtplD2PK@ep-broad-bush-a1ff27pd-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"

    if not DATABASE_URL_RAW:
        # Halt deployment if the variable is missing
        raise ValueError(
            "FATAL ERROR: DATABASE_URL environment variable is not set. Cannot connect to Neon."
        )

    # Format the URL for SQLAlchemy compatibility
    DATABASE_URL_FORMATTED = DATABASE_URL_RAW.replace("postgres://", "postgresql://")

    app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL_FORMATTED
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # Bind the DB object to the application instance
    db.init_app(app)

    # After configuration, we create the model and run setup
    # We must ensure all tables exist and initial data is present
    with app.app_context():
        db.create_all()
        if Location.query.count() == 0:
            initial_locations = [
                ("Canteen Corner Booths", "Yellow", datetime.now(timezone.utc)),
                ("Canteen outside", "Green", datetime.now(timezone.utc)),
                ("CB benches", "Green", datetime.now(timezone.utc)),
                ("Ground", "Green", datetime.now(timezone.utc)),
                ("Library", "Green", datetime.now(timezone.utc)),
                ("KK Block", "Yellow", datetime.now(timezone.utc)),
            ]
            for name, color, time in initial_locations:
                loc = Location(name=name, status_color=color, last_updated_time=time)
                db.session.add(loc)
            db.session.commit()


# --- Run the Configuration before routes are defined ---
configure_database(app)


# --- 4. FLASK-LOGIN & OTHER CONFIGURATION ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "reporter_login"


class Reporter(UserMixin):
    def get_id(self):
        return "reporter_user"


@login_manager.user_loader
def load_user(user_id):
    if user_id == "reporter_user":
        return Reporter()
    return None


# --- 5. ROUTES (NOW USING db.session AND Location MODEL) ---


@app.route("/")
def dashboard():
    # Use the Location model now that it's globally defined
    locations = db.session.execute(db.select(Location)).scalars().all()
    return render_template("dashboard.html", locations=locations)


@app.route("/api/status")
def api_status():
    locations = db.session.execute(db.select(Location)).scalars().all()

    results = []
    for loc in locations:
        results.append(
            {
                "id": loc.id,
                "name": loc.name,
                "status_color": loc.status_color,
                "last_updated_time": loc.last_updated_time.strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
            }
        )
    return jsonify(results)


@app.route("/reporter", methods=["GET", "POST"])
def reporter_login():
    if request.method == "POST":
        password = request.form.get("password")
        if password == REPORTER_PASSWORD:
            login_user(Reporter())

            # Fetch locations using the correct SQLAlchemy method
            locations = db.session.execute(db.select(Location)).scalars().all()
            return render_template("reporter_update.html", locations=locations)
        else:
            return render_template("reporter_login.html", error="Invalid Password")

    if current_user.is_authenticated:
        locations = (
            db.session.execute(db.select(Location)).scalars().all()
        )
        return render_template("reporter_update.html", locations=locations)

    return render_template("reporter_login.html")


@app.route("/update/<int:location_id>/<string:color>")
@login_required
def update_status(location_id, color):
    if color not in ["Green", "Yellow", "Red"]:
        return "Invalid color status.", 400

    # Find location by ID using the session
    loc = db.session.get(Location, location_id)

    if loc:
        loc.status_color = color
        loc.last_updated_time = datetime.now(timezone.utc)
        db.session.commit()

    return redirect(url_for("reporter_login"))


@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for("dashboard"))


if __name__ == "__main__":
    # When running locally, ensure the configuration runs
    app.run(debug=True)
