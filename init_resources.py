import time
from decimal import Decimal
from botocore.exceptions import ClientError, EndpointConnectionError
from werkzeug.security import generate_password_hash

from aws_clients import dynamodb_client, dynamodb_resource, s3_client, sqs_client
from config import (
    DEFAULT_ADMIN_PASSWORD,
    DEFAULT_ADMIN_USERNAME,
    MENU_TABLE_NAME,
    ORDERS_TABLE_NAME,
    S3_BUCKET_NAME,
    SQS_QUEUE_NAME,
    USERS_TABLE_NAME,
    PROMOS_TABLE_NAME,
)


def wait_for_localstack(max_attempts=45):
    print("Menunggu LocalStack...")
    s3 = s3_client()
    for attempt in range(1, max_attempts + 1):
        try:
            s3.list_buckets()
            return
        except (EndpointConnectionError, ClientError) as exc:
            print(f"LocalStack belum siap ({attempt}/{max_attempts}): {exc}")
            time.sleep(2)
    raise RuntimeError("LocalStack tidak siap. Pastikan container LocalStack berjalan.")


def table_exists(table_name):
    client = dynamodb_client()
    try:
        client.describe_table(TableName=table_name)
        return True
    except ClientError as exc:
        if exc.response["Error"]["Code"] == "ResourceNotFoundException":
            return False
        raise


def create_table(table_name, partition_key):
    if table_exists(table_name):
        return

    client = dynamodb_client()
    client.create_table(
        TableName=table_name,
        KeySchema=[{"AttributeName": partition_key, "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": partition_key, "AttributeType": "S"}],
        BillingMode="PAY_PER_REQUEST",
    )
    waiter = client.get_waiter("table_exists")
    waiter.wait(TableName=table_name)


def create_bucket():
    s3 = s3_client()
    try:
        s3.head_bucket(Bucket=S3_BUCKET_NAME)
    except ClientError:
        s3.create_bucket(Bucket=S3_BUCKET_NAME)


def create_queue():
    sqs = sqs_client()
    sqs.create_queue(QueueName=SQS_QUEUE_NAME)


def seed_admin_user():
    db = dynamodb_resource()
    table = db.Table(USERS_TABLE_NAME)
    existing = table.get_item(Key={"username": DEFAULT_ADMIN_USERNAME}).get("Item")
    if existing:
        return

    table.put_item(
        Item={
            "username": DEFAULT_ADMIN_USERNAME,
            "password_hash": generate_password_hash(DEFAULT_ADMIN_PASSWORD),
            "role": "ADMIN",
            "created_at": int(time.time()),
        }
    )


