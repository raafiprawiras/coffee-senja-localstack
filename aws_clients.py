from decimal import Decimal
import json
import boto3
from botocore.config import Config

from config import AWS_ENDPOINT_URL, AWS_REGION


def _client(service_name: str):
    return boto3.client(
        service_name,
        endpoint_url=AWS_ENDPOINT_URL,
        region_name=AWS_REGION,
        aws_access_key_id="test",
        aws_secret_access_key="test",
        config=Config(retries={"max_attempts": 3, "mode": "standard"}),
    )


def _resource(service_name: str):
    return boto3.resource(
        service_name,
        endpoint_url=AWS_ENDPOINT_URL,
        region_name=AWS_REGION,
        aws_access_key_id="test",
        aws_secret_access_key="test",
        config=Config(retries={"max_attempts": 3, "mode": "standard"}),
    )


def s3_client():
    return _client("s3")


def sqs_client():
    return _client("sqs")


def dynamodb_resource():
    return _resource("dynamodb")


def dynamodb_client():
    return _client("dynamodb")


class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            if obj % 1 == 0:
                return int(obj)
            return float(obj)
        return super().default(obj)


def to_decimal(value):
    if value is None or value == "":
        return Decimal("0")
    return Decimal(str(value))
