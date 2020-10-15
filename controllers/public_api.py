import traceback

from flask import Blueprint, jsonify, request
from flask_cors import CORS

from autobot_helpers import context_helper
from models import cloud_service_provider, users
from models.account_setup import AccountSetup
from services.aws.utils import Constants, Helpers
from models.aws_access_policy_docs import  AwsAccessPolicyDoc

public_api = Blueprint('public_api', __name__)
cors = CORS(public_api, resources={r"/*": {"origins": "*"}})


@public_api.route('/users/accounts', methods=['POST'])
def account_setup_callback():
    request_json = request.get_json()
    try:
        external_id = request_json.get('externalId')
        account_id = request_json.get('accountId')
        if not external_id or not account_id or not Helpers.is_uuid(external_id):
            return jsonify({'success': False, 'error': 'Invalid Params'})
        account_setup = AccountSetup.get(external_id)
        user = users.get_by_email(email=account_setup.user_id)
        if user['userType'] == Constants.UserTypes.ROOT.value:
            root_user = users.get_by_email(email=user['rootUserId'])
        csp = {
                'userId': root_user['id'] if root_user else user['id'],
                'accountId': account_id,
                'externalId': external_id,
                'roleArn': Helpers.arn(account_id),
                'cspName': Constants.CSPTypes.AWS.value,
                'indexFailures': 0,
                'isUnauthorized': False,
                'isResourcesTagged': False,
            }
        response = cloud_service_provider.save(csp)
        preferences = user.get('preferences')
        if not preferences:
            preferences = {'defaultAccount': csp['accountId']}
            users.update_preferences(user['id'], user['rootUserId'], preferences)
        permissions = user.get('permissions')
        if not permissions:
            permissions = {'accounts': [csp['accountId']]}
        else:
            permissions['accounts'].append(csp['accountId'])
        users.update_permissions(user['id'], user['rootUserId'], permissions)
        return jsonify({'success': True})
    except BaseException as e:
        err_str = traceback.format_exc()
        context_helper.logger().exception("Some exception while account_setup callback=%s", err_str)
        return jsonify({'success': False, 'error_code': 'EXCEPTION', 'message': err_str})
