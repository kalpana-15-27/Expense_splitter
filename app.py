from flask import Flask, render_template, request, redirect, url_for, g, jsonify # ADD jsonify
# ... rest of imports

import sqlite3
from datetime import datetime
# New imports
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
# --- Configuration ---
DATABASE = 'status.db'
app = Flask(__name__)
app.config['SECRET_KEY'] = 'cklm'
# Simple, temporary security for reporters page (DO NOT use in a real production app!)
REPORTER_PASSWORD = "easy" 

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
# Redirect users to this route if they try to access a @login_required page
login_manager.login_view = 'reporter_login'
# app.py

# ... (After initializing login_manager)

class Reporter(UserMixin):
    """
    A simple class to represent a logged-in reporter.
    In this beginner scope, all logged-in reporters are the same.
    """
    def get_id(self):
        # The user ID is simply a string
        return "reporter_user" 

@login_manager.user_loader
def load_user(user_id):
    """
    Required by Flask-Login. Tells the extension how to find a user
    when given the user_id stored in the session.
    """
    if user_id == "reporter_user":
        return Reporter()
    return None

# ... (Your @app.route('/') and other routes follow)

# Inside app.py, below the imports but before the routes
# Convert DB time string to a friendly format (e.g., "5 minutes ago")
@app.template_filter('friendly_time')
def format_friendly_time(timestamp_str):
    if not timestamp_str:
        return "Never updated"

    # Parse the string back into a datetime object
    last_updated = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
    now = datetime.now()

    delta = now - last_updated

    # Calculate time difference
    if delta.total_seconds() < 60:
        return "just now"
    elif delta.total_seconds() < 3600:
        minutes = int(delta.total_seconds() / 60)
        return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
    elif delta.total_seconds() < 86400:
        hours = int(delta.total_seconds() / 3600)
        return f"{hours} hour{'s' if hours > 1 else ''} ago"
    else:
        return last_updated.strftime("%b %d, %I:%M %p")

# --- Database Connection Management ---
def get_db():
    """Establishes and returns a database connection."""
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row # Allows accessing columns by name (loc.name)
    return db

