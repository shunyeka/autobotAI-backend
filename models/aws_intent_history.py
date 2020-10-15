from autobot_helpers import boto3_helper
from boto3.dynamodb.conditions import Key


def get_latest_by_account_id(account_id):
    table = boto3_helper.get_dynamo_db_table("aws_intent_history", True)
    result = table.query(
      KeyConditionExpression=Key('cid').eq(account_id+'_AllResources'),
      ScanIndexForward=False,
      Limit=1,
    )
    if result and result.get('Items'):
        return result['Items'][0]
    return None


def update_metadata(timestamp, account_id, metadata, intent_type, issue_type):
    table = boto3_helper.get_dynamo_db_table("aws_intent_history", True)
    cid = account_id + "_AllResources"
    table.update_item(
        Key={
            'cid': cid,
            'timestamp': timestamp
        },
        UpdateExpression="set #metadata.#intentType.#issueType = :r",
        ExpressionAttributeNames={"#metadata": 'data', '#intentType': intent_type, '#issueType': issue_type},
        ExpressionAttributeValues={
            ':r': metadata,
        },
        ReturnValues="UPDATED_NEW"
    )


def get_by_intent_id(timestamp, account_id):
    table = boto3_helper.get_dynamo_db_table("aws_intent_history", True)
    cid = account_id+"_AllResources"
    result = table.query(
        KeyConditionExpression=Key('cid').eq(cid) & Key('timestamp').eq(timestamp),
    )
    if result and result.get('Items'):
        return result['Items'][0]
    return None


def save(account_number, intent, timestamp, data):
    table = boto3_helper.get_dynamo_db_table("aws_intent_history", True)
    table.put_item(
        Item={
          "cid": account_number + "_" + intent,
          "timestamp": timestamp,
          "data": data
        }
    )
