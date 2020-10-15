import uuid

from boto3.dynamodb.conditions import Key

from autobot_helpers import boto3_helper
from services.aws.utils import Helpers


class AccountSetup:
    __colname__ = 'account_setup'

    def __init__(self):
        pass

    def __init__(self, externalId, user_id, created, updated):
        self.externalId = externalId
        self.user_id = user_id
        self.created = created
        self.updated = updated
        self.alias = None

    def __repr__(self):
        return u'AccountSetup(ExternalId={}, userId={}, created={}, updated={})'.format(
                self.externalId, self.user_id, self.created, self.updated)

    @staticmethod
    def new(user_id):
        account_setup = AccountSetup(str(uuid.uuid4()), user_id, Helpers.timestamp(), Helpers.timestamp())
        account_setup.save()
        return account_setup.externalId

    def save(self):
        table = boto3_helper.get_dynamo_db_table(AccountSetup.__colname__, True)
        response = table.put_item(
            Item=self.to_dict()
        )
        return response

    @staticmethod
    def from_dict(externalId, doc):
        return AccountSetup(externalId, doc['user_id'], doc['created'], doc['updated'])

    def to_dict(self):
        return vars(self)

    @staticmethod
    def get(externalId):
        table = boto3_helper.get_dynamo_db_table(AccountSetup.__colname__, True)
        result = table.query(
            KeyConditionExpression=Key('externalId').eq(externalId),
            Limit=1,
        )
        if result and result.get('Items'):
            return AccountSetup.from_dict(externalId, result['Items'][0])
        return None
