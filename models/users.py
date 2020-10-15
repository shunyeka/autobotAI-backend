from boto3.dynamodb.conditions import Attr, Key

from autobot_helpers import boto3_helper
from services.aws.utils import Constants
from services.aws.utils import Helpers


def get_by_email(email):
    table = boto3_helper.get_dynamo_db_table("users", True)
    result = table.query(
        KeyConditionExpression=Key('id').eq(email),
        Limit=1,
    )
    if result and result.get('Items'):
        return result['Items'][0]
    return None


def get_all_by_root(email):
    table = boto3_helper.get_dynamo_db_table("users", True)
    response = table.scan(
        FilterExpression=Attr('rootUserId').eq(email) & Attr('userType').ne('ROOT')
    )
    if 'Items' in response:
        return response['Items']
    return None


def create_sub_user(user_data, root_user_id):
    table = boto3_helper.get_dynamo_db_table("users", True)
    item = {
        'id': user_data['email'],
        'rootUserId': root_user_id,
        'name': user_data.get('name'),
        'phone': user_data.get('phone'),
        'userType': Constants.UserTypes.SUB_USER.value,
        'isActive': False,
        'readOnly': user_data.get('readOnly'),
        'createdAt': Helpers.timestamp(),
        'updatedAt': Helpers.timestamp()
    }
    if user_data['accounts']:
        item['preferences'] = {'defaultAccount': user_data['accounts'][0]}
        item['permissions'] = {'accounts': user_data['accounts']}
    response = table.put_item(Item=item)
    return response


def get_root_user(email):
    user = get_by_email(email)
    if not user:
        return None
    if user['userType'] == Constants.UserTypes.ROOT.value:
        return user
    else:
        root_user = get_by_email(user['rootUserId'])
        return root_user


def get_all():
    table = boto3_helper.get_dynamo_db_table("users", True)
    response = table.scan()
    return response['Items']


def update_preferences(user_id, root_user_id, preferences):
    table = boto3_helper.get_dynamo_db_table("users", True)
    response = table.update_item(
        Key={
            'id': user_id,
            'rootUserId': root_user_id,
        },
        UpdateExpression="set #prefs = :p",
        ExpressionAttributeNames={"#prefs": 'preferences'},
        ExpressionAttributeValues={
            ':p': preferences
        },
        ReturnValues="UPDATED_NEW"
    )


def update_permissions(user_id, root_user_id, permissions):
    table = boto3_helper.get_dynamo_db_table("users", True)
    response = table.update_item(
        Key={
            'id': user_id,
            'rootUserId': root_user_id,
        },
        UpdateExpression="set #perms = :p",
        ExpressionAttributeNames={"#perms": 'permissions'},
        ExpressionAttributeValues={
            ':p': permissions
        },
        ReturnValues="UPDATED_NEW"
    )


def restore(items):
    import simplejson
    from datetime import datetime
    table = boto3_helper.get_dynamo_db_table("users", True)
    file_name = "live_cloud_service_provider"
    csps = None
    with open('backup/'+file_name+'.json') as f:
            csps = simplejson.loads(f.read())
    with table.batch_writer() as batch:
        for org_item in items:
            csp = next((item for item in csps if item["email"] == org_item['email']), None)
            item = {
                    'id': org_item['email'],
                    'rootUserId': org_item['email'],
                    'name': org_item.get('name'),
                    'phone': org_item.get('phone'),
                    'userType': Constants.UserTypes.ROOT.value,
                    'isActive': True,
                    'createdAt': datetime.utcfromtimestamp(org_item.get('createdAt')/1000.0).isoformat(),
                    'updatedAt': datetime.utcfromtimestamp(org_item.get('updatedAt')/1000.0).isoformat()
                }
            if csp:
                if 'roleArn' in csp:
                    account_id = csp['roleArn'][13:25]
                    item['preferences'] = {'defaultAccount': account_id}
                    item['permissions'] = {'accounts': [account_id]}
                item['accessToken'] = csp.get('accessToken')
            final_item = {k: v for k, v in item.items() if v is not None}
            batch.put_item(Item=final_item)