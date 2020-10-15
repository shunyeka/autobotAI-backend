from boto3.dynamodb.conditions import Key, Attr
from autobot_helpers import boto3_helper
from services.aws.utils import Constants


def __get_table():
    return boto3_helper.get_dynamo_db_table("aws_datapoint_history", True)


def get_datapoints_by_id(account_number, timestamp, resource_id):
    table = __get_table()
    result = table.query(
        KeyConditionExpression=Key('intentId').eq(account_number + '_' + timestamp),
        FilterExpression=Attr('id').eq(resource_id),
    )
    if result and result.get('Items'):
        return result['Items'][0]


def get_datapoints_by_ids(account_number, timestamp, resource_ids):
    table = __get_table()
    items = []
    if len(resource_ids) > 99:
        result = table.query(
            KeyConditionExpression=Key('intentId').eq(account_number + '_'+timestamp),
        )
        if result and result.get('Items'):
            for item in result['Items']:
                if item['id'] in resource_ids:
                    items.append(item)
    else:
        result = table.query(
            KeyConditionExpression=Key('intentId').eq(account_number + '_' + timestamp),
            FilterExpression=Attr('id').is_in(resource_ids),
        )
        if result and result.get('Items'):
            items = result['Items']
    return items


def get_datapoints_by_type(account_number, timestamp, data_type):
    table = __get_table()
    result = table.query(
        KeyConditionExpression=Key('intentId').eq(account_number + '_' + timestamp) & Key('itemId').begins_with(data_type),
    )
    if result and result.get('Items'):
        items = result['Items']
        return items



def save_all_resources(account_number, timestamp, dataset):
    table = __get_table()
    with table.batch_writer() as batch:
        for region in dataset['regionalData']:
            for datapoint in dataset['regionalData'][region]['datapoints']:
                if dataset['regionalData'][region]['datapoints'][datapoint]:
                    for item in dataset['regionalData'][region]['datapoints'][datapoint]:
                        item['intentId'] = account_number + '_' + timestamp
                        item['itemId'] = datapoint+'_'+item['id']
                        item['region'] = region
                        item['type'] = Constants.datapoint_display_names[datapoint]
                        batch.put_item(Item=item)
        for datapoint in dataset['globalData']['datapoints']:
            if dataset['globalData']['datapoints'][datapoint]:
                if isinstance(dataset['globalData']['datapoints'][datapoint], list):
                    for item in dataset['globalData']['datapoints'][datapoint]:
                        item['intentId'] = account_number + '_' + timestamp
                        item['itemId'] = datapoint + '_' + item['id']
                        item['region'] = 'global'
                        item['type'] = Constants.datapoint_display_names[datapoint]
                        batch.put_item(Item=item)

