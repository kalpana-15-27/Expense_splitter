# Final Code: Flask App using Permanent Neon PostgreSQL (Free Tier Solution)
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask import Flask, render_template, request, redirect, url_for, jsonify, g
from datetime import datetime, timezone
import os # Added for environment variable access, best practice for deployment

# --- Configuration (Define 'app' first) ---
app = Flask(__name__) 

# CRITICAL: PASTE YOUR URL HERE from Neon Console (e.g., postgres://user:pass@ep-bush-1234.cloud.neon.tec)h/neondb)
DATABASE_URL_RAW = os.environ.get('DATABASE_URL')
db = None
if DATABASE_URL_RAW:
# Configure Flask-SQLAlchemys
    if DATABASE_URL_RAW.startswith('postgres://'):
        DATABASE_URL_FORMATTED= DATABASE_URL_RAW.replace("postgres://","postgresql://")
    else:
        DATABASE_URL_FORMATTED = DATABASE_URL_RAW
# Use the postgresql:// scheme for SQLAlchemy compatibility
    app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False 
    app.config['SECRET_KEY'] = 'cklm' # Required for Flask-Login

    db = SQLAlchemy(app) # Initialize SQLAlchemy
else:
    print("VARIABLE NOT FOUND")
REPORTER_PASSWORD = "easy" 

# --- Flask-Login Configuration ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'reporter_login'

class Reporter(UserMixin):
    def get_id(self):
        return "reporter_user" 

@login_manager.user_loader
def load_user(user_id):
    if user_id == "reporter_user":
        return Reporter()
    return None

# --- Define the Database Model (The 'locations' table) ---
class Location(db.Model):
    __tablename__ = 'locations'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    status_color = db.Column(db.String(10), nullable=False)
    last_updated_time = db.Column(db.DateTime, nullable=False)

# --- Initialization Function (Runs ONCE to set up table) ---
def init_db():
    with app.app_context():
        # Create the tables if they don't exist
        db.create_all() 
        
        # Insert initial data ONLY if the table is empty
        if Location.query.count() == 0:
            initial_locations = [
                ("Canteen Corner Booths", "Yellow", datetime.now(timezone.utc)), 
                ("Canteen outside", "Green", datetime.now(timezone.utc)),
                ("CB benches", "Green", datetime.now(timezone.utc)),
                ("Ground", "Green", datetime.now(timezone.utc)),
                ("Library", "Green", datetime.now(timezone.utc)),
                ("KK Block", "Yellow", datetime.now(timezone.utc))
            ]
            for name, color, time in initial_locations:
                loc = Location(name=name, status_color=color, last_updated_time=time)
                db.session.add(loc)
            db.session.commit()

# --- 1. Public Dashboard Route (READ) ---
@app.route('/')
def dashboard():
    locations = Location.query.all()
    return render_template('dashboard.html', locations=locations)

# --- 2. API Status Route (JSON READ for AJAX) ---
@app.route('/api/status')
def api_status():
    locations = Location.query.all()
    
    results = []
    for loc in locations:
        results.append({
            'id': loc.id,
            'name': loc.name,
            'status_color': loc.status_color,
            # Format time correctly for the JavaScript front-end
            'last_updated_time': loc.last_updated_time.strftime("%Y-%m-%d %H:%M:%S")
        })
    return jsonify(results)

# --- 3. Reporter Login/Logout Routes ---
@app.route('/reporter', methods=['GET', 'POST'])
def reporter_login():
    if request.method == 'POST':
        password = request.form.get('password')
        if password == REPORTER_PASSWORD:
            user = Reporter()
            login_user(user) 
            
            locations = Location.query.all()
            return render_template('reporter_update.html', locations=locations)
        else:
            return render_template('reporter_login.html', error="Invalid Password")
            
    if current_user.is_authenticated:
        locations = Location.query.all()
        return render_template('reporter_update.html', locations=locations)
        
    return render_template('reporter_login.html')

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('dashboard'))

# --- 4. Status Update Route (WRITE) ---
@app.route('/update/<int:location_id>/<string:color>')
@login_required 
def update_status(location_id, color):
    if color not in ['Green', 'Yellow', 'Red']:
        return "Invalid color status.", 400
        
    loc = Location.query.get(location_id) 
    
    if loc:
        loc.status_color = color
        # Record time in UTC, which is what the database expects
        loc.last_updated_time = datetime.now(timezone.utc)
        db.session.commit()
    
    return redirect(url_for('reporter_login'))

if __name__ == '__main__':
    # We do NOT run init_db() here. We run it ONCE manually on Render.
    app.run(debug=True)
