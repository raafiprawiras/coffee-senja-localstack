import json
import os
import time
import uuid
import datetime
from decimal import Decimal
from functools import wraps

from flask import Flask, flash, redirect, render_template, request, session, url_for, jsonify
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

from aws_clients import DecimalEncoder, dynamodb_resource, s3_client, sqs_client, to_decimal
from config import (
    APP_NAME,
    APP_SECRET_KEY,
    MENU_TABLE_NAME,
    ORDERS_TABLE_NAME,
    S3_BUCKET_NAME,
    SQS_QUEUE_NAME,
    USERS_TABLE_NAME,
    PROMOS_TABLE_NAME,
)

app = Flask(__name__)
app.secret_key = APP_SECRET_KEY

UPLOAD_SUBDIR = "uploads/menu"
UPLOAD_FOLDER = os.path.join(app.root_path, "static", UPLOAD_SUBDIR)
ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp", "svg"}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def allowed_image(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS


def save_menu_image(file_storage):
    if not file_storage or not file_storage.filename:
        return ""
    if not allowed_image(file_storage.filename):
        raise ValueError("Format foto tidak didukung. Gunakan PNG, JPG, JPEG, WEBP, GIF, atau SVG.")

    original = secure_filename(file_storage.filename)
    ext = original.rsplit(".", 1)[1].lower()
    filename = f"menu-{uuid.uuid4().hex[:12]}.{ext}"
    file_path = os.path.join(UPLOAD_FOLDER, filename)
    file_storage.save(file_path)
    return f"{UPLOAD_SUBDIR}/{filename}"



def menu_table():
    return dynamodb_resource().Table(MENU_TABLE_NAME)


def orders_table():
    return dynamodb_resource().Table(ORDERS_TABLE_NAME)


def users_table():
    return dynamodb_resource().Table(USERS_TABLE_NAME)


def promos_table():
    return dynamodb_resource().Table(PROMOS_TABLE_NAME)


def now_ts():
    return int(time.time())


def rupiah(value):
    value = int(value or 0)
    return "Rp {:,}".format(value).replace(",", ".")


app.jinja_env.filters["rupiah"] = rupiah

@app.before_request
def init_cart():
    if "cart" not in session:
        session["cart"] = []


def format_datetime(value):
    if not value or int(value) < 1000000:
        return "-"
    try:
        dt = datetime.datetime.fromtimestamp(int(value))
        return dt.strftime("%d %b %Y, %H:%M")
    except (ValueError, TypeError):
        return value


app.jinja_env.filters["datetime"] = format_datetime


def get_queue_url():
    return sqs_client().get_queue_url(QueueName=SQS_QUEUE_NAME)["QueueUrl"]


def active_menus():
    items = menu_table().scan().get("Items", [])
    items = [item for item in items if item.get("is_active", True)]
    return sorted(items, key=lambda item: item.get("created_at", 0), reverse=False)


def all_menus():
    items = menu_table().scan().get("Items", [])
    return sorted(items, key=lambda item: item.get("created_at", 0), reverse=True)


def all_orders():
    items = orders_table().scan().get("Items", [])
    return sorted(items, key=lambda item: item.get("created_at", 0), reverse=True)


def admin_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if not session.get("admin_username") or session.get("user_role") != "ADMIN":
            flash("Akses ditolak. Halaman ini hanya untuk Admin.", "danger")
            return redirect(url_for("customer_page"))
        return view(*args, **kwargs)

    return wrapped_view


def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if not session.get("admin_username"):
            flash("Silakan login terlebih dahulu.", "warning")
            return redirect(url_for("login"))
        return view(*args, **kwargs)

    return wrapped_view


@app.context_processor
def inject_globals():
    try:
        order_count = len(all_orders())
    except Exception:
        order_count = 0
    return {
        "app_name": APP_NAME, 
        "admin_username": session.get("admin_username"), 
        "user_role": session.get("user_role"),
        "order_count": order_count
    }


@app.get("/")
def customer_page():
    menus = active_menus()
    orders = [order for order in all_orders()[:10]]
    promos = [p for p in promos_table().scan().get("Items", []) if p.get("is_active", True)]
    return render_template("index.html", menus=menus, orders=orders, promos=promos)


@app.get("/promos")
def promos_page():
    items = promos_table().scan().get("Items", [])
    active_promos = [p for p in items if p.get("is_active", True)]
    return render_template("promos.html", promos=active_promos)


@app.get("/about")
def about_page():
    return render_template("about.html")


@app.get("/my-orders")
@login_required
def my_orders():
    username = session.get("admin_username")
    # Filter by the hidden member_username field for 100% accuracy
    orders = [o for o in all_orders() if o.get("member_username") == username]
    return render_template("orders.html", orders=orders)


