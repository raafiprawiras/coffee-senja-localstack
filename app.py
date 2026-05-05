import json
import os
import time
import uuid
from decimal import Decimal
from functools import wraps

from flask import Flask, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash
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


def now_ts():
    return int(time.time())


def rupiah(value):
    value = int(value or 0)
    return "Rp {:,}".format(value).replace(",", ".")


app.jinja_env.filters["rupiah"] = rupiah


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


def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if not session.get("admin_username"):
            flash("Silakan login sebagai admin terlebih dahulu.", "warning")
            return redirect(url_for("login"))
        return view(*args, **kwargs)

    return wrapped_view


@app.context_processor
def inject_globals():
    try:
        order_count = len(all_orders())
    except Exception:
        order_count = 0
    return {"app_name": APP_NAME, "admin_username": session.get("admin_username"), "order_count": order_count}


@app.get("/")
def customer_page():
    menus = active_menus()
    orders = [order for order in all_orders()[:10]]
    return render_template("index.html", menus=menus, orders=orders)


@app.post("/order")
def create_order():
    customer_name = request.form.get("customer_name", "").strip()
    menu_id = request.form.get("menu_id", "").strip()
    quantity = int(request.form.get("quantity", "1") or 1)
    note = request.form.get("note", "").strip()

    if not customer_name:
        flash("Nama customer wajib diisi.", "danger")
        return redirect(url_for("customer_page"))

    if quantity < 1:
        quantity = 1

    menu = menu_table().get_item(Key={"menu_id": menu_id}).get("Item")
    if not menu or not menu.get("is_active", True):
        flash("Menu tidak ditemukan atau sedang tidak aktif.", "danger")
        return redirect(url_for("customer_page"))

    order_id = f"ORD-{uuid.uuid4().hex[:8].upper()}"
    price = to_decimal(menu.get("price"))
    total = price * Decimal(quantity)

    order = {
        "order_id": order_id,
        "customer_name": customer_name,
        "menu_id": menu_id,
        "menu_name": menu.get("name"),
        "menu_category": menu.get("category"),
        "menu_image_path": menu.get("image_path", ""),
        "quantity": quantity,
        "price": price,
        "total": total,
        "note": note,
        "status": "QUEUED",
        "receipt_key": "",
        "created_at": now_ts(),
        "updated_at": now_ts(),
    }

    orders_table().put_item(Item=order)

    message = {
        "order_id": order_id,
        "customer_name": customer_name,
        "menu_name": menu.get("name"),
        "menu_image_path": menu.get("image_path", ""),
        "quantity": quantity,
        "total": int(total),
        "created_at": order["created_at"],
    }
    sqs_client().send_message(QueueUrl=get_queue_url(), MessageBody=json.dumps(message, cls=DecimalEncoder))

    flash(f"Pesanan {order_id} berhasil dibuat. Barista sedang menyiapkan pesananmu.", "success")
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
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        user = users_table().get_item(Key={"username": username}).get("Item")
        if user and check_password_hash(user.get("password_hash", ""), password):
            session["admin_username"] = username
            flash("Login admin berhasil.", "success")
            return redirect(url_for("admin_dashboard"))

        flash("Username atau password salah.", "danger")

    return render_template("login.html")


@app.get("/logout")
def logout():
    session.clear()
    flash("Logout berhasil.", "success")
    return redirect(url_for("customer_page"))


@app.get("/admin")
@login_required
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
    return render_template("admin.html", menus=menus, orders=orders, queue_orders=queue_orders, stats=stats)


@app.post("/admin/menu")
@login_required
def add_menu():
    name = request.form.get("name", "").strip()
    category = request.form.get("category", "Signature").strip()
    description = request.form.get("description", "").strip()
    price = request.form.get("price", "0").strip()
    emoji = request.form.get("emoji", "☕").strip() or "☕"

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
            "emoji": emoji,
            "image_path": image_path,
            "is_active": True,
            "created_at": now_ts(),
            "updated_at": now_ts(),
        }
    )

    flash(f"Menu baru '{name}' berhasil ditambahkan dan aktif di halaman customer.", "success")
    return redirect(url_for("admin_dashboard"))


@app.post("/admin/menu/<menu_id>/toggle")
@login_required
def toggle_menu(menu_id):
    item = menu_table().get_item(Key={"menu_id": menu_id}).get("Item")
    if not item:
        flash("Menu tidak ditemukan.", "danger")
        return redirect(url_for("admin_dashboard"))

    new_status = not item.get("is_active", True)
    menu_table().update_item(
        Key={"menu_id": menu_id},
        UpdateExpression="SET is_active = :active",
        ExpressionAttributeValues={":active": new_status},
    )
    flash("Status menu berhasil diubah.", "success")
    return redirect(url_for("admin_dashboard"))


@app.post("/admin/menu/<menu_id>/photo")
@login_required
def update_menu_photo(menu_id):
    item = menu_table().get_item(Key={"menu_id": menu_id}).get("Item")
    if not item:
        flash("Menu tidak ditemukan.", "danger")
        return redirect(url_for("admin_dashboard"))

    try:
        image_path = save_menu_image(request.files.get("image"))
    except ValueError as exc:
        flash(str(exc), "danger")
        return redirect(url_for("admin_dashboard"))

    if not image_path:
        flash("Pilih file foto terlebih dahulu.", "warning")
        return redirect(url_for("admin_dashboard"))

    menu_table().update_item(
        Key={"menu_id": menu_id},
        UpdateExpression="SET image_path = :image_path, updated_at = :updated_at",
        ExpressionAttributeValues={":image_path": image_path, ":updated_at": now_ts()},
    )
    flash(f"Foto menu '{item.get('name')}' berhasil diperbarui.", "success")
    return redirect(url_for("admin_dashboard"))


@app.post("/admin/process-queue")
@login_required
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


@app.get("/health")
def health():
    return {"status": "ok", "app": APP_NAME}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=True)