@app.teardown_appcontext
def close_connection(exception):
    """Closes the database connection at the end of the request."""
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    """Initializes the database and populates it with starting locations."""
    with app.app_context():
        db = get_db()
        cursor = db.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS locations (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                status_color TEXT NOT NULL,
                last_updated_time DATETIME NOT NULL
            )
        """)
        
        # Initial locations to populate the dashboard
        initial_locations = [
            ("Library (Quiet)", "Green", datetime.now()),
            ("Canteen outside", "Yellow", datetime.now()),
            ("Canteen Corner Booths", "Red", datetime.now()),
            ("Ground", "Green", datetime.now()),
            ("CB Benches", "Green", datetime.now()),
            ("KK Block", "Yellow", datetime.now())
            
        ]
        
        # Insert initial data, skipping if location already exists
        for name, color, time in initial_locations:
            try:
                cursor.execute(
                    "INSERT INTO locations (name, status_color, last_updated_time) VALUES (?, ?, ?)",
                    (name, color, time.strftime("%Y-%m-%d %H:%M:%S"))
                )
            except sqlite3.IntegrityError:
                pass 
                
        db.commit()

# app.py

# --- API Endpoint (READ for AJAX) ---
@app.route('/api/status')
def api_status():
    """API endpoint to return status data as JSON for AJAX updates."""
    db = get_db()
    
    # We fetch the data the same way as the dashboard
    locations = db.execute("SELECT * FROM locations ORDER BY id").fetchall()
    
    # Convert sqlite row objects to a list of dictionaries for JSON
    # SQLite rows can't be directly converted to JSON, so we convert them to standard Python dictionaries first.
    results = []
    for loc in locations:
        results.append(dict(loc))
        
    # Return the data as a JSON response
    return jsonify(results)

# ... rest of your routes

# --- 1. Public Dashboard Route (READ) ---
@app.route('/')
def dashboard():
    """Displays the main public dashboard with all locations and their current status."""
    db = get_db()
    # Fetch all locations, ordered by ID
    locations = db.execute("SELECT * FROM locations ORDER BY id").fetchall()
    return render_template('dashboard.html', locations=locations)

# --- 2. Reporter Login Route ---
@app.route('/reporter', methods=['GET', 'POST'])
def reporter_login():
    """Handles reporter login and displays the update form on success."""
    if request.method == 'POST':
        password = request.form.get('password')
        if password == REPORTER_PASSWORD:
            # On successful login, fetch data and render update page
                        # --- CRITICAL FIXES FOR FLASK-LOGIN ---
            user = Reporter()  # Create the user object
            login_user(user)   # Log the user into the session

            db = get_db()
            locations = db.execute("SELECT * FROM locations ORDER BY id").fetchall()
            return render_template('reporter_update.html', locations=locations)
        else:
            return render_template('reporter_login.html', error="Invalid Password")
            
    return render_template('reporter_login.html')


# --- 3. Status Update Route (WRITE) ---
@app.route('/update/<int:location_id>/<string:color>')
def update_status(location_id, color):
    """Updates the status of a specific location in the database."""
    # Basic validation
    if color not in ['Green', 'Yellow', 'Red']:
        return "Invalid color status.", 400
        
    db = get_db()
    # Get current timestamp in a format SQLite understands
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Update the status and timestamp for the given location ID
    db.execute(
        "UPDATE locations SET status_color = ?, last_updated_time = ? WHERE id = ?",
        (color, current_time, location_id)
    )
    db.commit()
    
    # Redirect back to the reporter login page (which automatically shows the update form if the password is hardcoded)
    return redirect(url_for('reporter_login')) 


if __name__ == '__main__':
    # Initialize the database file and table when the application starts
    with app.app_context():
        init_db()
    # Run the Flask server in debug mode
    app.run(debug=True)
class Reporter(UserMixin):
    def get_id(self):
        # The user ID is simply the password check result (e.g., reporter)
        return "reporter_user" 

@login_manager.user_loader
def load_user(user_id):
    # This function tells Flask-Login how to load a user object
    if user_id == "reporter_user":
        return Reporter()
    return None
# Find the old @app.route('/reporter', methods=['GET', 'POST'])
@app.route('/reporter', methods=['GET', 'POST'])
def reporter_login():
    if request.method == 'POST':
        password = request.form.get('password')
        # Check the password
        if password == REPORTER_PASSWORD:
            user = Reporter()
            login_user(user) # <-- LOG THE USER IN!

            db = get_db()
            locations = db.execute("SELECT * FROM locations ORDER BY id").fetchall()
            # Redirect to the update page after successful login
            return render_template('reporter_update.html', locations=locations)
        else:
            return render_template('reporter_login.html', error="Invalid Password")

    # If the user is already logged in, show the update page immediately
    if current_user.is_authenticated:
        db = get_db()
        locations = db.execute("SELECT * FROM locations ORDER BY id").fetchall()
        return render_template('reporter_update.html', locations=locations)

    return render_template('reporter_login.html')
# --- 3. Status Update Route (WRITE) ---
@app.route('/update/<int:location_id>/<string:color>')
@login_required # Requires the user to be logged in as a reporter
def update_status(location_id, color):
    """Updates the status of a specific location in the database."""
    
    # Basic validation
    if color not in ['Green', 'Yellow', 'Red']:
        return "Invalid color status.", 400
        
    db = get_db()
    
    # Get current timestamp in a format SQLite understands
    # NOTE: This uses the Python datetime object for the time of the update.
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Update the status and timestamp for the given location ID
    db.execute(
        "UPDATE locations SET status_color = ?, last_updated_time = ? WHERE id = ?",
        (color, current_time, location_id)
    )
    db.commit()
    
    # After a successful update, redirect the reporter back to the update page.
    # This is a good UX practice so they can see the change was accepted 
    # and quickly update another location if needed.
    return redirect(url_for('reporter_login'))
@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('dashboard'))
@app.route('/api/status')
def api_status():
    """API endpoint to return status data as JSON for AJAX updates."""
    db = get_db()
    locations = db.execute("SELECT * FROM locations ORDER BY id").fetchall()

    # Convert sqlite row objects to a list of dictionaries for JSON
    results = []
    for loc in locations:
        results.append(dict(loc))

    return jsonify(results)
