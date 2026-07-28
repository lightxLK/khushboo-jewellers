from flask import render_template, request, redirect, url_for, session, jsonify, send_from_directory, flash
from app import app, db, allowed_file
from models import Segment, Category, Subcategory, Product, DynamicSection, AdminUser, ContactInquiry
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from functools import wraps
from PIL import Image
import os, json, io, re, requests, hmac
from app import limiter, logger, csrf

# Guard against decompression-bomb DoS on uploaded images (~40MP cap).
Image.MAX_IMAGE_PIXELS = 40_000_000

# ==================== validate_and_process_image() ====================

def validate_and_process_image(file, max_size_mb=1):
    """
    Validates and processes uploaded image:
    - Accepts any image format and any size
    - Converts to WebP format
    - Resizes to 1080x1080px
    - Compresses to under 1MB
    - Returns: (success: bool, message: str, processed_file: FileStorage or None)
    """
    if not file or not file.filename:
        return False, "No file selected", None

    # Accept any image format
    allowed_extensions = {'jpg', 'jpeg', 'webp', 'png', 'bmp', 'tiff', 'gif', 'heic'}
    file_ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''

    if file_ext not in allowed_extensions:
        return False, f"Invalid file type. Please upload an image file. You uploaded: {file_ext.upper()}", None

    try:
        # Read file into memory
        file_bytes = file.read()

        # Open image with Pillow
        img = Image.open(io.BytesIO(file_bytes))

        # Convert to RGB if necessary (for transparency)
        if img.mode in ('RGBA', 'LA', 'P'):
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
            img = background

                # Resize to 1080x1080 with center-crop (no white bars)
        target_size = (1080, 1080)
        
        # Calculate scaling to FILL the box (not fit inside)
        img_ratio = img.size[0] / img.size[1]
        target_ratio = 1.0  # Square
        
        if img_ratio > target_ratio:
            # Image wider than square - scale to height, crop width
            new_height = target_size[1]
            new_width = int(new_height * img_ratio)
        else:
            # Image taller than square - scale to width, crop height
            new_width = target_size[0]
            new_height = int(new_width / img_ratio)
        
        # Resize image to fill entire box
        img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # Center crop to exact 1080x1080
        left = (new_width - target_size[0]) // 2
        top = (new_height - target_size[1]) // 2
        right = left + target_size[0]
        bottom = top + target_size[1]
        
        final_img = img.crop((left, top, right, bottom))

        # Save to BytesIO as WebP with quality adjustment
        output = io.BytesIO()
        quality = 90  # Start with high quality

        # Try saving with decreasing quality until under 1MB
        while quality > 10:
            output = io.BytesIO()  # Reset buffer
            final_img.save(output, format='WEBP', quality=quality, optimize=True)
            output_size = output.tell()

            # If under 1MB, we're done!
            if output_size <= max_size_mb * 1024 * 1024:
                break

            # Reduce quality and try again
            quality -= 5

        output.seek(0)

        # Create new FileStorage object with WebP extension
        from werkzeug.datastructures import FileStorage
        original_name = file.filename.rsplit('.', 1)[0]
        webp_filename = f"{original_name}.webp"

        processed_file = FileStorage(
            stream=output,
            filename=webp_filename,
            content_type='image/webp'
        )

        final_size_kb = output_size / 1024
        return True, f"Image converted to WebP, resized to 1080x1080, compressed to {final_size_kb:.1f}KB", processed_file

    except Image.DecompressionBombError:
        return False, "Image is too large to process (exceeds pixel limit).", None
    except Exception as e:
        return False, f"Error processing image: {str(e)}", None

# ==================== AUTHENTICATION DECORATORS ====================

def login_required(f):
    """Decorator to require login for admin routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_user_id' not in session:
            flash('Please log in to access the admin panel', 'error')
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """Decorator to require admin role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_user_id' not in session:
            flash('Please log in to access the admin panel', 'error')
            return redirect(url_for('admin_login'))

        # Handle .env admin
        if session.get('is_env_admin'):
            return f(*args, **kwargs)

        # Handle database users
        user = AdminUser.query.get(session['admin_user_id'])
        if not user or user.role != 'admin':
            flash('Access denied. Admin privileges required.', 'error')
            return redirect(url_for('admin_dashboard'))

        return f(*args, **kwargs)
    return decorated_function