@app.post("/cart/add")
def add_to_cart():
    menu_id = request.form.get("menu_id")
    quantity = int(request.form.get("quantity", 1))
    note = request.form.get("note", "").strip()
    
    menu = menu_table().get_item(Key={"menu_id": menu_id}).get("Item")
    if not menu:
        return jsonify({"error": "Menu not found"}), 404
    
    cart = session.get("cart", [])
    # Check if item already in cart with same note
    existing = next((item for item in cart if item["menu_id"] == menu_id and item["note"] == note), None)
    if existing:
        existing["quantity"] = int(existing.get("quantity", 0)) + quantity
    else:
        cart.append({
            "menu_id": menu_id,
            "name": menu["name"],
            "price": float(menu["price"]),
            "quantity": quantity,
            "note": note,
            "image_path": menu.get("image_path", "")
        })
    
    session["cart"] = cart
    session.modified = True
    
    # Calculate count safely
    cart_count = 0
    for i in cart:
        cart_count += int(i.get("quantity", 0))

    return jsonify({
        "message": f"{menu['name']} ditambahkan ke keranjang", 
        "cart_count": cart_count
    })


@app.get("/cart")
def view_cart():
    cart = session.get("cart", [])
    # Calculate subtotal using float for template display (safe for rupiah filter)
    subtotal = 0.0
    for item in cart:
        try:
            price = float(item.get("price", 0))
            qty = int(item.get("quantity", 1))
            subtotal += price * qty
        except (TypeError, ValueError):
            continue
    return render_template("cart.html", cart=cart, subtotal=subtotal)


@app.post("/cart/remove/<int:index>")
def remove_from_cart(index):
    cart = session.get("cart", [])
    if 0 <= index < len(cart):
        cart.pop(index)
    session["cart"] = cart
    session.modified = True
    return redirect(url_for("view_cart"))


@app.post("/cart/clear")
def clear_cart():
    session["cart"] = []
    session.modified = True
    return redirect(url_for("customer_page"))


@app.post("/order")
def create_order():
    customer_name = request.form.get("customer_name", "").strip()
    promo_code = request.form.get("promo_code", "").strip().upper()
    cart = session.get("cart", [])

    if not cart:
        flash("Keranjang belanja kosong.", "warning")
        return redirect(url_for("customer_page"))

    if not customer_name:
        flash("Nama customer wajib diisi.", "danger")
        return redirect(url_for("view_cart"))

    order_id = f"ORD-{uuid.uuid4().hex[:8].upper()}"
    
    items_data = []
    subtotal = Decimal("0")
    for item in cart:
        try:
            # Defensive conversion to avoid TypeError
            item_price = to_decimal(item.get("price", 0))
            item_qty = Decimal(str(item.get("quantity", 1)))
            item_subtotal = item_price * item_qty
            
            subtotal += item_subtotal
            items_data.append({
                "menu_id": item.get("menu_id"),
                "name": item.get("name", "Unknown Item"),
                "price": item_price,
                "quantity": int(item_qty),
                "note": item.get("note", ""),
                "subtotal": item_subtotal,
                "image_path": item.get("image_path", "")
            })
        except Exception as e:
            print(f"Error processing cart item: {e}")
            continue

    # Compat fields for single-item legacy views
    main_item = items_data[0]

    # Promo logic
    discount = Decimal("0")
    applied_promo = None
    if promo_code:
        items = promos_table().scan().get("Items", [])
        promo = next((p for p in items if p.get("code") == promo_code and p.get("is_active")), None)
        if promo:
            if subtotal >= to_decimal(promo.get("min_purchase", 0)):
                discount = to_decimal(promo.get("discount_value", 0))
                applied_promo = promo_code
            else:
                flash(f"Promo {promo_code} minimal pembelian {rupiah(promo.get('min_purchase'))}.", "warning")
        else:
            flash(f"Kode promo {promo_code} tidak valid.", "warning")

    total = max(Decimal("0"), subtotal - discount)

    order = {
        "order_id": order_id,
        "customer_name": customer_name,
        "items": items_data,
        "menu_name": str(main_item["name"]) + (f" (+{len(items_data)-1} lainnya)" if len(items_data) > 1 else ""),
        "menu_image_path": main_item.get("image_path", ""),
        "quantity": int(sum(int(i["quantity"]) for i in items_data)),
        "subtotal": subtotal,
        "discount": discount,
        "total": total,
        "promo_code": str(applied_promo or ""),
        "member_username": str(session.get("admin_username") if session.get("user_role") == "MEMBER" else ""),
        "status": "QUEUED",
        "receipt_key": "",
        "created_at": now_ts(),
        "updated_at": now_ts(),
    }

    orders_table().put_item(Item=order)

    # SQS message
    message = {
        "order_id": order_id,
        "customer_name": customer_name,
        "items_count": len(items_data),
        "total": int(total),
        "created_at": order["created_at"],
    }
    sqs_client().send_message(QueueUrl=get_queue_url(), MessageBody=json.dumps(message, cls=DecimalEncoder))

    session["cart"] = []
    session.modified = True
    
    flash(f"Pesanan {order_id} berhasil dibuat.", "success")
    return redirect(url_for("receipt_page", order_id=order_id))


