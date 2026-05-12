import os

APP_NAME = os.getenv("APP_NAME", "Coffee Senja")
APP_SECRET_KEY = os.getenv("APP_SECRET_KEY", "coffee-senja-dev-secret")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
AWS_ENDPOINT_URL = os.getenv("AWS_ENDPOINT_URL", "http://localhost:4566")
DYNAMODB_ENDPOINT_URL = os.getenv("DYNAMODB_ENDPOINT_URL", AWS_ENDPOINT_URL)

S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "coffee-senja-localstack-receipts")
SQS_QUEUE_NAME = os.getenv("SQS_QUEUE_NAME", "coffee-senja-localstack-orders")
MENU_TABLE_NAME = os.getenv("MENU_TABLE_NAME", "CoffeeSenjaLocalstackMenu")
ORDERS_TABLE_NAME = os.getenv("ORDERS_TABLE_NAME", "CoffeeSenjaLocalstackOrders")
USERS_TABLE_NAME = os.getenv("USERS_TABLE_NAME", "CoffeeSenjaLocalstackUsers")
PROMOS_TABLE_NAME = os.getenv("PROMOS_TABLE_NAME", "CoffeeSenjaLocalstackPromos")

DEFAULT_ADMIN_USERNAME = os.getenv("DEFAULT_ADMIN_USERNAME", "admin")
DEFAULT_ADMIN_PASSWORD = os.getenv("DEFAULT_ADMIN_PASSWORD", "admin123")