def manager_allowed(f):
    """Decorator to allow both admin and manager roles"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_user_id' not in session:
            flash('Please log in to access the admin panel', 'error')
            return redirect(url_for('admin_login'))

        # Handle .env admin (has full access)
        if session.get('is_env_admin'):
            return f(*args, **kwargs)

        # Handle database users
        user = AdminUser.query.get(session['admin_user_id'])
        if not user or user.role not in ['admin', 'manager']:
            flash('Access denied.', 'error')
            return redirect(url_for('admin_dashboard'))

        return f(*args, **kwargs)
    return decorated_function

# ==================== CONTEXT PROCESSOR ====================

@app.context_processor
def inject_globals():
    """Make current user info and site globals available in all templates"""
    globals = {
        'current_user': None,
        'is_admin': False,
        'is_manager': False,
        'unread_inquiries_count': 0
    }
    
    if 'admin_user_id' in session:
        # ✅ Handle .env admin
        if session.get('is_env_admin'):
            globals['current_user'] = type('obj', (object,), {
                'email': os.getenv('ADMIN_USERNAME', 'admin'),
                'role': 'admin'
            })()
            globals['is_admin'] = True
        else:
            # ✅ Handle database users
            user = AdminUser.query.get(session['admin_user_id'])
            if user:
                globals['current_user'] = user
                globals['is_admin'] = user.role == 'admin'
                globals['is_manager'] = user.role == 'manager'
        
        # Count unread inquiries for the badge
        globals['unread_inquiries_count'] = ContactInquiry.query.filter_by(is_read=False).count()

    return globals

# ==================== HELPER FUNCTIONS ====================

def save_single_image(file, folder):
    """Save single image with validation and return path"""
    if file and file.filename:
        # Validate and process image
        success, message, processed_file = validate_and_process_image(file)

        if not success:
            flash(message, 'error')
            return None

        # Save processed image
        filename = f"{int(datetime.now().timestamp())}_{secure_filename(processed_file.filename)}"
        folder_path = os.path.join(app.config['UPLOAD_FOLDER'], folder)
        os.makedirs(folder_path, exist_ok=True)
        filepath = os.path.join(folder_path, filename)
        processed_file.save(filepath)

        flash(f"Image uploaded successfully! {message}", 'success')
        return f"/uploads/{folder}/{filename}"
    return None

def save_gallery_images(files_dict, folder, keys=['gallery_image_1', 'gallery_image_2', 'gallery_image_3']):
    """Save multiple gallery images with validation and return JSON array"""
    paths = []
    for key in keys:
        file = files_dict.get(key)
        if file and file.filename:
            # Validate and process each image
            success, message, processed_file = validate_and_process_image(file)

            if success:
                filename = f"{int(datetime.now().timestamp())}_{secure_filename(processed_file.filename)}"
                folder_path = os.path.join(app.config['UPLOAD_FOLDER'], folder)
                os.makedirs(folder_path, exist_ok=True)
                filepath = os.path.join(folder_path, filename)
                processed_file.save(filepath)
                paths.append(f"/uploads/{folder}/{filename}")
            else:
                flash(f"Gallery image {key} error: {message}", 'warning')

    return json.dumps(paths) if paths else None

def delete_image_file(image_path):
    """Safely delete image file"""
    try:
        if image_path:
            filepath = image_path.replace('/uploads/', '')
            full_path = os.path.join(app.config['UPLOAD_FOLDER'], filepath)
            if os.path.exists(full_path):
                os.remove(full_path)
    except Exception as e:
        logger.warning(f"Error deleting file: {e}")

# ==================== PUBLIC APIs ====================

@app.route('/api/segments')
def api_segments():
    try:
        segments = Segment.query.filter_by(is_active=True).order_by(Segment.display_order).all()
        return jsonify([s.to_dict() for s in segments])
    except Exception as e:
        logger.exception("api_segments failed")
        return jsonify({'error': 'Something went wrong. Please try again later.'}), 500

@app.route('/api/categories')
def api_all_categories():
    """Get all categories (used in search, filters, etc.)"""
    try:
        categories = Category.query.filter_by(is_active=True).order_by(Category.name).all()
        return jsonify([c.to_dict() for c in categories])
    except Exception as e:
        logger.exception("api_all_categories failed")
        return jsonify({'error': 'Something went wrong. Please try again later.'}), 500

@app.route('/api/categories/<int:segment_id>')
def api_categories(segment_id):
    try:
        categories = Category.query.filter_by(segment_id=segment_id, is_active=True).all()
        return jsonify([c.to_dict() for c in categories])
    except Exception as e:
        logger.exception("categories-by-segment API failed")
        return jsonify({'error': 'Something went wrong. Please try again later.'}), 500

@app.route('/api/menu-data')
def api_menu_data():
    """Optimized endpoint for mega menu - returns segments with their categories"""
    try:
        segments = Segment.query.filter_by(is_active=True).order_by(Segment.display_order).all()
        result = []
        for seg in segments:
            categories = Category.query.filter_by(segment_id=seg.id, is_active=True).all()
            result.append({
                'segment': seg.to_dict(),
                'categories': [c.to_dict() for c in categories]
            })
        return jsonify(result)
    except Exception as e:
        logger.exception("api_menu_data failed")
        return jsonify({'error': 'Something went wrong. Please try again later.'}), 500

@app.route('/api/subcategories/<int:category_id>')
def api_subcategories(category_id):
    try:
        subcategories = Subcategory.query.filter_by(category_id=category_id, is_active=True).all()
        return jsonify([s.to_dict() for s in subcategories])
    except Exception as e:
        logger.exception("subcategories-by-category API failed")
        return jsonify({'error': 'Something went wrong. Please try again later.'}), 500

@app.route('/api/products/<int:subcategory_id>')
def api_products(subcategory_id):
    try:
        products = Product.query.filter_by(subcategory_id=subcategory_id, is_active=True).all()
        return jsonify([p.to_dict() for p in products])
    except Exception as e:
        logger.exception("products-by-subcategory API failed")
        return jsonify({'error': 'Something went wrong. Please try again later.'}), 500

@app.route('/api/direct-products/<int:category_id>')
def api_direct_products(category_id):
    try:
        products = Product.query.filter_by(category_id=category_id, is_active=True).all()
        return jsonify([p.to_dict() for p in products])
    except Exception as e:
        logger.exception("api_direct_products failed")
        return jsonify({'error': 'Something went wrong. Please try again later.'}), 500

@app.route('/api/product/<int:product_id>')
def api_single_product(product_id):
    """Get single product by ID - for dynamic sections"""
    try:
        product = Product.query.get_or_404(product_id)
        product_dict = product.to_dict()

        if product.subcategory:
            product_dict['subcategory_name'] = product.subcategory.name
            if product.subcategory.category:
                product_dict['category_name'] = product.subcategory.category.name
                if product.subcategory.category.segment:
                    product_dict['segment_name'] = product.subcategory.category.segment.name

        return jsonify(product_dict)
    except Exception as e:
        logger.exception("api_single_product failed")
        return jsonify({'error': 'Something went wrong. Please try again later.'}), 500

@app.route('/api/dynamic-sections')
def api_dynamic_sections():
    try:
        sections = DynamicSection.query.filter_by(is_visible=True).order_by(DynamicSection.display_order).all()
        return jsonify([s.to_dict() for s in sections])
    except Exception as e:
        logger.exception("api_dynamic_sections failed")
        return jsonify({'error': 'Something went wrong. Please try again later.'}), 500

@app.route('/admin/get-resources')
@admin_required
def admin_get_resources():
    type = request.args.get('type')
    try:
        if type == 'Categories':
            items = Category.query.all()
            return jsonify([{'id': i.id, 'name': i.name} for i in items])
        elif type == 'Subcategories':
            items = Subcategory.query.all()
            return jsonify([{'id': i.id, 'name': i.name} for i in items])
        elif type == 'Products':
            items = Product.query.all()
            return jsonify([{'id': i.id, 'name': f"{i.name} ({i.product_code})"} for i in items])
        return jsonify([])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/dynamic-section-items/<int:section_id>')
def api_dynamic_section_items(section_id):
    try:
        section = DynamicSection.query.get_or_404(section_id)
        items = []
        import json
        import random
        
        if section.is_automatic:
            # Automatic logic based on automatic_type
            if section.automatic_type == 'best_sellers':
                products = Product.query.filter_by(is_best_selling=True).limit(10).all()
                items = [p.to_dict() for p in products]
            elif section.automatic_type == 'new_arrivals':
                products = Product.query.order_by(Product.created_at.desc()).limit(10).all()
                items = [p.to_dict() for p in products]
            elif section.automatic_type == 'category' and section.parent_type == 'segment':
                categories = Category.query.filter_by(segment_id=section.parent_id, is_active=True).all()
                selected = random.sample(categories, min(8, len(categories)))
                items = [c.to_dict() for c in selected]
            elif section.automatic_type == 'subcategory' and section.parent_type == 'category':
                subcategories = Subcategory.query.filter_by(category_id=section.parent_id, is_active=True).all()
                selected = random.sample(subcategories, min(8, len(subcategories)))
                items = [s.to_dict() for s in selected]
            elif section.automatic_type == 'product' and section.parent_type == 'subcategory':
                products = Product.query.filter_by(subcategory_id=section.parent_id, is_active=True).all()
                selected = random.sample(products, min(8, len(products)))
                items = [p.to_dict() for p in selected]
        else:
            # Manual logic based on display_type and product_ids
            try:
                ids = json.loads(section.product_ids or '[]')
            except:
                ids = []
                
            if section.display_type == 'category':
                for cid in ids:
                    cat = Category.query.get(cid)
                    if cat: items.append({'id': cat.id, 'name': cat.name, 'image_path': cat.image_path})
            elif section.display_type == 'subcategory':
                for sid in ids:
                    sub = Subcategory.query.get(sid)
                    if sub: items.append({'id': sub.id, 'name': sub.name, 'image_path': sub.image_path})
            else: # product
                for pid in ids:
                    prod = Product.query.get(pid)
                    if prod: items.append(prod.to_dict())
                    
        return jsonify({
            'type': section.display_type,
            'items': items
        })
    except Exception as e:
        logger.exception("api_dynamic_section_items failed")
        return jsonify({'error': 'Something went wrong. Please try again later.'}), 500

# ==================== FRONTEND ROUTES ====================

@app.route('/categories/<int:segment_id>')
def categories_page(segment_id):
    """Categories Page - Shows all categories in a segment"""
    try:
        segment = Segment.query.get_or_404(segment_id)
        categories = Category.query.filter_by(segment_id=segment_id).all()

        return render_template('categories.html',
            segment=segment,
            categories=categories
        )
    except Exception as e:
        logger.exception("Failed loading categories page")
        return "Something went wrong. Please try again later.", 404

@app.route('/subcategories/<int:category_id>')
def subcategories_page(category_id):
    """Subcategories Page - Shows all subcategories in a category"""
    try:
        category = Category.query.get_or_404(category_id)
        segment = category.segment
        subcategories = Subcategory.query.filter_by(category_id=category_id, is_active=True).all()

        # SMART ROUTING: only when no active subcategories exist
        if not subcategories:
            seg_slug = segment.name.lower().replace(' ', '-')
            cat_slug = category.name.lower().replace(' ', '-')

            # Check direct products (Path B)
            direct_products = Product.query.filter_by(category_id=category_id, is_active=True).all()

            if len(direct_products) == 1:
                p = direct_products[0]
                prod_slug = p.name.lower().replace(' ', '-')
                return redirect(f'/product/{seg_slug}/{cat_slug}/direct/{prod_slug}/{p.id}')
            elif len(direct_products) > 1:
                return redirect(f'/product-listing/{seg_slug}/{cat_slug}/direct')

        # Default: show subcategory page (existing behaviour — untouched)
        all_subcategories = Subcategory.query.filter_by(category_id=category_id).all()
        direct_products = Product.query.filter_by(category_id=category_id, is_active=True).all()
        return render_template('subcategory.html',
            segment=segment,
            category=category,
            subcategories=all_subcategories,
            direct_products=direct_products
        )
    except Exception as e:
        logger.exception("Failed loading subcategories page")
        return "Something went wrong. Please try again later.", 404

@app.route('/product/<segment_name>/<category_name>/<subcategory_name>/<product_name>/<int:product_id>')
def product_detail(segment_name, category_name, subcategory_name, product_name, product_id):
    """Product Detail Page with Recommendations"""
    try:
        product = Product.query.get_or_404(product_id)
        subcategory = product.subcategory
        category = subcategory.category
        segment = category.segment

        similar_products = Product.query.filter(
            Product.subcategory_id == product.subcategory_id,
            Product.id != product_id
        ).limit(4).all()

        more_from_collection = Product.query.join(Subcategory).join(Category).filter(
            Category.segment_id == segment.id,
            Product.subcategory_id != product.subcategory_id
        ).limit(4).all()

        other_segments = Product.query.join(Subcategory).join(Category).filter(
            Category.segment_id != segment.id
        ).limit(4).all()

        return render_template('product-detail.html',
            product=product,
            segment=segment,
            category=category,
            subcategory=subcategory,
            similar_products=similar_products,
            more_from_collection=more_from_collection,
            other_segments=other_segments
        )
    except Exception as e:
        logger.exception("Failed loading product detail page")
        return "Something went wrong. Please try again later.", 404

    # ==================== MISSING ROUTE - ADD THIS ====================

@app.route('/product/<int:product_id>')
def product_by_id(product_id):
    product = Product.query.get_or_404(product_id)
    if product.subcategory_id:
        sub = product.subcategory
        cat = sub.category
        seg = cat.segment
        seg_slug = seg.name.lower().replace(' ', '-')
        cat_slug = cat.name.lower().replace(' ', '-')
        sub_slug = sub.name.lower().replace(' ', '-')
        prod_slug = product.name.lower().replace(' ', '-')
        return redirect(f'/product/{seg_slug}/{cat_slug}/{sub_slug}/{prod_slug}/{product.id}')
    else:
        cat = product.category
        seg = cat.segment
        seg_slug = seg.name.lower().replace(' ', '-')
        cat_slug = cat.name.lower().replace(' ', '-')
        prod_slug = product.name.lower().replace(' ', '-')
        return redirect(f'/product/{seg_slug}/{cat_slug}/direct/{prod_slug}/{product.id}')

@app.route('/product-listing/<int:subcategory_id>')
def product_listing_by_id(subcategory_id):
    sub = Subcategory.query.get_or_404(subcategory_id)
    cat = sub.category
    seg = cat.segment
    seg_slug = seg.name.lower().replace(' ', '-')
    cat_slug = cat.name.lower().replace(' ', '-')
    sub_slug = sub.name.lower().replace(' ', '-')
    return redirect(f'/product-listing/{seg_slug}/{cat_slug}/{sub_slug}')


@app.route('/product-listing/<segment_name>/<category_name>/<subcategory_name>')
def product_listing_by_slug(segment_name, category_name, subcategory_name):
    try:
        sub = Subcategory.query.join(Category).join(Segment).filter(
            Segment.name.ilike(segment_name.replace('-',' ')),
            Category.name.ilike(category_name.replace('-',' ')),
            Subcategory.name.ilike(subcategory_name.replace('-',' '))
        ).first_or_404()
        page = request.args.get('page', 1, type=int)
        pagination = Product.query.filter_by(subcategory_id=sub.id, is_active=True).paginate(page=page, per_page=24, error_out=False)
        return render_template('products.html',
            subcategory=sub,
            category=sub.category,
            segment=sub.category.segment,
            products=pagination.items,
            pagination=pagination)
    except Exception as e:
        logger.exception("Failed loading product listing by slug")
        return "Something went wrong. Please try again later.", 404

@app.route('/product-listing/all/all/all')
def product_listing_all():
    """Show all products across all categories"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = 24

        # Get all products
        pagination = Product.query.filter_by(is_active=True).paginate(
            page=page, per_page=per_page, error_out=False
        )

        return render_template('products.html',
            subcategory=None,
            category=None,
            segment=None,
            products=pagination.items,
            pagination=pagination,
            page_title="All Products"
        )
    except Exception as e:
        logger.exception("Failed loading all-products listing")
        return "Something went wrong. Please try again later.", 500

