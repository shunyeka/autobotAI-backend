from autobot_helpers import boto3_helper
from boto3.dynamodb.conditions import Key, Attr, And
from functools import reduce


class InstanceSchedule:
    __table__ = 'instance_schedule'

    def __init__(self):
        pass

    def __init__(self, params):
        self.data = params

    @staticmethod
    def create(params):
        pass

    @classmethod
    def find_one(cls, schedule_id, user_id):
        table = boto3_helper.get_dynamo_db_table(cls.__table__, True)
        result = table.query(
            KeyConditionExpression=Key('user_id').eq(user_id),
            FilterExpression=Attr('schedule_id').eq(schedule_id),
            Limit = 1
        )
        if result and result.get('Items'):
            return result['Items'][0]
        return None

    @classmethod
    def find(cls, filters):
        table = boto3_helper.get_dynamo_db_table(cls.__table__, True)
        response = table.scan(FilterExpression=reduce(And, ([Key(k).eq(v) for k, v in filters.items()])))
        return response['Items']

    def save(self):
        table = boto3_helper.get_dynamo_db_table(InstanceSchedule.__table__, True)
        response = table.put_item(
            Item=self.data
        )
        return response
