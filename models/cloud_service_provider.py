from datetime import datetime

from boto3.dynamodb.conditions import Attr, Key

from autobot_helpers import boto3_helper
from services.aws.utils import Helpers,Constants


def save(data):
    table = boto3_helper.get_dynamo_db_table("cloud_service_providers", True)
    if 'createdAt' not in data:
        data['createdAt'] = Helpers.timestamp()
        data['updatedAt'] = Helpers.timestamp()
    response = table.put_item(
        Item=data
    )
    return response


def get_by_email(email):
    table = boto3_helper.get_dynamo_db_table("cloud_service_providers", True)
    result = table.query(
        KeyConditionExpression=Key('userId').eq(email),
        FilterExpression=Attr('isActive').eq(True) & Attr('isUnauthorized').eq(False),
        Limit=1,
    )
    if result and result.get('Items'):
        return result['Items'][0]
    return None


def get_all_by_user_id(user_id, external_id=None):
    table = boto3_helper.get_dynamo_db_table("cloud_service_providers", True)
    filter_expression = None
    if external_id:
        filter_expression = Attr('externalId').eq(external_id)
    if filter_expression:
        result = table.query(
            KeyConditionExpression=Key('userId').eq(user_id),
            ProjectionExpression="userId,accountId,cspName,defaultRegion,activeRegions,isActive,"
                                 "indexFailures,lastIndexedAt,isUnauthorized,"
                                 "isResourcesTagged,accountPreferences,createdAt,updatedAt",
            FilterExpression=filter_expression
        )
    else:
        result = table.query(
            KeyConditionExpression=Key('userId').eq(user_id),
            ProjectionExpression="userId,accountId,cspName,defaultRegion,activeRegions,isActive,"
                                 "indexFailures,lastIndexedAt,isUnauthorized,"
                                 "isResourcesTagged,accountPreferences,createdAt,updatedAt"
        )
    if result and result.get('Items'):
        return result['Items']
    return None


def get_by_account_id(email, account_id, safe=False):
    table = boto3_helper.get_dynamo_db_table("cloud_service_providers", True)
    if safe:
        item = table.get_item(Key={
            'userId': email,
            'accountId': account_id
        },
            ProjectionExpression="userId,accountId,cspName,defaultRegion,activeRegions,isActive,"
                                 "indexFailures,lastIndexedAt,isUnauthorized,"
                                 "isResourcesTagged,accountPreferences,createdAt,updatedAt"
        )
    else:
        item = table.get_item(Key={
            'userId': email,
            'accountId': account_id
        })
    return item.get('Item', None)


def update_region_preference(email, account_id,  default_region, active_regions):
    table = boto3_helper.get_dynamo_db_table("cloud_service_providers", True)
    response = table.update_item(
        Key={
            'userId': email,
            'accountId': account_id
        },
        UpdateExpression="set #dRegion = :r, #aRegions = :s, #iActive = :t",
        ExpressionAttributeNames={"#dRegion": 'defaultRegion', '#aRegions': 'activeRegions', '#iActive': 'isActive'},
        ExpressionAttributeValues={
            ':r': default_region,
            ':s': active_regions,
            ':t': True,
        },
        ReturnValues="UPDATED_NEW"
    )


def get_accounts_to_be_indexed(batch=2):
    table = boto3_helper.get_dynamo_db_table("cloud_service_providers", True)
    today = datetime.utcnow().date().isoformat()
    response = table.scan(
        FilterExpression=(Attr('lastIndexedAt').not_exists() | Attr("lastIndexedAt").lt(today))
                         & Attr("isActive").eq(True) & Attr('roleArn').exists() & Attr('isUnauthorized').eq(False)
    )
    if 'Items' in response:
        return response['Items']
    return None


def mark_indexed(email, account_id):
    table = boto3_helper.get_dynamo_db_table("cloud_service_providers", True)
    table.update_item(
        Key={
            'userId': email,
            'accountId': account_id
        },
        UpdateExpression="set lastIndexedAt = :t, indexFailures = :c",
        ExpressionAttributeValues={
            ':t': Helpers.timestamp(),
            ':c': 0
        },
        ReturnValues="UPDATED_NEW"
    )


def update_failure_count(email, account_id,  count):
    table = boto3_helper.get_dynamo_db_table("cloud_service_providers", True)
    resp = table.update_item(
        Key={
            'userId': email,
            'accountId': account_id
        },
        UpdateExpression="set indexFailures = :i",
        ExpressionAttributeValues={
            ':i': count,
        },
        ReturnValues="UPDATED_NEW"
    )


def disable_account(email, account_id, unauthorized=False):
    table = boto3_helper.get_dynamo_db_table("cloud_service_providers", True)
    table.update_item(
        Key={
            'userId': email,
            'accountId': account_id
        },
        UpdateExpression="set isActive = :t, indexFailures = :c, isUnauthorized = :u",
        ExpressionAttributeValues={
            ':t': False,
            ':c': 0,
            ':u': unauthorized
        },
        ReturnValues="UPDATED_NEW"
    )


def get_all():
    table = boto3_helper.get_dynamo_db_table("cloud_service_providers", True)
    response = table.scan()
    return response['Items']


def update_all_csp():
    table = boto3_helper.get_dynamo_db_table("cloud_service_providers", True)
    response = table.scan(
        FilterExpression=Attr("defaultRegion").exists() and Attr('roleArn').exists() and Attr('externalId').exists()
    )
    print(response)
    # yesterday = (datetime.utcnow() - timedelta(days=1)).isoformat()
    if 'Items' in response:
        for item in response['Items']:
            print(item['userId'])
            response = table.update_item(
                Key={
                    'userId': item['email']
                },
                UpdateExpression="set isActive = :t, indexFailures = :c",
                ExpressionAttributeValues={
                    ':t': True,
                    ':c': 0
                },
                ReturnValues="UPDATED_NEW"
            )
            print(response)


def restore(items):
    table = boto3_helper.get_dynamo_db_table("cloud_service_providers", True)
    with table.batch_writer() as batch:
        for org_item in items:
            if 'roleArn' in org_item:
                item = {
                    'userId': org_item['email'],
                    'accountId': org_item['roleArn'][13:25],
                    'externalId': org_item.get('externalId'),
                    'roleArn': org_item.get('roleArn'),
                    'cspName': Constants.CSPTypes.AWS.value,
                    'defaultRegion': org_item.get('defaultRegion'),
                    'activeRegions': org_item.get('activeRegions'),
                    'isActive': org_item.get('isActive'),
                    'indexFailures': org_item.get('indexFailures'),
                    'lastIndexedAt': org_item.get('lastIndexedAt'),
                    'isUnauthorized': org_item.get('unauthorized', False),
                    'isResourcesTagged': org_item.get('resourcesTagged', False),
                    'accountPreferences': org_item.get('accountPreferences'),
                    'createdAt': org_item.get('createdAt', datetime.utcnow().isoformat()),
                    'updatedAt': org_item.get('updatedAt', datetime.utcnow().isoformat())
                }
                final_item = {k: v for k, v in item.items() if v is not None}
                batch.put_item(Item=final_item)