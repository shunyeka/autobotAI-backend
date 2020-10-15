from services.aws.data_fetch_service import DataFetchService
from services.aws.aws import AWS
from autobot_helpers import context_helper
import json
import traceback
import os


def fetch(event, context):
    email = None
    os.environ['ROOT_PATH'] = os.path.dirname(os.path.realpath(__file__))
    try:
        try:
            account_id = event['Records'][0]['Sns']['Message']
            email = event['Records'][0]['Sns']['Subject']
        except:
            return json.dumps({'success': False,
                               'error_code': 'DF_INSUFFICIENT_DATA',
                               'error': 'Insufficient data provided'})
        if not email or not account_id:
            return json.dumps(
                {'success': False, 'error_code': 'DF_INSUFFICIENT_DATA', 'error': 'Insufficient data provided'})
        context_helper.logger().info("Email received="+email)
        result = context_helper.initialize(email, account_id)
        if not result['success']:
            DataFetchService.index_failure_handler(email, account_id, result)
            return json.dumps(result)
        AWS.refresh_access_policy_for_current_account()
        response = DataFetchService.fetch_data()
        if response['success']:
            DataFetchService.index_success_handler(email, account_id)
        else:
            DataFetchService.index_failure_handler(email, account_id, response)
        return json.dumps(response)
    except BaseException as e:
        context_helper.logger().exception("Some exception while fetching data")
        traceback.print_exc()
        error_desc = traceback.format_exc()
        DataFetchService.index_failure_handler(email, account_id, error_desc)
        return json.dumps({'success': False, 'error_code': 'EXCEPTION', 'message': error_desc})