def seed_menu():
    db = dynamodb_resource()
    table = db.Table(MENU_TABLE_NAME)
    existing = table.scan().get("Items", [])
    if existing:
        default_images = {
            "menu-espresso": "uploads/menu/espresso.svg",
            "menu-cappuccino": "uploads/menu/cappuccino.svg",
            "menu-caramel-latte": "uploads/menu/caramel-latte.svg",
            "menu-matcha-latte": "uploads/menu/matcha-latte.svg",
            "menu-croissant": "uploads/menu/croissant.svg",
            "menu-tiramisu": "uploads/menu/tiramisu.svg",
        }
        for item in existing:
            menu_id = item.get("menu_id")
            if menu_id in default_images and not item.get("image_path"):
                table.update_item(
                    Key={"menu_id": menu_id},
                    UpdateExpression="SET image_path = :image_path",
                    ExpressionAttributeValues={":image_path": default_images[menu_id]},
                )
        return

    menus = [
        {
            "menu_id": "menu-espresso",
            "name": "Espresso",
            "category": "Coffee",
            "description": "Rasa pekat dengan body kuat dan aroma roasted beans yang khas.",
            "price": Decimal("22000"),
            "emoji": "☕",
            "is_active": True,
            "image_path": "uploads/menu/espresso.svg",
            "created_at": int(time.time()),
        },
        {
            "menu_id": "menu-cappuccino",
            "name": "Cappuccino",
            "category": "Coffee",
            "description": "Perpaduan espresso dengan susu berbusa lembut dan rasa seimbang.",
            "price": Decimal("32000"),
            "emoji": "☕",
            "is_active": True,
            "image_path": "uploads/menu/cappuccino.svg",
            "created_at": int(time.time()),
        },
        {
            "menu_id": "menu-caramel-latte",
            "name": "Caramel Latte",
            "category": "Coffee",
            "description": "Espresso dengan susu creamy dan caramel manis yang lembut.",
            "price": Decimal("36000"),
            "emoji": "🥤",
            "is_active": True,
            "image_path": "uploads/menu/caramel-latte.svg",
            "created_at": int(time.time()),
        },
        {
            "menu_id": "menu-matcha-latte",
            "name": "Matcha Latte",
            "category": "Non-Coffee",
            "description": "Matcha premium dengan susu lembut, creamy, dan menenangkan.",
            "price": Decimal("34000"),
            "emoji": "🍵",
            "is_active": True,
            "image_path": "uploads/menu/matcha-latte.svg",
            "created_at": int(time.time()),
        },
        {
            "menu_id": "menu-croissant",
            "name": "Croissant",
            "category": "Snack",
            "description": "Croissant buttery yang renyah di luar dan lembut di dalam.",
            "price": Decimal("28000"),
            "emoji": "🥐",
            "is_active": True,
            "image_path": "uploads/menu/croissant.svg",
            "created_at": int(time.time()),
        },
        {
            "menu_id": "menu-tiramisu",
            "name": "Tiramisu",
            "category": "Dessert",
            "description": "Perpaduan mascarpone lembut dan kopi dengan cita rasa klasik.",
            "price": Decimal("38000"),
            "emoji": "🍰",
            "is_active": True,
            "image_path": "uploads/menu/tiramisu.svg",
            "created_at": int(time.time()),
        },
    ]

    with table.batch_writer() as batch:
        for item in menus:
            batch.put_item(Item=item)


def seed_promos():
    db = dynamodb_resource()
    table = db.Table(PROMOS_TABLE_NAME)
    existing = table.scan().get("Items", [])
    if existing:
        return

    promos = [
        {
            "promo_id": "PR-WELCOME",
            "code": "SENJAHOO",
            "discount_value": Decimal("10000"),
            "description": "Potongan Rp 10.000 untuk member baru.",
            "min_purchase": Decimal("50000"),
            "is_active": True,
            "created_at": int(time.time()),
        },
        {
            "promo_id": "PR-SIGNATURE",
            "code": "KOPISTIK",
            "discount_value": Decimal("5000"),
            "description": "Potongan Rp 5.000 khusus menu signature.",
            "min_purchase": Decimal("30000"),
            "is_active": True,
            "created_at": int(time.time()),
        },
    ]

    with table.batch_writer() as batch:
        for item in promos:
            batch.put_item(Item=item)


def main():
    wait_for_localstack()
    create_table(MENU_TABLE_NAME, "menu_id")
    create_table(ORDERS_TABLE_NAME, "order_id")
    create_table(USERS_TABLE_NAME, "username")
    create_table(PROMOS_TABLE_NAME, "promo_id")
    create_bucket()
    create_queue()
    seed_admin_user()
    seed_menu()
    seed_promos()

    print("Resource siap:")
    print(
        {
            "dynamodb_tables": [MENU_TABLE_NAME, ORDERS_TABLE_NAME, USERS_TABLE_NAME, PROMOS_TABLE_NAME],
            "sqs_queue": SQS_QUEUE_NAME,
            "s3_bucket": S3_BUCKET_NAME,
            "admin_login": f"{DEFAULT_ADMIN_USERNAME} / {DEFAULT_ADMIN_PASSWORD}",
        }
    )


if __name__ == "__main__":
    main()
