from flask import Flask, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__, template_folder='templates')

# Configuration
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key-change-this')

basedir = os.path.abspath(os.path.dirname(__file__))
db_path = os.path.join(basedir, 'database', 'jewellery.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

app.config['UPLOAD_FOLDER'] = os.path.join(basedir, 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max file size

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

# Initialize database
db = SQLAlchemy(app)

# ==================== JINJA2 CUSTOM FILTERS ====================

@app.template_filter('from_json')
def from_json_filter(value):
    """Parse JSON string to Python object"""
    try:
        if value:
            return json.loads(value)
        return []
    except:
        return []

# ==================== HELPER FUNCTIONS ====================

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def create_upload_folders():
    """Create required folders"""
    folders = [
        os.path.join(app.config['UPLOAD_FOLDER'], 'segments'),
        os.path.join(app.config['UPLOAD_FOLDER'], 'categories'),
        os.path.join(app.config['UPLOAD_FOLDER'], 'subcategories'),
        os.path.join(app.config['UPLOAD_FOLDER'], 'products', 'primary'),
        os.path.join(app.config['UPLOAD_FOLDER'], 'products', 'gallery'),
        os.path.join(app.config['UPLOAD_FOLDER'], 'sections'),
        os.path.join(basedir, 'database')
    ]
    for folder in folders:
        os.makedirs(folder, exist_ok=True)

# ==================== STATIC FILE ROUTES ====================

@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


@app.route('/<path:filename>')
def catch_all_static(filename):
    """Serve static files (HTML, CSS, JS, images) if not handled by routes"""
    # Get the templates directory (where your HTML files are)
    templates_dir = os.path.join(basedir, 'templates')
    
    if filename.endswith('.html'):
        return send_from_directory(templates_dir, filename)
    elif filename.startswith('css/'):
        return send_from_directory(templates_dir, filename)
    elif filename.startswith('js/'):
        return send_from_directory(templates_dir, filename)
    elif filename.startswith('images/'):
        return send_from_directory(basedir, filename)
    return "The requested file or page was not found.", 404

# Import routes after app and db initialization
from routes import *

if __name__ == '__main__':
    create_upload_folders()
    with app.app_context():
        db.create_all()
    
    print("=" * 50)
    print("Server started successfully!")
    print("=" * 50)
    print("Frontend: http://localhost:5000")
    print("Admin Panel: http://localhost:5000/admin/login")
    print("Dashboard: http://localhost:5000/admin/dashboard")
    print("=" * 50)
    
    app.run(debug=True, host='0.0.0.0', port=5000)