@app.route('/search')
def search():
    """Search Page - Searches in products and categories"""
    try:
        query = request.args.get('q', '').strip()

        if not query:
            return render_template('search-results.html',
                query='',
                products=[],
                categories=[],
                total_results=0
            )

        products = Product.query.filter(
            db.or_(
                Product.name.ilike(f'%{query}%'),
                Product.product_code.ilike(f'%{query}%'),
                db.and_(Product.details.isnot(None), Product.details.ilike(f'%{query}%'))
            )
        ).limit(20).all()

        categories = Category.query.filter(
            Category.name.ilike(f'%{query}%')
        ).limit(10).all()

        return render_template('search-results.html',
            query=query,
            products=products,
            categories=categories,
            total_results=len(products) + len(categories)
        )
    except Exception as e:
        logger.exception("Search failed")
        return "Something went wrong. Please try again later.", 500

@app.route('/best-selling')
def best_selling_products():
    """Best Selling Products Page"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = 24

        pagination = Product.query.filter_by(
            is_best_selling=True
        ).paginate(page=page, per_page=per_page, error_out=False)

        return render_template('best-selling.html',
            products=pagination.items,
            pagination=pagination
        )
    except Exception as e:
        logger.exception("Failed loading best-selling products")
        return "Something went wrong. Please try again later.", 500

# ==================== ADMIN AUTH ====================

@app.route('/admin/login', methods=['GET', 'POST'])
@limiter.limit("5 per minute", methods=["POST"])
def admin_login():
    """Admin login - checks .env first, then database"""
    if request.method == 'POST':
        username = request.form.get('email') or ''  # Can be email or username
        password = request.form.get('password') or ''

        # ✅ STEP 1: Check .env credentials FIRST
        env_username = os.getenv('ADMIN_USERNAME')
        env_password = os.getenv('ADMIN_PASSWORD')

        if env_username and env_password:
            username_ok = hmac.compare_digest(username.encode(), env_username.encode())
            password_ok = hmac.compare_digest(password.encode(), env_password.encode())
            if username_ok and password_ok:
                # Create temporary session for .env admin
                session['admin_user_id'] = 'env_admin'
                session['is_env_admin'] = True
                session['email'] = env_username  # ← ADD THIS LINE
                session.permanent = True
                flash(f'Welcome back, {username}! (.env admin)', 'success')
                return redirect(url_for('admin_dashboard'))

        # ✅ STEP 2: Check database users
        user = AdminUser.query.filter_by(email=username).first()

        if user and user.check_password(password) and user.is_active:
            session['admin_user_id'] = user.id
            session['is_env_admin'] = False
            session['email'] = user.email  # ← ADD THIS LINE
            session.permanent = True
            flash(f'Welcome back, {user.email}!', 'success')
            return redirect(url_for('admin_dashboard'))

        return render_template('admin/login.html', error="Invalid username or password")

    # If already logged in, redirect to dashboard
    if 'admin_user_id' in session:
        return redirect(url_for('admin_dashboard'))

    return render_template('admin/login.html')

@app.route('/admin/logout')
def admin_logout():
    """Logout current user"""
    session.pop('admin_user_id', None)
    flash('You have been logged out successfully', 'success')
    return redirect(url_for('admin_login'))

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    """Admin dashboard - accessible to all authenticated users"""
    # ✨ Get latest 5 inquiries for activity feed
    recent_inquiries = ContactInquiry.query.order_by(ContactInquiry.created_at.desc()).limit(5).all()

    # 📊 Inventory Chart Data
    segments = Segment.query.all()
    segment_labels = [s.name for s in segments]
    segment_counts = []
    
    for seg in segments:
        count = Product.query.join(Subcategory, Product.subcategory_id == Subcategory.id)\
                           .join(Category, Subcategory.category_id == Category.id)\
                           .filter(Category.segment_id == seg.id)\
                           .count()
        segment_counts.append(count)

    return render_template('admin/dashboard.html',
        segment_count=Segment.query.count(),
        category_count=Category.query.count(),
        subcategory_count=Subcategory.query.count(),
        product_count=Product.query.count(),
        recent_inquiries=recent_inquiries,
        segment_labels=segment_labels,
        segment_counts=segment_counts
    )

# ==================== USER MANAGEMENT (ADMIN ONLY) ====================

@app.route('/admin/user-management', methods=['GET'])
@app.route('/admin/users', methods=['GET'])
@admin_required
def admin_user_management():
    """User management page - admin only"""
    users = AdminUser.query.order_by(AdminUser.created_at.desc()).all()
    return render_template('admin/user-management.html', users=users)

@app.route('/admin/user-management/add', methods=['POST'])
@admin_required
def admin_add_user():
    """Add new admin user - admin only"""
    try:
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role')

        # Validate inputs
        if not email or not password or not role:
            flash('All fields are required', 'error')
            return redirect(url_for('admin_user_management'))

        if role not in ['admin', 'manager']:
            flash('Invalid role selected', 'error')
            return redirect(url_for('admin_user_management'))

        # Check if user already exists
        existing = AdminUser.query.filter_by(email=email).first()
        if existing:
            flash(f'User with email {email} already exists', 'error')
            return redirect(url_for('admin_user_management'))

        # Create new user
        new_user = AdminUser(email=email, role=role)
        new_user.set_password(password)

        db.session.add(new_user)
        db.session.commit()

        flash(f'User {email} created successfully with role: {role}', 'success')
        return redirect(url_for('admin_user_management'))

    except Exception as e:
        db.session.rollback()
        flash(f'Error creating user: {str(e)}', 'error')
        return redirect(url_for('admin_user_management'))

@app.route('/admin/user-management/edit/<int:id>', methods=['GET', 'POST'])
@admin_required
def admin_edit_user(id):
    """Edit existing user - admin only"""
    user = AdminUser.query.get_or_404(id)

    if request.method == 'POST':
        try:
            email = request.form.get('email')
            role = request.form.get('role')
            password = request.form.get('password')
            is_active = bool(request.form.get('is_active'))

            # Validate
            if not email or not role:
                flash('Email and role are required', 'error')
                return render_template('admin/edit-user.html', user=user)

            if role not in ['admin', 'manager']:
                flash('Invalid role selected', 'error')
                return render_template('admin/edit-user.html', user=user)

            # Check if email is taken by another user
            existing = AdminUser.query.filter(
                AdminUser.email == email,
                AdminUser.id != id
            ).first()

            if existing:
                flash(f'Email {email} is already in use', 'error')
                return render_template('admin/edit-user.html', user=user)

            # Update user
            user.email = email
            user.role = role
            user.is_active = is_active

            # Update password if provided
            if password and password.strip():
                user.set_password(password)

            db.session.commit()
            flash(f'User {email} updated successfully', 'success')
            return redirect(url_for('admin_user_management'))

        except Exception as e:
            db.session.rollback()
            flash(f'Error updating user: {str(e)}', 'error')
            return render_template('admin/edit-user.html', user=user)

    return render_template('admin/edit-user.html', user=user)

@app.route('/admin/user-management/delete/<int:id>', methods=['POST'])
@admin_required
def admin_delete_user(id):
    """Delete user - admin only"""
    try:
        user = AdminUser.query.get_or_404(id)

        # Prevent deleting yourself
        if user.id == session.get('admin_user_id'):
            flash('You cannot delete your own account', 'error')
            return redirect(url_for('admin_user_management'))

        email = user.email
        db.session.delete(user)
        db.session.commit()

        flash(f'User {email} deleted successfully', 'success')
        return redirect(url_for('admin_user_management'))

    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting user: {str(e)}', 'error')
        return redirect(url_for('admin_user_management'))

# ==================== SEGMENTS (ADMIN ONLY) ====================

@app.route('/admin/add-segment', methods=['GET', 'POST'])
@admin_required
def admin_add_segment():
    if request.method == 'POST':
        try:
            name = request.form.get('name')
            segment_code = request.form.get('segment_code')
            image = request.files.get('image')
            
            # ✅ ADD VALIDATION
            if not name or not name.strip():
                flash('❌ Segment name is required!', 'error')
                segments = Segment.query.order_by(Segment.created_at.desc()).all()
                return render_template('admin/add-segment.html', segments=segments)
            
            if not image or not image.filename:
                flash('❌ Primary image is required!', 'error')
                segments = Segment.query.order_by(Segment.created_at.desc()).all()
                return render_template('admin/add-segment.html', segments=segments)
            
            # Duplicate check
            existing = Segment.query.filter(
                db.or_(
                    Segment.name.ilike(name),
                    Segment.segment_code == segment_code
                )
            ).first()
            if existing:
                flash(f'❌ Segment "{existing.name}" already exists! Go to edit page to modify it.', 'error')
                segments = Segment.query.order_by(Segment.created_at.desc()).all()
                return render_template('admin/add-segment.html', segments=segments)
            
            logger.debug(f"Attempting to add segment: {name}")

            image_path = save_single_image(image, 'segments')

            if not image_path:
                flash('❌ Failed to save image!', 'error')
                segments = Segment.query.order_by(Segment.created_at.desc()).all()
                return render_template('admin/add-segment.html', segments=segments)

            logger.info(f"Image saved: {image_path}")

            segment = Segment(
                name=name,
                segment_code=segment_code or None,
                image_path=image_path
            )
            db.session.add(segment)
            db.session.commit()

            logger.info(f"Segment saved to DB: ID={segment.id}")

            flash(f'Segment "{name}" added successfully!', 'success')
            segments = Segment.query.order_by(Segment.created_at.desc()).all()
            return render_template('admin/add-segment.html', segments=segments)

        except Exception as e:
            db.session.rollback()
            logger.exception("Failed to add segment")

            flash(f'Error: {str(e)}', 'error')
            segments = Segment.query.order_by(Segment.created_at.desc()).all()
            return render_template('admin/add-segment.html', segments=segments)

    segments = Segment.query.order_by(Segment.created_at.desc()).all()
    return render_template('admin/add-segment.html', segments=segments)


@app.route('/admin/edit-segment/<int:id>', methods=['GET', 'POST'])
@admin_required
def admin_edit_segment(id):
    segment = Segment.query.get_or_404(id)

    if request.method == 'POST':
        try:
            segment.name = request.form.get('name')
            segment.segment_code = request.form.get('segment_code') or None

            # Handle primary image replacement
            new_image = request.files.get('image')
            if new_image and new_image.filename:
                if segment.image_path:
                    delete_image_file(segment.image_path)
                segment.image_path = save_single_image(new_image, 'segments')

            db.session.commit()
            flash(f'Segment "{segment.name}" updated successfully!', 'success')
            return redirect(url_for('admin_add_segment'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error: {str(e)}', 'error')
            return render_template('admin/edit-segment.html', segment=segment)

    return render_template('admin/edit-segment.html', segment=segment)

@app.route('/admin/delete-segment/<int:id>', methods=['POST'])
@admin_required
def admin_delete_segment(id):
    try:
        segment = Segment.query.get_or_404(id)
        name = segment.name
        if segment.image_path:
            delete_image_file(segment.image_path)
        db.session.delete(segment)
        db.session.commit()
        flash(f'Segment "{name}" deleted successfully', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error: {str(e)}', 'error')

    return redirect(url_for('admin_add_segment'))

@app.route('/admin/toggle-segment/<int:id>', methods=['POST'])
@admin_required
def admin_toggle_segment(id):
    try:
        segment = Segment.query.get_or_404(id)
        segment.is_active = not segment.is_active

        if not segment.is_active:
            for category in segment.categories:
                category.is_active = False
                for subcategory in category.subcategories:
                    subcategory.is_active = False
                    for product in subcategory.products:
                        product.is_active = False

        db.session.commit()
        status = "activated" if segment.is_active else "deactivated"
        flash(f'Segment "{segment.name}" {status} successfully', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error: {str(e)}', 'error')

    return redirect(url_for('admin_add_segment'))

# ==================== CATEGORIES (ADMIN ONLY) ====================

@app.route('/admin/add-category', methods=['GET', 'POST'])
@admin_required
def admin_add_category():
    segments = Segment.query.all()

    if request.method == 'POST':
        try:
            name = request.form.get('name')
            category_code = request.form.get('category_code')
            segment_id = request.form.get('segment_id')

            # Duplicate check
            existing = Category.query.filter(
                db.or_(
                    Category.name.ilike(name),
                    Category.category_code == category_code
                )
            ).first()
            if existing:
                flash(f'❌ Category "{existing.name}" already exists! Go to edit page to modify it.', 'error')
                categories = Category.query.order_by(Category.created_at.desc()).all()
                return render_template('admin/add-category.html', segments=segments, categories=categories)
            
            primary_image = save_single_image(request.files.get('image'), 'categories')
            gallery_images = save_gallery_images(request.files, 'categories')

            category = Category(
                name=name,
                category_code=category_code or None,
                segment_id=int(segment_id),
                image_path=primary_image,
                gallery_images=gallery_images
            )
            db.session.add(category)
            db.session.commit()

            flash(f'Category "{name}" added successfully!', 'success')
            categories = Category.query.order_by(Category.created_at.desc()).all()
            return render_template('admin/add-category.html', segments=segments, categories=categories)

        except Exception as e:  # ✅ ADD THIS BLOCK
            db.session.rollback()
            flash(f'Error: {str(e)}', 'error')
            categories = Category.query.order_by(Category.created_at.desc()).all()
            return render_template('admin/add-category.html', segments=segments, categories=categories)

    categories = Category.query.order_by(Category.created_at.desc()).all()
    return render_template('admin/add-category.html', segments=segments, categories=categories)

@app.route('/admin/edit-category/<int:id>', methods=['GET', 'POST'])
@admin_required
def admin_edit_category(id):
    category = Category.query.get_or_404(id)
    segments = Segment.query.all()

    if request.method == 'POST':
        try:
            category.name = request.form.get('name')
            category.category_code = request.form.get('category_code') or None
            category.segment_id = int(request.form.get('segment_id'))

            # Handle primary image replacement
            new_image = request.files.get('image')
            if new_image and new_image.filename:
                if category.image_path:
                    delete_image_file(category.image_path)
                category.image_path = save_single_image(new_image, 'categories')

            # ✅ NEW: Handle gallery images individually (slot-by-slot)
            gallery_images = []
            if category.gallery_images:
                gallery_images = json.loads(category.gallery_images)

            # Ensure we have 4 slots (pad with None if needed)
            while len(gallery_images) < 4:
                gallery_images.append(None)

            # Check each gallery slot (1-4) individually
            for i in range(1, 5):
                field_name = f'gallery_image_{i}'
                file = request.files.get(field_name)

                if file and file.filename:
                    # Delete old image at this position
                    if gallery_images[i-1]:
                        delete_image_file(gallery_images[i-1])

                    # Save new image
                    new_path = save_single_image(file, 'categories')
                    gallery_images[i-1] = new_path

            # Remove trailing None values for cleaner storage
            while gallery_images and gallery_images[-1] is None:
                gallery_images.pop()

            # Save updated gallery (or None if empty)
            category.gallery_images = json.dumps(gallery_images) if gallery_images else None

            db.session.commit()
            flash(f'Category "{category.name}" updated successfully!', 'success')
            return redirect(url_for('admin_add_category'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error: {str(e)}', 'error')
            return render_template('admin/edit-category.html', category=category, segments=segments)

    return render_template('admin/edit-category.html', category=category, segments=segments)

@app.route('/admin/delete-category/<int:id>', methods=['POST'])
@admin_required
def admin_delete_category(id):
    try:
        category = Category.query.get_or_404(id)
        name = category.name
        if category.image_path:
            delete_image_file(category.image_path)
        if category.gallery_images:
            for img in json.loads(category.gallery_images):
                delete_image_file(img)
        db.session.delete(category)
        db.session.commit()
        flash(f'Category "{name}" deleted successfully', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error: {str(e)}', 'error')

    return redirect(url_for('admin_add_category'))

@app.route('/admin/toggle-category/<int:id>', methods=['POST'])
@admin_required
def admin_toggle_category(id):
    try:
        category = Category.query.get_or_404(id)
        category.is_active = not category.is_active

        if not category.is_active:
            for subcategory in category.subcategories:
                subcategory.is_active = False
                for product in subcategory.products:
                    product.is_active = False

        db.session.commit()
        status = "activated" if category.is_active else "deactivated"
        flash(f'Category "{category.name}" {status} successfully', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error: {str(e)}', 'error')

    return redirect(url_for('admin_add_category'))

# ==================== SUBCATEGORIES (MANAGER ALLOWED) ====================

@app.route('/admin/add-subcategory', methods=['GET', 'POST'])
@manager_allowed
def admin_add_subcategory():
    categories = Category.query.all()

    if request.method == 'POST':
        try:
            name = request.form.get('name')
            subcategory_code = request.form.get('subcategory_code')
            category_id = request.form.get('category_id')

            # Duplicate check
            existing = Subcategory.query.filter(
                db.or_(
                    Subcategory.name.ilike(name),
                    Subcategory.subcategory_code == subcategory_code
                )
            ).first()
            if existing:
                flash(f'❌ Subcategory "{existing.name}" already exists! Go to edit page to modify it.', 'error')
                subcategories = Subcategory.query.order_by(Subcategory.created_at.desc()).all()
                return render_template('admin/add-subcategory.html', categories=categories, subcategories=subcategories)

            primary_image = save_single_image(request.files.get('image'), 'subcategories')
            gallery_images = save_gallery_images(request.files, 'subcategories')

            subcategory = Subcategory(
                name=name,
                subcategory_code=subcategory_code or None,
                category_id=int(category_id),
                image_path=primary_image,
                gallery_images=gallery_images
            )
            db.session.add(subcategory)
            db.session.commit()

            flash(f'Subcategory "{name}" added successfully!', 'success')
            subcategories = Subcategory.query.order_by(Subcategory.created_at.desc()).all()
            return render_template('admin/add-subcategory.html', categories=categories, subcategories=subcategories)
        except Exception as e:
            db.session.rollback()
            flash(f'Error: {str(e)}', 'error')
            subcategories = Subcategory.query.order_by(Subcategory.created_at.desc()).all()
            return render_template('admin/add-subcategory.html', categories=categories, subcategories=subcategories)

    subcategories = Subcategory.query.order_by(Subcategory.created_at.desc()).all()
    return render_template('admin/add-subcategory.html', categories=categories, subcategories=subcategories)

@app.route('/admin/edit-subcategory/<int:id>', methods=['GET', 'POST'])
@manager_allowed
def admin_edit_subcategory(id):
    subcategory = Subcategory.query.get_or_404(id)
    categories = Category.query.all()

    if request.method == 'POST':
        try:
            subcategory.name = request.form.get('name')
            subcategory.subcategory_code = request.form.get('subcategory_code') or None
            subcategory.category_id = int(request.form.get('category_id'))

            # Handle primary image replacement
            new_image = request.files.get('image')
            if new_image and new_image.filename:
                if subcategory.image_path:
                    delete_image_file(subcategory.image_path)
                subcategory.image_path = save_single_image(new_image, 'subcategories')

            # ✅ NEW: Handle gallery images individually (slot-by-slot)
            gallery_images = []
            if subcategory.gallery_images:
                gallery_images = json.loads(subcategory.gallery_images)

            # Ensure we have 4 slots (pad with None if needed)
            while len(gallery_images) < 4:
                gallery_images.append(None)

            # Check each gallery slot (1-4) individually
            for i in range(1, 5):
                field_name = f'gallery_image_{i}'
                file = request.files.get(field_name)

                if file and file.filename:
                    # Delete old image at this position
                    if gallery_images[i-1]:
                        delete_image_file(gallery_images[i-1])

                    # Save new image
                    new_path = save_single_image(file, 'subcategories')
                    gallery_images[i-1] = new_path

            # Remove trailing None values for cleaner storage
            while gallery_images and gallery_images[-1] is None:
                gallery_images.pop()

            # Save updated gallery (or None if empty)
            subcategory.gallery_images = json.dumps(gallery_images) if gallery_images else None

            db.session.commit()
            flash(f'Subcategory "{subcategory.name}" updated successfully!', 'success')
            return redirect(url_for('admin_add_subcategory'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error: {str(e)}', 'error')
            return render_template('admin/edit-subcategory.html', subcategory=subcategory, categories=categories)

    return render_template('admin/edit-subcategory.html', subcategory=subcategory, categories=categories)

@app.route('/admin/delete-subcategory/<int:id>', methods=['POST'])
@manager_allowed
def admin_delete_subcategory(id):
    try:
        subcategory = Subcategory.query.get_or_404(id)
        name = subcategory.name
        if subcategory.image_path:
            delete_image_file(subcategory.image_path)
        if subcategory.gallery_images:
            for img in json.loads(subcategory.gallery_images):
                delete_image_file(img)
        db.session.delete(subcategory)
        db.session.commit()
        flash(f'Subcategory "{name}" deleted successfully', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error: {str(e)}', 'error')

    return redirect(url_for('admin_add_subcategory'))

@app.route('/admin/toggle-subcategory/<int:id>', methods=['POST'])
@manager_allowed
def admin_toggle_subcategory(id):
    try:
        subcategory = Subcategory.query.get_or_404(id)
        subcategory.is_active = not subcategory.is_active

        if not subcategory.is_active:
            for product in subcategory.products:
                product.is_active = False

        db.session.commit()
        status = "activated" if subcategory.is_active else "deactivated"
        flash(f'Subcategory "{subcategory.name}" {status} successfully', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error: {str(e)}', 'error')

    return redirect(url_for('admin_add_subcategory'))

# ==================== PRODUCTS (MANAGER ALLOWED) ====================

@app.route('/admin/add-product', methods=['GET', 'POST'])
@manager_allowed
def admin_add_product():
    subcategories = Subcategory.query.all()
    categories = Category.query.all()

    if request.method == 'POST':
        try:
            name = request.form.get('name')
            product_code = request.form.get('product_code')
            details = request.form.get('details')
            parent_type = request.form.get('parent_type')
            
            # Duplicate check
            if product_code:
                existing = Product.query.filter_by(product_code=product_code).first()
                if existing:
                    flash(f'❌ Product with code "{product_code}" already exists! Go to edit page to modify it.', 'error')
                    products = Product.query.order_by(Product.created_at.desc()).all()
                    return render_template('admin/add-product.html', subcategories=subcategories, categories=categories, products=products)
            
            logger.debug(f"Attempting to add product: {name} (parent type: {parent_type})")

            primary_image = save_single_image(request.files.get('primary_image'), 'products/primary')

            if not primary_image:
                logger.warning("Failed to save primary image for new product")
                flash('❌ Failed to save primary image!', 'error')
                subcategories = Subcategory.query.all()
                categories = Category.query.all()
                products = Product.query.order_by(Product.created_at.desc()).all()
                return render_template('admin/add-product.html', subcategories=subcategories, categories=categories, products=products)

            logger.info(f"Primary image saved: {primary_image}")
            
            gallery_images = save_gallery_images(
                request.files, 'products/gallery',
                keys=['gallery_image_1', 'gallery_image_2', 'gallery_image_3', 'gallery_image_4']
            )

            if parent_type == 'category':
                category_id = request.form.get('category_id')
                product = Product(
                    name=name,
                    product_code=product_code,
                    details=details,
                    subcategory_id=None,
                    category_id=int(category_id),
                    primary_image=primary_image,
                    secondary_images=gallery_images,
                    is_best_selling=bool(request.form.get('is_best_selling')),
                    is_assured=bool(request.form.get('is_assured')),
                    rating=float(request.form.get('rating', 0))
                )
            else:
                subcategory_id = request.form.get('subcategory_id')
                product = Product(
                    name=name,
                    product_code=product_code,
                    details=details,
                    subcategory_id=int(subcategory_id),
                    category_id=None,
                    primary_image=primary_image,
                    secondary_images=gallery_images,
                    is_best_selling=bool(request.form.get('is_best_selling')),
                    is_assured=bool(request.form.get('is_assured')),
                    rating=float(request.form.get('rating', 0))
                )

            db.session.add(product)
            db.session.commit()
            
            logger.info(f"Product saved to DB: ID={product.id}")

            flash(f'Product "{name}" added successfully!', 'success')
            
            subcategories = Subcategory.query.all()
            categories = Category.query.all()
            products = Product.query.order_by(Product.created_at.desc()).all()
            
            return render_template('admin/add-product.html', subcategories=subcategories, categories=categories, products=products)
            
        except Exception as e:
            db.session.rollback()
            logger.exception("Failed to add product")

            flash(f'Error: {str(e)}', 'error')

            subcategories = Subcategory.query.all()
            categories = Category.query.all()
            products = Product.query.order_by(Product.created_at.desc()).all()

            return render_template('admin/add-product.html', subcategories=subcategories, categories=categories, products=products)

    products = Product.query.order_by(Product.created_at.desc()).all()
    return render_template('admin/add-product.html', subcategories=subcategories, categories=categories, products=products)

@app.route('/admin/edit-product/<int:id>', methods=['GET', 'POST'])
@manager_allowed
def admin_edit_product(id):
    product = Product.query.get_or_404(id)
    subcategories = Subcategory.query.all()
    categories = Category.query.all()

    if request.method == 'POST':
        try:
            product.name = request.form.get('name')
            product.product_code = request.form.get('product_code')
            product.details = request.form.get('details')
            product.is_best_selling = bool(request.form.get('is_best_selling'))
            product.is_assured = bool(request.form.get('is_assured'))
            product.rating = float(request.form.get('rating', 0))

            parent_type = request.form.get('parent_type')
            if parent_type == 'category':
                product.subcategory_id = None
                product.category_id = int(request.form.get('category_id'))
            else:
                product.subcategory_id = int(request.form.get('subcategory_id'))
                product.category_id = None

            # Handle primary image replacement
            new_primary = request.files.get('primary_image')
            if new_primary and new_primary.filename:
                if product.primary_image:
                    delete_image_file(product.primary_image)
                product.primary_image = save_single_image(new_primary, 'products/primary')

            # Handle gallery images slot-by-slot
            gallery_images = []
            if product.secondary_images:
                gallery_images = json.loads(product.secondary_images)
            while len(gallery_images) < 4:
                gallery_images.append(None)
            for i in range(1, 5):
                file = request.files.get(f'gallery_image_{i}')
                if file and file.filename:
                    if gallery_images[i-1]:
                        delete_image_file(gallery_images[i-1])
                    gallery_images[i-1] = save_single_image(file, 'products/gallery')
            while gallery_images and gallery_images[-1] is None:
                gallery_images.pop()
            product.secondary_images = json.dumps(gallery_images) if gallery_images else None

            db.session.commit()
            flash(f'Product "{product.name}" updated successfully!', 'success')
            return redirect(url_for('admin_add_product'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error: {str(e)}', 'error')
            return render_template('admin/edit-product.html', product=product, subcategories=subcategories, categories=categories)

    return render_template('admin/edit-product.html', product=product, subcategories=subcategories, categories=categories)

@app.route('/admin/delete-product/<int:id>', methods=['POST'])
@manager_allowed
def admin_delete_product(id):
    try:
        product = Product.query.get_or_404(id)
        name = product.name
        if product.primary_image:
            delete_image_file(product.primary_image)
        if product.secondary_images:
            for img in json.loads(product.secondary_images):
                delete_image_file(img)
        db.session.delete(product)
        db.session.commit()
        flash(f'Product "{name}" deleted successfully', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error: {str(e)}', 'error')

    return redirect(url_for('admin_add_product'))

@app.route('/admin/toggle-product/<int:id>', methods=['POST'])
@manager_allowed
def admin_toggle_product(id):
    try:
        product = Product.query.get_or_404(id)
        product.is_active = not product.is_active
        db.session.commit()
        status = "activated" if product.is_active else "deactivated"
        flash(f'Product "{product.name}" {status} successfully', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error: {str(e)}', 'error')

    return redirect(url_for('admin_add_product'))

# ==================== DYNAMIC SECTIONS (ADMIN ONLY) ====================

@app.route('/admin/dynamic-section', methods=['GET', 'POST'])
@admin_required
def admin_dynamic_section():
    if request.method == 'POST':
        try:
            title = request.form.get('title')
            subtitle = request.form.get('subtitle')
            is_visible = bool(request.form.get('is_visible'))

            section_mode = request.form.get('section_mode', 'manual')

            if section_mode == 'automatic':
                automatic_type = request.form.get('automatic_type')
                parent_id = request.form.get('parent_id')
                parent_type = request.form.get('parent_type')

                section = DynamicSection(
                    title=title,
                    subtitle=subtitle,
                    display_type=automatic_type,
                    is_visible=is_visible,
                    is_automatic=True,
                    automatic_type=automatic_type,
                    parent_id=int(parent_id) if parent_id else None,
                    parent_type=parent_type,
                    product_ids=None
                )
            else:
                display_type = request.form.get('display_type', 'product')
                product_ids = request.form.get('product_ids')

                section = DynamicSection(
                    title=title,
                    subtitle=subtitle,
                    display_type=display_type,
                    product_ids=product_ids,
                    is_visible=is_visible,
                    is_automatic=False
                )

            db.session.add(section)
            db.session.commit()

            flash('Section created successfully!', 'success')
            sections = DynamicSection.query.order_by(DynamicSection.display_order).all()
            sections_json = [s.to_dict() for s in sections]
            return render_template('admin/dynamic-section.html', sections=sections, sections_json=sections_json)
        except Exception as e:
            db.session.rollback()
            flash(f'Error: {str(e)}', 'error')
            sections = DynamicSection.query.order_by(DynamicSection.display_order).all()
            sections_json = [s.to_dict() for s in sections]
            return render_template('admin/dynamic-section.html', sections=sections, sections_json=sections_json)

    sections = DynamicSection.query.order_by(DynamicSection.display_order).all()
    sections_json = [s.to_dict() for s in sections]
    return render_template('admin/dynamic-section.html', sections=sections, sections_json=sections_json)

@app.route('/admin/edit-dynamic-section/<int:id>', methods=['GET', 'POST'])
@admin_required
def admin_edit_dynamic_section(id):
    section = DynamicSection.query.get_or_404(id)

    if request.method == 'POST':
        try:
            section.title = request.form.get('title')
            section.subtitle = request.form.get('subtitle')
            section.is_visible = bool(request.form.get('is_visible'))

            section_mode = request.form.get('section_mode', 'manual')

            if section_mode == 'automatic':
                section.automatic_type = request.form.get('automatic_type')
                section.parent_id = int(request.form.get('parent_id')) if request.form.get('parent_id') else None
                section.parent_type = request.form.get('parent_type')
                section.display_type = request.form.get('automatic_type')
                section.is_automatic = True
                section.product_ids = None
            else:
                section.display_type = request.form.get('display_type', 'product')
                section.product_ids = request.form.get('product_ids')
                section.is_automatic = False
                section.automatic_type = None
                section.parent_id = None
                section.parent_type = None

            db.session.commit()
            flash('Section updated successfully!', 'success')
            return redirect(url_for('admin_dynamic_section'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error: {str(e)}', 'error')
            return render_template('admin/edit-dynamic-section.html', section=section)

    return render_template('admin/edit-dynamic-section.html', section=section)

@app.route('/admin/toggle-section/<int:id>', methods=['POST'])
@admin_required
def admin_toggle_section(id):
    try:
        section = DynamicSection.query.get_or_404(id)
        section.is_visible = not section.is_visible
        db.session.commit()
        status = "visible" if section.is_visible else "hidden"
        flash(f'Section "{section.title}" is now {status}', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error: {str(e)}', 'error')

    return redirect(url_for('admin_dynamic_section'))

@app.route('/admin/delete-dynamic-section/<int:id>', methods=['POST'])
@admin_required
def admin_delete_dynamic_section(id):
    try:
        section = DynamicSection.query.get_or_404(id)
        title = section.title
        db.session.delete(section)
        db.session.commit()
        flash(f'Section "{title}" deleted successfully', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error: {str(e)}', 'error')

    return redirect(url_for('admin_dynamic_section'))

# ==================== BULK ACTIONS ====================

@app.route('/admin/bulk-segment-action', methods=['POST'])
@admin_required
def bulk_segment_action():
    action = request.form.get('action')
    segment_ids = request.form.get('segment_ids', '')

    if not segment_ids:
        flash('No segments selected', 'error')
        return redirect(url_for('admin_add_segment'))

    ids = [int(id.strip()) for id in segment_ids.split(',') if id.strip()]

    if action == 'delete':
        for seg_id in ids:
            segment = Segment.query.get(seg_id)
            if segment:
                db.session.delete(segment)
        db.session.commit()
        flash(f'Successfully deleted {len(ids)} segment(s)', 'success')

    elif action == 'activate':
        for seg_id in ids:
            segment = Segment.query.get(seg_id)
            if segment:
                segment.is_active = True
        db.session.commit()
        flash(f'Successfully activated {len(ids)} segment(s)', 'success')

    elif action == 'deactivate':
        for seg_id in ids:
            segment = Segment.query.get(seg_id)
            if segment:
                segment.is_active = False
                for category in segment.categories:
                    category.is_active = False
                    for subcategory in category.subcategories:
                        subcategory.is_active = False
                        for product in subcategory.products:
                            product.is_active = False
        db.session.commit()
        flash(f'Successfully deactivated {len(ids)} segment(s) and all nested items', 'success')

    return redirect(url_for('admin_add_segment'))

@app.route('/admin/bulk-category-action', methods=['POST'])
@admin_required
def bulk_category_action():
    action = request.form.get('action')
    category_ids = request.form.get('category_ids', '')

    if not category_ids:
        flash('No categories selected', 'error')
        return redirect(url_for('admin_add_category'))

    ids = [int(id.strip()) for id in category_ids.split(',') if id.strip()]

    if action == 'delete':
        for cat_id in ids:
            category = Category.query.get(cat_id)
            if category:
                db.session.delete(category)
        db.session.commit()
        flash(f'Successfully deleted {len(ids)} category/categories', 'success')

    elif action == 'activate':
        for cat_id in ids:
            category = Category.query.get(cat_id)
            if category:
                category.is_active = True
        db.session.commit()
        flash(f'Successfully activated {len(ids)} category/categories', 'success')

    elif action == 'deactivate':
        for cat_id in ids:
            category = Category.query.get(cat_id)
            if category:
                category.is_active = False
                for subcategory in category.subcategories:
                    subcategory.is_active = False
                    for product in subcategory.products:
                        product.is_active = False
        db.session.commit()
        flash(f'Successfully deactivated {len(ids)} category/categories and all nested items', 'success')

    return redirect(url_for('admin_add_category'))

@app.route('/admin/bulk-subcategory-action', methods=['POST'])
@manager_allowed
def bulk_subcategory_action():
    action = request.form.get('action')
    subcategory_ids = request.form.get('subcategory_ids', '')

    if not subcategory_ids:
        flash('No subcategories selected', 'error')
        return redirect(url_for('admin_add_subcategory'))

    ids = [int(id.strip()) for id in subcategory_ids.split(',') if id.strip()]

    if action == 'delete':
        for sub_id in ids:
            subcategory = Subcategory.query.get(sub_id)
            if subcategory:
                db.session.delete(subcategory)
        db.session.commit()
        flash(f'Successfully deleted {len(ids)} subcategory/subcategories', 'success')

    elif action == 'activate':
        for sub_id in ids:
            subcategory = Subcategory.query.get(sub_id)
            if subcategory:
                subcategory.is_active = True
        db.session.commit()
        flash(f'Successfully activated {len(ids)} subcategory/subcategories', 'success')

    elif action == 'deactivate':
        for sub_id in ids:
            subcategory = Subcategory.query.get(sub_id)
            if subcategory:
                subcategory.is_active = False
                for product in subcategory.products:
                    product.is_active = False
        db.session.commit()
        flash(f'Successfully deactivated {len(ids)} subcategory/subcategories and all products', 'success')

    return redirect(url_for('admin_add_subcategory'))

@app.route('/admin/bulk-product-action', methods=['POST'])
@manager_allowed
def bulk_product_action():
    action = request.form.get('action')
    product_ids = request.form.get('product_ids', '')

    if not product_ids:
        flash('No products selected', 'error')
        return redirect(url_for('admin_add_product'))

    ids = [int(id.strip()) for id in product_ids.split(',') if id.strip()]

    if action == 'delete':
        for prod_id in ids:
            product = Product.query.get(prod_id)
            if product:
                db.session.delete(product)
        db.session.commit()
        flash(f'Successfully deleted {len(ids)} product(s)', 'success')

    elif action == 'activate':
        for prod_id in ids:
            product = Product.query.get(prod_id)
            if product:
                product.is_active = True
        db.session.commit()
        flash(f'Successfully activated {len(ids)} product(s)', 'success')

    elif action == 'deactivate':
        for prod_id in ids:
            product = Product.query.get(prod_id)
            if product:
                product.is_active = False
        db.session.commit()
        flash(f'Successfully deactivated {len(ids)} product(s)', 'success')

    return redirect(url_for('admin_add_product'))

# ==================== OTHER ROUTES ====================

@app.route('/admin/all-data-view')
@login_required
def admin_all_data_view():
    segments = Segment.query.order_by(Segment.name).all()
    categories = Category.query.order_by(Category.name).all()
    subcategories = Subcategory.query.order_by(Subcategory.name).all()
    products = Product.query.order_by(Product.created_at.desc()).all()

    combined_data = []

    for s in segments:
        combined_data.append({
            '_id': s.id,
            'name': s.name,
            'type': 'Segments',
            'parent_name': 'Global',
            'image_url': s.image_path,
            'edit_url': f'/admin/edit-segment/{s.id}'
        })

    for c in categories:
        combined_data.append({
            '_id': c.id,
            'name': c.name,
            'type': 'Categories',
            'parent_name': c.segment.name if c.segment else 'Unknown',
            'image_url': c.image_path,
            'edit_url': f'/admin/edit-category/{c.id}'
        })

    for sc in subcategories:
        combined_data.append({
            '_id': sc.id,
            'name': sc.name,
            'type': 'Subcategories',
            'parent_name': sc.category.name if sc.category else 'Unknown',
            'image_url': sc.image_path,
            'edit_url': f'/admin/edit-subcategory/{sc.id}'
        })

    for p in products:
        combined_data.append({
            '_id': p.id,
            'name': p.name,
            'type': 'Products',
            'parent_name': p.subcategory.name if p.subcategory else (p.category.name if p.category else 'Direct'),
            'image_url': p.primary_image,
            'edit_url': f'/admin/edit-product/{p.id}'
        })

    return render_template('admin/all-data-view.html', combined_data=combined_data)

# ==================== USER MANUAL ====================

@app.route('/admin/manual')
@login_required
def admin_user_manual():
    """User manual page - accessible to all authenticated users"""
    return render_template('admin/user_manual.html')

# ==================== PUBLIC ROUTES ====================

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/privacy-policy')
def privacy_policy():
    return render_template('privacy-policy.html')

@app.route('/terms-conditions')
def terms_conditions():
    return render_template('terms-conditions.html')

@app.route('/api/get-categories-by-segment/<int:segment_id>')
def get_categories_by_segment(segment_id):
    try:
        categories = Category.query.filter_by(segment_id=segment_id, is_active=True).all()
        return jsonify([c.to_dict() for c in categories])
    except Exception as e:
        logger.exception("categories-by-segment API failed")
        return jsonify({'error': 'Something went wrong. Please try again later.'}), 500

@app.route('/api/get-subcategories-by-category/<int:category_id>')
def get_subcategories_by_category(category_id):
    try:
        subcategories = Subcategory.query.filter_by(category_id=category_id, is_active=True).all()
        return jsonify([s.to_dict() for s in subcategories])
    except Exception as e:
        logger.exception("subcategories-by-category API failed")
        return jsonify({'error': 'Something went wrong. Please try again later.'}), 500

@app.route('/api/get-products-by-subcategory/<int:subcategory_id>')
def get_products_by_subcategory(subcategory_id):
    try:
        products = Product.query.filter_by(subcategory_id=subcategory_id, is_active=True).all()
        return jsonify([p.to_dict() for p in products])
    except Exception as e:
        logger.exception("products-by-subcategory API failed")
        return jsonify({'error': 'Something went wrong. Please try again later.'}), 500



# ==================== SERVE STATIC FILES FROM TEMPLATES ====================

@app.route('/css/<path:filename>')
def serve_css(filename):
    """Serve CSS files from templates/css/"""
    return send_from_directory('templates/css', filename)

@app.route('/js/<path:filename>')
def serve_js(filename):
    """Serve JS files from templates/js/"""
    return send_from_directory('templates/js', filename)

@app.route('/images/<path:filename>')
def serve_images(filename):
    """Serve image files from images/"""
    return send_from_directory('images', filename)

# ==================== FIX RELATIVE IMAGE PATHS ====================

@app.route('/product-listing/<path:subpath>/images/<filename>')
def serve_images_from_product_listing(subpath, filename):
    """Handle relative image paths from product listing pages"""
    return send_from_directory('images', filename)




@app.route('/product-listing/<segment_name>/<category_name>/direct')
def product_listing_direct(segment_name, category_name):
    """Product Listing for Path B - directly under category"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = 24

        category = Category.query.join(Segment).filter(
            Segment.name.ilike(segment_name.replace('-', ' ')),
            Category.name.ilike(category_name.replace('-', ' '))
        ).first_or_404()

        segment = category.segment
        query = Product.query.filter_by(category_id=category.id, is_active=True)
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)

        return render_template('products.html',
            subcategory=None,
            category=category,
            segment=segment,
            products=pagination.items,
            pagination=pagination
        )
    except Exception as e:
        logger.exception("Failed loading direct-category products")
        return "Something went wrong. Please try again later.", 404

