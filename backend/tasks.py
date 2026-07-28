import threading
import uuid
from PIL import Image
import os, io, json, re
from datetime import datetime

import_tasks_store = {}
def get_drive_file_id(drive_link):
    patterns = [
        r'/folders/([a-zA-Z0-9_-]+)',
        r'/file/d/([a-zA-Z0-9_-]+)',
        r'id=([a-zA-Z0-9_-]+)'
    ]
    for pattern in patterns:
        match = re.search(pattern, drive_link)
        if match:
            return match.group(1)
    return None

_drive_folder_cache = {}

def download_image_from_drive(folder_id, image_code, save_folder, upload_folder):
    try:
        import gdown, tempfile, shutil
        if folder_id not in _drive_folder_cache:
            output_dir = os.path.join(tempfile.gettempdir(), f'kj_drive_{folder_id}')
            if os.path.exists(output_dir):
                shutil.rmtree(output_dir)
            os.makedirs(output_dir, exist_ok=True)
            gdown.download_folder(
                url=f"https://drive.google.com/drive/folders/{folder_id}",
                output=output_dir, quiet=False, use_cookies=False
            )
            file_index = {}
            for root, dirs, files in os.walk(output_dir):
                for fname in files:
                    base = fname.rsplit('.', 1)[0].upper()
                    file_index[base] = os.path.join(root, fname)
            _drive_folder_cache[folder_id] = file_index

        file_index = _drive_folder_cache[folder_id]
        found_file = file_index.get(image_code.upper())
        if not found_file:
            return None

        with open(found_file, 'rb') as f:
            file_bytes = f.read()

        img = Image.open(io.BytesIO(file_bytes))
        if img.mode in ('RGBA', 'LA', 'P'):
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
            img = background

        img_ratio = img.size[0] / img.size[1]
        if img_ratio > 1.0:
            new_height = 1080
            new_width = int(new_height * img_ratio)
        else:
            new_width = 1080
            new_height = int(new_width / img_ratio)
        img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        left = (new_width - 1080) // 2
        top = (new_height - 1080) // 2
        img = img.crop((left, top, left + 1080, top + 1080))

        out = io.BytesIO()
        img.save(out, format='WEBP', quality=85)
        out.seek(0)

        folder_path = os.path.join(upload_folder, save_folder)
        os.makedirs(folder_path, exist_ok=True)
        save_filename = f"{int(datetime.now().timestamp())}_{image_code}.webp"
        save_path = os.path.join(folder_path, save_filename)
        with open(save_path, 'wb') as f:
            f.write(out.read())

        return f"/uploads/{save_folder}/{save_filename}"
    except Exception as e:
        print(f"Drive download error: {e}")
        return None

def run_import_background(file_bytes, overwrite_images=False):
    task_id = str(uuid.uuid4())
    import_tasks_store[task_id] = {'state': 'PENDING', 'progress': 0, 'status': 'Starting...', 'result': None}
    
    def background_worker():
        import_tasks_store[task_id]['state'] = 'PROGRESS'
        run_import_logic(task_id, file_bytes, overwrite_images)
        
    thread = threading.Thread(target=background_worker)
    thread.daemon = True
    thread.start()
    return task_id