@app.get("/receipt/<order_id>")
def receipt_page(order_id):
    order = orders_table().get_item(Key={"order_id": order_id}).get("Item")
    if not order:
        flash("Order tidak ditemukan.", "danger")
        return redirect(url_for("customer_page"))

    receipt = None
    receipt_source = "Order"
    if order.get("receipt_key"):
        try:
            response = s3_client().get_object(Bucket=S3_BUCKET_NAME, Key=order["receipt_key"])
            receipt = json.loads(response["Body"].read().decode("utf-8"))
            receipt_source = "Receipt Digital"
        except Exception:
            receipt = None

    return render_template("receipt.html", order=order, receipt=receipt, receipt_source=receipt_source)


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        form_type = request.form.get("form_type", "login")

        # --- LOGIKA REGISTER ---
        if form_type == "register":
            full_name = request.form.get("full_name", "").strip()
            username = request.form.get("new_username", "").strip()
            password = request.form.get("new_password", "")
            confirm = request.form.get("confirm_password", "")

            if not username or not password or not full_name:
                flash("Semua field wajib diisi.", "danger")
                return render_template("login.html")
            
            if password != confirm:
                flash("Konfirmasi password tidak cocok.", "danger")
                return render_template("login.html")

            # Cek apakah username sudah ada
            existing_user = users_table().get_item(Key={"username": username}).get("Item")
            if existing_user:
                flash("Username sudah digunakan, silakan pilih yang lain.", "warning")
                return render_template("login.html")

            # Simpan user baru (Role default: MEMBER)
            users_table().put_item(
                Item={
                    "username": username,
                    "full_name": full_name,
                    "password_hash": generate_password_hash(password),
                    "role": "MEMBER",
                    "created_at": now_ts()
                }
            )
            flash("Pendaftaran berhasil! Silakan masuk dengan akun baru Anda.", "success")
            return render_template("login.html")

        # --- LOGIKA LOGIN ---
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if not username:
            flash("Username wajib diisi.", "danger")
            return render_template("login.html")

        user = users_table().get_item(Key={"username": username}).get("Item")
        if user and check_password_hash(user.get("password_hash", ""), password):
            session["admin_username"] = username
            
            # --- HOTFIX: Pastikan admin utama selalu dikenali ---
            from config import DEFAULT_ADMIN_USERNAME
            if username == DEFAULT_ADMIN_USERNAME:
                session["user_role"] = "ADMIN"
                
                # Perbarui role di database jika kebetulan tersimpan sebagai MEMBER
                if user.get("role") != "ADMIN":
                    users_table().update_item(
                        Key={"username": username},
                        UpdateExpression="SET #r = :role",
                        ExpressionAttributeNames={"#r": "role"},
                        ExpressionAttributeValues={":role": "ADMIN"}
                    )
            else:
                session["user_role"] = user.get("role", "MEMBER")
            
            if session["user_role"] == "ADMIN":
                flash(f"Selamat datang kembali, Admin {username}!", "success")
                return redirect(url_for("ops_dashboard"))
            else:
                flash(f"Halo {user.get('full_name', username)}, selamat menikmati kopi Senja!", "success")
                return redirect(url_for("customer_page"))

        flash("Username atau password salah.", "danger")

    return render_template("login.html")


@app.get("/logout")
def logout():
    session.clear()
    flash("Logout berhasil.", "success")
    return redirect(url_for("customer_page"))


@app.get("/admin")
@admin_required
def admin_dashboard():
    menus = all_menus()
    orders = all_orders()
    queue_orders = [order for order in orders if order.get("status") == "QUEUED"]
    ready_orders = [order for order in orders if order.get("status") == "READY"]
    total_sales = sum(Decimal(order.get("total", 0)) for order in ready_orders)

    stats = {
        "total_menus": len([item for item in menus if item.get("is_active", True)]),
        "queued_orders": len(queue_orders),
        "ready_orders": len(ready_orders),
        "total_sales": total_sales,
    }
    return render_template("admin.html", menus=menus, orders=orders, queue_orders=queue_orders, stats=stats, promos=promos_table().scan().get("Items", []))