@app.route('/product/<segment_name>/<category_name>/direct/<product_name>/<int:product_id>')
def product_detail_direct(segment_name, category_name, product_name, product_id):
    """Product Detail for Path B"""
    try:
        product = Product.query.get_or_404(product_id)
        category = product.category
        segment = category.segment

        similar_products = Product.query.filter(
            Product.category_id == product.category_id,
            Product.id != product_id,
            Product.is_active == True
        ).limit(4).all()

        more_from_collection = Product.query.join(Subcategory).join(Category).filter(
            Category.segment_id == segment.id
        ).limit(4).all()

        other_segments = Product.query.join(Subcategory).join(Category).filter(
            Category.segment_id != segment.id
        ).limit(4).all()

        return render_template('product-detail.html',
            product=product,
            segment=segment,
            category=category,
            subcategory=None,
            similar_products=similar_products,
            more_from_collection=more_from_collection,
            other_segments=other_segments
        )
    except Exception as e:
        logger.exception("Failed loading direct product detail")
        return "Something went wrong. Please try again later.", 404

@app.route('/categories/<path:subpath>/images/<filename>')
def serve_images_from_categories(subpath, filename):
    """Handle relative image paths from category pages"""
    return send_from_directory('images', filename)

@app.route('/subcategories/<path:subpath>/images/<filename>')
def serve_images_from_subcategories(subpath, filename):
    """Handle relative image paths from subcategory pages"""
    return send_from_directory('images', filename)

