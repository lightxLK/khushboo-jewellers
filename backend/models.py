from app import db
from datetime import datetime
import json
from werkzeug.security import generate_password_hash, check_password_hash

# ==================== SEGMENT TABLE ====================
class Segment(db.Model):
    __tablename__ = 'segments'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    segment_code = db.Column(db.String(50), nullable=True, unique=True)
    image_path = db.Column(db.String(200), nullable=True)
    gallery_images = db.Column(db.Text, nullable=True)  # JSON array
    display_order = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship with categories
    categories = db.relationship('Category', backref='segment', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        gallery = []
        if self.gallery_images:
            try:
                gallery = json.loads(self.gallery_images)
            except:
                gallery = []
        
        return {
            'id': self.id,
            'name': self.name,
            'segment_code': self.segment_code,
            'image_path': self.image_path,
            'gallery_images': gallery,
            'display_order': self.display_order,
            'is_active': self.is_active,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None
        }

# ==================== CATEGORY TABLE ====================
class Category(db.Model):
    __tablename__ = 'categories'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    category_code = db.Column(db.String(50), nullable=True, unique=True)
    image_path = db.Column(db.String(200), nullable=True)
    gallery_images = db.Column(db.Text, nullable=True)  # JSON array
    segment_id = db.Column(db.Integer, db.ForeignKey('segments.id'), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    subcategories = db.relationship('Subcategory', backref='category', lazy=True, cascade='all, delete-orphan')
    direct_products = db.relationship('Product', backref='category', lazy=True, foreign_keys='Product.category_id')
    
    def to_dict(self):
        gallery = []
        if self.gallery_images:
            try:
                gallery = json.loads(self.gallery_images)
            except:
                gallery = []
        
        return {
            'id': self.id,
            'name': self.name,
            'category_code': self.category_code,
            'image_path': self.image_path,
            'gallery_images': gallery,
            'segment_id': self.segment_id,
            'segment_name': self.segment.name if self.segment else None,
            'segment': self.segment.to_dict() if self.segment else None,
            'is_active': self.is_active,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None
        }

# ==================== SUBCATEGORY TABLE ====================
class Subcategory(db.Model):
    __tablename__ = 'subcategories'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    subcategory_code = db.Column(db.String(50), nullable=True, unique=True)
    image_path = db.Column(db.String(200), nullable=True)
    gallery_images = db.Column(db.Text, nullable=True)  # JSON array
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship with products
    products = db.relationship('Product', backref='subcategory', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        gallery = []
        if self.gallery_images:
            try:
                gallery = json.loads(self.gallery_images)
            except:
                gallery = []
        
        return {
            'id': self.id,
            'name': self.name,
            'subcategory_code': self.subcategory_code,
            'image_path': self.image_path,
            'gallery_images': gallery,
            'category_id': self.category_id,
            'category_name': self.category.name if self.category else None,
            'is_active': self.is_active,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None
        }

# ==================== PRODUCT TABLE ====================
class Product(db.Model):
    __tablename__ = 'products'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    product_code = db.Column(db.String(50), nullable=False, unique=True)
    details = db.Column(db.Text, nullable=True)
    primary_image = db.Column(db.String(200), nullable=True)
    secondary_images = db.Column(db.Text, nullable=True)  # JSON array (gallery)
    subcategory_id = db.Column(db.Integer, db.ForeignKey('subcategories.id'), nullable=True)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=True)
    
    # Product tags and rating
    is_best_selling = db.Column(db.Boolean, default=False)
    is_assured = db.Column(db.Boolean, default=False)
    rating = db.Column(db.Float, default=0.0)  # 0.0 to 5.0
    is_active = db.Column(db.Boolean, default=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        secondary = []
        if self.secondary_images:
            try:
                secondary = json.loads(self.secondary_images)
            except:
                secondary = []

        if self.subcategory_id and self.subcategory:
            resolved_category = self.subcategory.category
            resolved_segment = resolved_category.segment if resolved_category else None
            resolved_subcategory_name = self.subcategory.name
        elif self.category_id and self.category:
            resolved_category = self.category
            resolved_segment = resolved_category.segment if resolved_category else None
            resolved_subcategory_name = None
        else:
            resolved_category = None
            resolved_segment = None
            resolved_subcategory_name = None

        return {
            'id': self.id,
            'name': self.name,
            'product_code': self.product_code,
            'details': self.details,
            'primary_image': self.primary_image,
            'secondary_images': secondary,
            'subcategory_id': self.subcategory_id,
            'category_id': self.category_id,
            'subcategory_name': resolved_subcategory_name,
            'category_name': resolved_category.name if resolved_category else None,
            'segment_name': resolved_segment.name if resolved_segment else None,
            'is_best_selling': self.is_best_selling,
            'is_assured': self.is_assured,
            'rating': self.rating,
            'is_active': self.is_active,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None
        }

# ==================== DYNAMIC SECTION TABLE ====================
class DynamicSection(db.Model):
    __tablename__ = 'dynamic_sections'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    subtitle = db.Column(db.String(500), nullable=True)
    display_type = db.Column(db.String(20), default='product')
    product_ids = db.Column(db.Text, nullable=True)  # JSON array of product IDs
    is_visible = db.Column(db.Boolean, default=True)
    display_order = db.Column(db.Integer, default=0)
    is_automatic = db.Column(db.Boolean, default=False)
    automatic_type = db.Column(db.String(50), nullable=True)
    parent_id = db.Column(db.Integer, nullable=True)
    parent_type = db.Column(db.String(50), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'subtitle': self.subtitle,
            'display_type': self.display_type,
            'product_ids': self.product_ids,
            'is_visible': self.is_visible,
            'display_order': self.display_order,
            'is_automatic': self.is_automatic,
            'automatic_type': self.automatic_type,
            'parent_id': self.parent_id,
            'parent_type': self.parent_type,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None
        }

# ==================== ADMIN USER TABLE ====================
class AdminUser(db.Model):
    __tablename__ = 'admin_users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<AdminUser {self.email}>'

# ==================== CONTACT INQUIRY TABLE ====================
class ContactInquiry(db.Model):
    __tablename__ = 'contact_inquiries'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(200), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    business = db.Column(db.String(200), nullable=True)
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_read = db.Column(db.Boolean, default=False)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'phone': self.phone,
            'business': self.business,
            'message': self.message,
            'created_at': self.created_at.strftime('%d %b %Y, %I:%M %p') if self.created_at else None,
            'is_read': self.is_read
        }