def run_import_logic(task_id, file_bytes, overwrite_images):
    import openpyxl
    from app import app, db
    from models import Segment, Category, Subcategory, Product

    try:
        with app.app_context():
            upload_folder = app.config['UPLOAD_FOLDER']
            wb = openpyxl.load_workbook(io.BytesIO(file_bytes))
            results = {'segments': 0, 'categories': 0, 'subcategories': 0, 'products': 0, 'errors': []}

            # Identify sheets flexibly
            sheet_map = {}
            for sn in wb.sheetnames:
                sn_norm = sn.upper().replace(' ', '')
                if 'SEGMENT' in sn_norm: sheet_map['segments'] = sn
                elif 'SUBCATEGORY' in sn_norm or 'SUBCAT' in sn_norm: sheet_map['subcategories'] = sn
                elif 'CATEGORY' in sn_norm: sheet_map['categories'] = sn
                elif 'PRODUCT' in sn_norm: sheet_map['products'] = sn

            # Count total rows for progress
            total_rows = 0
            for key in ['segments', 'categories', 'subcategories', 'products']:
                if key in sheet_map:
                    total_rows += wb[sheet_map[key]].max_row - 1
            
            done_rows = 0
            def update_progress(msg):
                nonlocal done_rows
                done_rows += 1
                pct = int((done_rows / max(total_rows, 1)) * 100)
                if task_id in import_tasks_store:
                    import_tasks_store[task_id]['progress'] = pct
                    import_tasks_store[task_id]['status'] = msg

            if not sheet_map:
                raise Exception("No valid inventory sheets found. Please ensure your Excel sheets are named correctly (e.g., SEGMENTS, CATEGORIES, SUBCATS, PRODUCTS).")

            # SHEET 1: SEGMENTS
            if 'segments' in sheet_map:
                ws = wb[sheet_map['segments']]
                for row in ws.iter_rows(min_row=2, values_only=True):
                    if not row or not row[0]:
                        update_progress("Skipping empty segment row")
                        continue
                    try:
                        seg_code = str(row[0]).strip()
                        seg_name = str(row[1]).strip() if row[1] else seg_code
                        img_code = str(row[2]).strip() if len(row) > 2 and row[2] else None
                        drive_link = str(row[3]).strip() if len(row) > 3 and row[3] else None
                        disp_order = int(row[4]) if len(row) > 4 and row[4] else 0
                        is_active = str(row[5]).strip().upper() == 'YES' if len(row) > 5 and row[5] else True

                        existing = Segment.query.filter_by(segment_code=seg_code).first()
                        
                        img_path = None
                        should_download = True
                        if existing and existing.image_path and not overwrite_images:
                            should_download = False
                            
                        if should_download and img_code and drive_link and 'PASTE' not in drive_link:
                            folder_id = get_drive_file_id(drive_link)
                            if folder_id:
                                img_path = download_image_from_drive(folder_id, img_code, 'segments', upload_folder)

                        if existing:
                            existing.name = seg_name
                            if img_path:
                                existing.image_path = img_path
                            existing.display_order = disp_order
                            existing.is_active = is_active
                        else:
                            db.session.add(Segment(name=seg_name, segment_code=seg_code, image_path=img_path, display_order=disp_order, is_active=is_active))
                        db.session.flush()
                        results['segments'] += 1
                        update_progress(f"Importing segment: {seg_name}")
                    except Exception as e:
                        results['errors'].append(f"Segment error: {str(e)}")
                        update_progress(f"Error in segment row")
                db.session.commit()

            # SHEET 2: CATEGORIES
            if 'categories' in sheet_map:
                ws = wb[sheet_map['categories']]
                for row in ws.iter_rows(min_row=2, values_only=True):
                    if not row or not row[1]: # Use cat_code as primary check
                        update_progress("Skipping category row")
                        continue
                    try:
                        seg_code = str(row[0]).strip()
                        cat_code = str(row[1]).strip()
                        cat_name = str(row[2]).strip() if row[2] else cat_code
                        img_code = str(row[3]).strip() if len(row) > 3 and row[3] else None
                        gal_codes = [str(row[i]).strip() for i in range(4, 8) if len(row) > i and row[i]]
                        drive_link = str(row[8]).strip() if len(row) > 8 and row[8] else None
                        is_active = str(row[9]).strip().upper() == 'YES' if len(row) > 9 and row[9] else True

                        segment = Segment.query.filter_by(segment_code=seg_code).first()
                        if not segment:
                            results['errors'].append(f"Category '{cat_name}': segment '{seg_code}' not found")
                            update_progress(f"Segment not found for category")
                            continue

                        existing = Category.query.filter_by(category_code=cat_code).first()
                        
                        img_path = None
                        gallery_paths = []
                        should_download = True
                        if existing and existing.image_path and not overwrite_images:
                            should_download = False

                        if should_download and drive_link and 'PASTE' not in drive_link:
                            folder_id = get_drive_file_id(drive_link)
                            if folder_id:
                                if img_code:
                                    img_path = download_image_from_drive(folder_id, img_code, 'categories', upload_folder)
                                for gc in gal_codes:
                                    gp = download_image_from_drive(folder_id, gc, 'categories', upload_folder)
                                    if gp:
                                        gallery_paths.append(gp)

                        if existing:
                            existing.name = cat_name
                            existing.segment_id = segment.id
                            if img_path:
                                existing.image_path = img_path
                            if gallery_paths:
                                existing.gallery_images = json.dumps(gallery_paths)
                            existing.is_active = is_active
                        else:
                            db.session.add(Category(name=cat_name, category_code=cat_code, segment_id=segment.id, image_path=img_path, gallery_images=json.dumps(gallery_paths) if gallery_paths else None, is_active=is_active))
                        db.session.flush()
                        results['categories'] += 1
                        update_progress(f"Importing category: {cat_name}")
                    except Exception as e:
                        results['errors'].append(f"Category error: {str(e)}")
                        update_progress(f"Error in category row")
                db.session.commit()

            # SHEET 3: SUBCATEGORIES
            if 'subcategories' in sheet_map:
                ws = wb[sheet_map['subcategories']]
                for row in ws.iter_rows(min_row=2, values_only=True):
                    if not row or not row[1]: # Use sub_code as primary check
                        update_progress("Skipping subcategory row")
                        continue
                    try:
                        cat_code = str(row[0]).strip()
                        sub_code = str(row[1]).strip()
                        sub_name = str(row[2]).strip() if row[2] else sub_code
                        img_code = str(row[3]).strip() if len(row) > 3 and row[3] else None
                        gal_codes = [str(row[i]).strip() for i in range(4, 8) if len(row) > i and row[i]]
                        drive_link = str(row[8]).strip() if len(row) > 8 and row[8] else None
                        is_active = str(row[9]).strip().upper() == 'YES' if len(row) > 9 and row[9] else True

                        category = Category.query.filter_by(category_code=cat_code).first()
                        if not category:
                            results['errors'].append(f"Subcategory '{sub_name}': category '{cat_code}' not found")
                            update_progress(f"Category not found for subcategory")
                            continue

                        existing = Subcategory.query.filter_by(subcategory_code=sub_code).first()
                        
                        img_path = None
                        gallery_paths = []
                        should_download = True
                        if existing and existing.image_path and not overwrite_images:
                            should_download = False
                            
                        if should_download and drive_link and 'PASTE' not in drive_link:
                            folder_id = get_drive_file_id(drive_link)
                            if folder_id:
                                if img_code:
                                    img_path = download_image_from_drive(folder_id, img_code, 'subcategories', upload_folder)
                                for gc in gal_codes:
                                    gp = download_image_from_drive(folder_id, gc, 'subcategories', upload_folder)
                                    if gp:
                                        gallery_paths.append(gp)

                        if existing:
                            existing.name = sub_name
                            existing.category_id = category.id
                            if img_path:
                                existing.image_path = img_path
                            if gallery_paths:
                                existing.gallery_images = json.dumps(gallery_paths)
                            existing.is_active = is_active
                        else:
                            db.session.add(Subcategory(name=sub_name, subcategory_code=sub_code, category_id=category.id, image_path=img_path, gallery_images=json.dumps(gallery_paths) if gallery_paths else None, is_active=is_active))
                        db.session.flush()
                        results['subcategories'] += 1
                        update_progress(f"Importing subcategory: {sub_name}")
                    except Exception as e:
                        results['errors'].append(f"Subcategory error: {str(e)}")
                        update_progress(f"Error in subcategory row")
                db.session.commit()

            # SHEET 4: PRODUCTS
            if 'products' in sheet_map:
                ws = wb[sheet_map['products']]
                for row in ws.iter_rows(min_row=2, values_only=True):
                    if not row or not row[1]: # Use prod_code as primary check
                        update_progress("Skipping product row")
                        continue
                    try:
                        sub_code = str(row[0]).strip()
                        prod_code = str(row[1]).strip()
                        prod_name = str(row[2]).strip() if row[2] else prod_code
                        img_code = str(row[3]).strip() if len(row) > 3 and row[3] else None
                        sec_codes = [str(row[i]).strip() for i in range(4, 8) if len(row) > i and row[i]]
                        drive_link = str(row[8]).strip() if len(row) > 8 and row[8] else None
                        details = str(row[9]).strip() if len(row) > 9 and row[9] else None
                        best_sell = str(row[10]).strip().upper() == 'YES' if len(row) > 10 and row[10] else False
                        is_assured = str(row[11]).strip().upper() == 'YES' if len(row) > 11 and row[11] else False
                        rating = float(row[12]) if len(row) > 12 and row[12] else 0.0
                        is_active = str(row[13]).strip().upper() == 'YES' if len(row) > 13 and row[13] else True

                        subcategory = Subcategory.query.filter_by(subcategory_code=sub_code).first()
                        if not subcategory:
                            results['errors'].append(f"Product '{prod_name}': subcategory '{sub_code}' not found")
                            update_progress("Subcategory not found for product")
                            continue

                        existing = Product.query.filter_by(product_code=prod_code).first()

                        primary_path = None
                        secondary_paths = []
                        should_download = True
                        if existing and existing.primary_image and not overwrite_images:
                            should_download = False

                        if should_download and drive_link and 'PASTE' not in drive_link:
                            folder_id = get_drive_file_id(drive_link)
                            if folder_id:
                                if img_code:
                                    primary_path = download_image_from_drive(folder_id, img_code, 'products/primary', upload_folder)
                                for sc in sec_codes:
                                    sp = download_image_from_drive(folder_id, sc, 'products/gallery', upload_folder)
                                    if sp:
                                        secondary_paths.append(sp)

                        if existing:
                            existing.name = prod_name
                            existing.details = details
                            existing.subcategory_id = subcategory.id
                            existing.category_id = None
                            if primary_path:
                                existing.primary_image = primary_path
                            if secondary_paths:
                                existing.secondary_images = json.dumps(secondary_paths)
                            existing.is_best_selling = best_sell
                            existing.is_assured = is_assured
                            existing.rating = rating
                            existing.is_active = is_active
                        else:
                            db.session.add(Product(name=prod_name, product_code=prod_code, details=details, subcategory_id=subcategory.id, category_id=None, primary_image=primary_path, secondary_images=json.dumps(secondary_paths) if secondary_paths else None, is_best_selling=best_sell, is_assured=is_assured, rating=rating, is_active=is_active))
                        db.session.flush()
                        results['products'] += 1
                        update_progress(f"Importing product: {prod_name}")
                    except Exception as e:
                        results['errors'].append(f"Product error: {str(e)}")
                        update_progress("Error in product row")
                db.session.commit()

        if task_id in import_tasks_store:
            import_tasks_store[task_id]['state'] = 'SUCCESS'
            import_tasks_store[task_id]['progress'] = 100
            import_tasks_store[task_id]['result'] = results
            
    except Exception as e:
        if task_id in import_tasks_store:
            import_tasks_store[task_id]['state'] = 'FAILURE'
            import_tasks_store[task_id]['status'] = str(e)