@app.get("/admin/dashboard")
@admin_required
def ops_dashboard():
    """
    Monitoring dashboard for daily operations.
    Shows revenue, transactions, inventory alerts, and recent activity.
    """
    orders = all_orders()
    
    # Calculate today's start timestamp (midnight)
    today_dt = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    today_ts = int(today_dt.timestamp())
    
    # Filter orders for today
    today_orders = [o for o in orders if int(o.get("created_at", 0)) >= today_ts]
    
    # Metrics
    total_revenue_today = sum(to_decimal(o.get("total", 0)) for o in today_orders if o.get("status") == "READY")
    total_transactions_today = len(today_orders)
    
    # Inventory Management (Simulation for now as table is not defined in config)
    # In production, this would be a query to CoffeeSenjaInventory table
    inventory_items = [
        {"name": "Biji Kopi Arabica", "stock": 5, "unit": "kg", "threshold": 10},
        {"name": "Susu UHT", "stock": 8, "unit": "liter", "threshold": 10},
        {"name": "Gelas Plastik", "stock": 250, "unit": "pcs", "threshold": 50},
        {"name": "Sirup Karamel", "stock": 2, "unit": "botol", "threshold": 5},
        {"name": "Bubuk Cokelat", "stock": 12, "unit": "kg", "threshold": 5}
    ]
    low_stock_items = [item for item in inventory_items if item["stock"] < item["threshold"]]
    
    # Recent activity
    recent_orders = sorted(orders, key=lambda x: int(x.get("created_at", 0)), reverse=True)[:5]
    
    return render_template(
        "dashboard.html",
        revenue_today=total_revenue_today,
        transactions_today=total_transactions_today,
        low_stock_items=low_stock_items,
        recent_orders=recent_orders
    )



@app.post("/admin/menu")
@admin_required
def add_menu():
    name = request.form.get("name", "").strip()
    category = request.form.get("category", "Signature").strip()
    description = request.form.get("description", "").strip()
    price = request.form.get("price", "0").strip()

    if not name or not description or not price:
        flash("Nama, deskripsi, dan harga menu wajib diisi.", "danger")
        return redirect(url_for("admin_dashboard"))

    try:
        price_decimal = to_decimal(price)
        if price_decimal <= 0:
            raise ValueError
    except Exception:
        flash("Harga harus berupa angka lebih dari 0.", "danger")
        return redirect(url_for("admin_dashboard"))

    try:
        image_path = save_menu_image(request.files.get("image"))
    except ValueError as exc:
        flash(str(exc), "danger")
        return redirect(url_for("admin_dashboard"))

    menu_id = f"MENU-{uuid.uuid4().hex[:8].upper()}"
    menu_table().put_item(
        Item={
            "menu_id": menu_id,
            "name": name,
            "category": category,
            "description": description,
            "price": price_decimal,
            "image_path": image_path,
            "is_active": True,
            "created_at": now_ts(),
            "updated_at": now_ts(),
        }
    )

    flash(f"Menu baru '{name}' berhasil ditambahkan dan aktif di halaman customer.", "success")
    return redirect(url_for("admin_dashboard"))


@app.post("/admin/menu/<menu_id>/edit")
@admin_required
def edit_menu(menu_id):
    item = menu_table().get_item(Key={"menu_id": menu_id}).get("Item")
    if not item:
        flash("Menu tidak ditemukan.", "danger")
        return redirect(url_for("admin_dashboard"))

    name = request.form.get("name", item.get("name")).strip()
    category = request.form.get("category", item.get("category")).strip()
    description = request.form.get("description", item.get("description")).strip()
    price = request.form.get("price", str(item.get("price"))).strip()
    is_active = request.form.get("is_active") == "on"

    try:
        price_decimal = to_decimal(price)
    except Exception:
        flash("Harga tidak valid.", "danger")
        return redirect(url_for("admin_dashboard"))

    image_file = request.files.get("image")
    image_path = item.get("image_path", "")
    if image_file and image_file.filename:
        try:
            image_path = save_menu_image(image_file)
        except ValueError as exc:
            flash(str(exc), "danger")
            return redirect(url_for("admin_dashboard"))

    menu_table().update_item(
        Key={"menu_id": menu_id},
        UpdateExpression="SET #n = :n, category = :c, description = :d, price = :p, is_active = :a, image_path = :i, updated_at = :u",
        ExpressionAttributeNames={"#n": "name"},
        ExpressionAttributeValues={
            ":n": name,
            ":c": category,
            ":d": description,
            ":p": price_decimal,
            ":a": is_active,
            ":i": image_path,
            ":u": now_ts(),
        },
    )
    flash(f"Menu '{name}' berhasil diperbarui.", "success")
    return redirect(url_for("admin_dashboard"))


