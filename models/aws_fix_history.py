from datetime import datetime

from autobot_helpers import boto3_helper


def save(account_number, timestamp, data, success=True, error_message=None, fix_type=None):
    table = boto3_helper.get_dynamo_db_table("aws_fix_history", True)
    table.put_item(
        Item={
            "accountId": account_number,
            "timestamp": datetime.utcnow().isoformat(),
            "intentTimestamp": timestamp,
            "fixType": fix_type,
            "data": data,
            "success": success,
            'error_message': error_message
        }
    )
