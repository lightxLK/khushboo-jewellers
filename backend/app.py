from flask import Flask, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os
import json
import logging
from dotenv import load_dotenv
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Load environment variables
load_dotenv()

FLASK_ENV = os.getenv('FLASK_ENV', 'production')
IS_PRODUCTION = FLASK_ENV == 'production'

# Initialize Flask app
app = Flask(__name__, template_folder='templates')

# Configuration
SECRET_KEY = os.getenv('SECRET_KEY')
if not SECRET_KEY:
    if IS_PRODUCTION:
        raise RuntimeError(
            "SECRET_KEY environment variable is not set. "
            "Set it in backend/.env before starting the app."
        )
    # Only allow an ephemeral dev key outside production, never a fixed default.
    import secrets as _secrets
    SECRET_KEY = _secrets.token_hex(32)
    logging.warning("SECRET_KEY not set; using a random ephemeral key for this dev run only.")
app.config['SECRET_KEY'] = SECRET_KEY

# Session cookie hardening
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_SECURE'] = IS_PRODUCTION

# ==================== LOGGING ====================
from logging.handlers import RotatingFileHandler

_log_level = logging.INFO if IS_PRODUCTION else logging.DEBUG
_log_format = logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s')

_root_logger = logging.getLogger()
_root_logger.setLevel(_log_level)

_stream_handler = logging.StreamHandler()
_stream_handler.setFormatter(_log_format)
_root_logger.addHandler(_stream_handler)

LOG_DIR = os.getenv('LOG_DIR', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs'))
os.makedirs(LOG_DIR, exist_ok=True)
_file_handler = RotatingFileHandler(
    os.path.join(LOG_DIR, 'khushboo.log'), maxBytes=5 * 1024 * 1024, backupCount=5
)
_file_handler.setFormatter(_log_format)
_root_logger.addHandler(_file_handler)

logger = logging.getLogger('khushboo')

# CSRF protection for all session-authenticated forms/POSTs.
# Server-to-server API endpoints (e.g. /api/sheet-sync) are exempted individually in routes.py.
csrf = CSRFProtect(app)

# Login rate limiting. In-memory storage is fine for a single gunicorn worker;
# a multi-worker deployment would need a shared backend (e.g. Redis) instead.
limiter = Limiter(get_remote_address, app=app, storage_uri="memory://")

basedir = os.path.abspath(os.path.dirname(__file__))
db_path = os.path.join(basedir, 'database', 'jewellery.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

app.config['UPLOAD_FOLDER'] = os.path.join(basedir, 'uploads')
# 100MB default is correct for production (public-facing endpoints never need
# more). The local bulk-image-import workflow raises this via
# MAX_CONTENT_LENGTH_BYTES in a *local* .env only — never set this above the
# default in the production .env.
app.config['MAX_CONTENT_LENGTH'] = int(os.getenv('MAX_CONTENT_LENGTH_BYTES', 100 * 1024 * 1024))

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

    # Never serve raw admin templates (unrendered Jinja source) unauthenticated.
    # Admin pages must always go through their proper @login_required routes.
    if filename.startswith('admin/') or filename.startswith('admin\\'):
        return "The requested file or page was not found.", 404

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
    
    logger.info("Server started successfully! Frontend: http://127.0.0.1:5000  Admin: http://127.0.0.1:5000/admin/login")

    # Debug mode and public bind must never be on in production.
    # host stays on localhost; nginx/reverse proxy handles the public interface.
    app.run(debug=not IS_PRODUCTION, host='127.0.0.1', port=int(os.getenv('PORT', 5000)))