@app.route('/product/<path:subpath>/images/<filename>')
def serve_images_from_product(subpath, filename):
    """Handle relative image paths from product detail pages"""
    return send_from_directory('images', filename)


# ==================== CONTACT FORM API ====================

@app.route('/api/contact', methods=['POST'])
@csrf.exempt  # public anonymous inquiry form, not a privileged/session action
def api_contact():
    """Save contact form submission"""
    try:
        data = request.get_json()

        inquiry = ContactInquiry(
            name=data.get('name'),
            email=data.get('email'),
            phone=data.get('phone'),
            business=data.get('business'),
            message=data.get('message')
        )

        db.session.add(inquiry)
        db.session.commit()

        return jsonify({'success': True, 'message': 'Message saved successfully'})

    except Exception as e:
        db.session.rollback()
        logger.exception("api_contact failed")
        return jsonify({'success': False, 'error': 'Something went wrong. Please try again later.'}), 500

# ==================== ADMIN CONTACT INQUIRIES ====================

@app.route('/admin/contact-inquiries')
@login_required
def admin_contact_inquiries():
    """View all contact inquiries"""
    inquiries = ContactInquiry.query.order_by(ContactInquiry.created_at.desc()).all()
    return render_template('admin/contact-inquiries.html', inquiries=inquiries)