@app.post("/admin/menu/<menu_id>/delete")
@admin_required
def delete_menu(menu_id):
    menu_table().delete_item(Key={"menu_id": menu_id})
    flash("Menu berhasil dihapus.", "success")
    return redirect(url_for("admin_dashboard"))


@app.post("/admin/process-queue")
@admin_required
def process_queue():
    sqs = sqs_client()
    queue_url = get_queue_url()
    response = sqs.receive_message(
        QueueUrl=queue_url,
        MaxNumberOfMessages=1,
        WaitTimeSeconds=2,
        VisibilityTimeout=20,
    )
    messages = response.get("Messages", [])

    if not messages:
        flash("Antrean kosong. Tidak ada pesanan untuk diproses.", "warning")
        return redirect(url_for("admin_dashboard"))

    message = messages[0]
    body = json.loads(message["Body"])
    order_id = body["order_id"]

    order = orders_table().get_item(Key={"order_id": order_id}).get("Item")
    if not order:
        sqs.delete_message(QueueUrl=queue_url, ReceiptHandle=message["ReceiptHandle"])
        flash("Pesanan tidak ditemukan. Data antrean telah dibersihkan.", "warning")
        return redirect(url_for("admin_dashboard"))

    receipt_key = f"receipts/{order_id}.json"
    receipt_payload = {
        "receipt_id": f"RCP-{uuid.uuid4().hex[:8].upper()}",
        "order_id": order_id,
        "customer_name": order.get("customer_name"),
        "menu_name": order.get("menu_name"),
        "menu_category": order.get("menu_category"),
        "menu_image_path": order.get("menu_image_path", ""),
        "quantity": order.get("quantity"),
        "price": order.get("price"),
        "total": order.get("total"),
        "note": order.get("note"),
        "status": "READY",
        "processed_by": session.get("admin_username"),
        "processed_at": now_ts(),
    }

    s3_client().put_object(
        Bucket=S3_BUCKET_NAME,
        Key=receipt_key,
        Body=json.dumps(receipt_payload, cls=DecimalEncoder, indent=2),
        ContentType="application/json",
    )

    orders_table().update_item(
        Key={"order_id": order_id},
        UpdateExpression="SET #s = :status, receipt_key = :receipt_key, updated_at = :updated_at",
        ExpressionAttributeNames={"#s": "status"},
        ExpressionAttributeValues={
            ":status": "READY",
            ":receipt_key": receipt_key,
            ":updated_at": now_ts(),
        },
    )

    sqs.delete_message(QueueUrl=queue_url, ReceiptHandle=message["ReceiptHandle"])
    flash(f"Pesanan {order_id} selesai diproses. Receipt digital sudah tersedia.", "success")
    return redirect(url_for("admin_dashboard"))


@app.post("/admin/promo")
@admin_required
def add_promo():
    code = request.form.get("code", "").strip().upper()
    discount = request.form.get("discount", "0").strip()
    min_purchase = request.form.get("min_purchase", "0").strip()
    description = request.form.get("description", "").strip()

    if not code or not discount or not min_purchase:
        flash("Kode, diskon, dan minimal pembelian wajib diisi.", "danger")
        return redirect(url_for("admin_dashboard"))

    try:
        discount_val = to_decimal(discount)
        min_purchase_val = to_decimal(min_purchase)
    except Exception:
        flash("Diskon dan minimal pembelian harus berupa angka.", "danger")
        return redirect(url_for("admin_dashboard"))

    promo_id = f"PR-{uuid.uuid4().hex[:8].upper()}"
    promos_table().put_item(
        Item={
            "promo_id": promo_id,
            "code": code,
            "discount_value": discount_val,
            "min_purchase": min_purchase_val,
            "description": description,
            "is_active": True,
            "created_at": now_ts(),
        }
    )
    flash(f"Promo '{code}' berhasil ditambahkan.", "success")
    return redirect(url_for("admin_dashboard"))


@app.post("/admin/promo/<promo_id>/delete")
@admin_required
def delete_promo(promo_id):
    promos_table().delete_item(Key={"promo_id": promo_id})
    flash("Promo berhasil dihapus.", "success")
    return redirect(url_for("admin_dashboard"))


@app.get("/health")

def health():
    return {"status": "ok", "app": APP_NAME}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=True)
