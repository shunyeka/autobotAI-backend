import json
import os

from autobot_helpers import boto3_helper, context_helper
from models import cloud_service_provider
from services.aws.data_fetch_service import DataFetchService


def schedule(event, context):
    os.environ['ROOT_PATH'] = os.path.dirname(os.path.realpath(__file__))
    try:
        print('Running schedule on '+context_helper.app().config["ENVIRONMENT"])
        batch = 2
        accounts = cloud_service_provider.get_accounts_to_be_indexed(batch)
        print('found accounts to be indexed -------------')
        print(accounts)
        print('found accounts to be indexed -------------')
        sns_client = boto3_helper.get_client('sns', autobot_resources=True)
        current_count = 0
        for account in accounts:
            account_id = account['accountId']
            response = DataFetchService.schedule_data_fetch_for_account(account['userId'], account_id)
            current_count += 1
            if not current_count < batch:
                break
            print(response)
        return json.dumps({'success': True})
    except BaseException as e:
        context_helper.logger().exception("Some error occured while scheduling")
        return json.dumps({'success': False, 'error_code': 'EXCEPTION', 'message': repr(e)})