@app.route('/admin/contact-inquiries/mark-read/<int:id>')
@login_required
def admin_mark_inquiry_read(id):
    """Mark inquiry as read"""
    try:
        inquiry = ContactInquiry.query.get_or_404(id)
        inquiry.is_read = True
        db.session.commit()
        flash('Marked as read', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error: {str(e)}', 'error')

    return redirect(url_for('admin_contact_inquiries'))

@app.route('/admin/contact-inquiries/delete/<int:id>', methods=['POST'])
@login_required
def admin_delete_inquiry(id):
    """Delete contact inquiry"""
    try:
        inquiry = ContactInquiry.query.get_or_404(id)
        name = inquiry.name
        db.session.delete(inquiry)
        db.session.commit()
        flash(f'Inquiry from {name} deleted successfully', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error: {str(e)}', 'error')

    return redirect(url_for('admin_contact_inquiries'))

@app.route('/admin/contact-inquiries/bulk-delete', methods=['POST'])
@login_required
def admin_bulk_delete_inquiries():
    """Bulk delete inquiries"""
    try:
        inquiry_ids = request.form.get('inquiry_ids', '')
        ids = [int(id.strip()) for id in inquiry_ids.split(',') if id.strip()]

        for inquiry_id in ids:
            inquiry = ContactInquiry.query.get(inquiry_id)
            if inquiry:
                db.session.delete(inquiry)

        db.session.commit()
        flash(f'Successfully deleted {len(ids)} inquiry/inquiries', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error: {str(e)}', 'error')

    return redirect(url_for('admin_contact_inquiries'))
# ==================== EXCEL IMPORT ====================

@app.route('/admin/import-excel', methods=['GET', 'POST'])
@admin_required
def admin_import_excel():
    if request.method == 'POST':
        try:
            from tasks import run_import_background
            import openpyxl
            
            sheet_url = request.form.get('sheet_url')
            if sheet_url and sheet_url.strip():
                import requests
                import re
                
                # Extract ID from URL
                match = re.search(r'/d/([a-zA-Z0-9-_]+)', sheet_url)
                if not match:
                    flash('Invalid Google Sheet URL format.', 'error')
                    return redirect(url_for('admin_import_excel'))
                
                sheet_id = match.group(1)
                export_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=xlsx"
                
                try:
                    response = requests.get(export_url, timeout=30)
                    if response.status_code != 200:
                        flash('Failed to fetch Google Sheet. Please make sure the sheet sharing settings are set to "Anyone with the link can view".', 'error')
                        return redirect(url_for('admin_import_excel'))
                    file_bytes = response.content
                except requests.RequestException as e:
                    flash(f'Failed to fetch Google Sheet: {str(e)}', 'error')
                    return redirect(url_for('admin_import_excel'))

            else:
                file = request.files.get('excel_file')
                if not file or not file.filename.endswith('.xlsx'):
                    flash('Please upload a valid .xlsx file or provide a Google Sheets URL', 'error')
                    return redirect(url_for('admin_import_excel'))
                file_bytes = file.read()
                
            overwrite_images = request.form.get('overwrite_images') == 'yes'    
            task_id = run_import_background(file_bytes, overwrite_images=overwrite_images)
            return render_template('admin/import-excel.html', task_id=task_id)
        except Exception as e:
            flash(f'Import failed: {str(e)}', 'error')
            return redirect(url_for('admin_import_excel'))
    return render_template('admin/import-excel.html', task_id=None)



# ==================== GOOGLE SHEET SYNC ====================

@app.route('/api/sheet-sync', methods=['POST'])
@csrf.exempt  # server-to-server call from Google Apps Script, authenticated via shared secret, not a browser session
def api_sheet_sync():
    """Auto-sync from Google Sheets App Script"""
    try:
        # Shared-secret check (constant-time compare)
        expected_secret = os.getenv('SHEET_SYNC_SECRET')
        if not expected_secret:
            logger.error("SHEET_SYNC_SECRET is not configured; refusing sheet-sync request")
            return jsonify({'error': 'Sync is not configured'}), 503

        secret = request.headers.get('X-Sync-Secret') or ''
        if not hmac.compare_digest(secret.encode(), expected_secret.encode()):
            return jsonify({'error': 'Unauthorized'}), 401

        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data received'}), 400

        results = {'segments': 0, 'categories': 0, 'subcategories': 0, 'products': 0, 'errors': []}

        # --- SEGMENTS ---
        for row in data.get('segments', []):
            try:
                code = str(row.get('segment_code', '')).strip()
                name = str(row.get('segment_name', '')).strip()
                if not name:
                    continue
                existing = Segment.query.filter(
                    db.or_(Segment.segment_code == code, Segment.name.ilike(name))
                ).first()
                if existing:
                    existing.name = name
                    existing.segment_code = code or existing.segment_code
                else:
                    db.session.add(Segment(name=name, segment_code=code or None))
                results['segments'] += 1
            except Exception as e:
                results['errors'].append(f'Segment error: {str(e)}')

        # --- CATEGORIES ---
        for row in data.get('categories', []):
            try:
                code = str(row.get('category_code', '')).strip()
                name = str(row.get('category_name', '')).strip()
                seg_code = str(row.get('segment_code', '')).strip()
                if not name:
                    continue
                segment = Segment.query.filter(
                    db.or_(Segment.segment_code == seg_code, Segment.name.ilike(seg_code))
                ).first()
                if not segment:
                    results['errors'].append(f'Segment not found for category: {name}')
                    continue
                existing = Category.query.filter(
                    db.or_(Category.category_code == code, Category.name.ilike(name))
                ).first()
                if existing:
                    existing.name = name
                    existing.category_code = code or existing.category_code
                    existing.segment_id = segment.id
                else:
                    db.session.add(Category(name=name, category_code=code or None, segment_id=segment.id))
                results['categories'] += 1
            except Exception as e:
                results['errors'].append(f'Category error: {str(e)}')

        # --- SUBCATEGORIES ---
        for row in data.get('subcategories', []):
            try:
                code = str(row.get('subcategory_code', '')).strip()
                name = str(row.get('subcategory_name', '')).strip()
                cat_code = str(row.get('category_code', '')).strip()
                if not name:
                    continue
                category = Category.query.filter(
                    db.or_(Category.category_code == cat_code, Category.name.ilike(cat_code))
                ).first()
                if not category:
                    results['errors'].append(f'Category not found for subcategory: {name}')
                    continue
                existing = Subcategory.query.filter(
                    db.or_(Subcategory.subcategory_code == code, Subcategory.name.ilike(name))
                ).first()
                if existing:
                    existing.name = name
                    existing.subcategory_code = code or existing.subcategory_code
                    existing.category_id = category.id
                else:
                    db.session.add(Subcategory(name=name, subcategory_code=code or None, category_id=category.id))
                results['subcategories'] += 1
            except Exception as e:
                results['errors'].append(f'Subcategory error: {str(e)}')

        # --- PRODUCTS ---
        for row in data.get('products', []):
            try:
                code = str(row.get('product_code', '')).strip()
                name = str(row.get('product_name', '')).strip()
                sub_code = str(row.get('subcategory_code', '')).strip()
                if not name or not code:
                    continue
                subcategory = Subcategory.query.filter(
                    db.or_(Subcategory.subcategory_code == sub_code, Subcategory.name.ilike(sub_code))
                ).first()
                existing = Product.query.filter_by(product_code=code).first()
                if existing:
                    existing.name = name
                    existing.details = row.get('details', existing.details)
                else:
                    db.session.add(Product(
                        name=name,
                        product_code=code,
                        details=row.get('details', ''),
                        subcategory_id=subcategory.id if subcategory else None
                    ))
                results['products'] += 1
            except Exception as e:
                results['errors'].append(f'Product error: {str(e)}')

        db.session.commit()
        return jsonify({'success': True, 'synced': results})

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/admin/import-status/<task_id>')
@admin_required
def import_status(task_id):
    from tasks import import_tasks_store
    
    task_info = import_tasks_store.get(task_id)
    if not task_info:
        return jsonify({'state': 'PENDING', 'progress': 0, 'status': 'Waiting to start...'})
        
    return jsonify({
        'state': task_info['state'],
        'progress': task_info.get('progress', 0),
        'status': task_info.get('status', ''),
        'result': task_info.get('result')
    })
