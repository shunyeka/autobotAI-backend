import json
import os
import traceback
from boto3.dynamodb.conditions import Attr

from autobot_helpers import boto3_helper, context_helper


class AwsAccessPolicyDoc(object):
    __colname__ = 'aws_config'

    def __init__(self, id, name, description, json, active):
        self.id = id
        self.name = name
        self.description = description
        self.json = json
        self.active = active

    def __repr__(self):
        return u'AwsAccessPolicyDoc(ID={}, name={}, description={}, json={}, ' \
               u'active={})'.format(
            self.id, self.name, self.description, self.json, self.active)

    @staticmethod
    def get_active_docs():
        table = boto3_helper.get_dynamo_db_table(AwsAccessPolicyDoc.__colname__)
        response = table.scan(FilterExpression=Attr('active').eq(True))
        return response['Items']

