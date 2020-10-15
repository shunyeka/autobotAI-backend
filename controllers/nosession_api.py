from flask import Blueprint, jsonify, request
from flask import current_app as app
from flask_cors import CORS

import traceback
from autobot_helpers import permission_helper, context_helper
from models import cloud_service_provider, users
from models.account_setup import AccountSetup
from botocore.exceptions import ClientError
from services.aws.cognito import Cognito

nosession_api = Blueprint('nosession_api', __name__)
cors = CORS(nosession_api, resources={r"/*": {"origins": "*"}})

user_email = None


@nosession_api.before_request
def init():
    global user_email
    if app.config["ENVIRONMENT"] != "local":
        try:
            user_email = request.environ['API_GATEWAY_AUTHORIZER']['claims']['email']
        except:
            return jsonify({"success": False, "error_code": "UNAUTHORIZED",
                            "error_message": "Not authorized"})
    else:
        user_email = "amit@shunyeka.com"
    account_id = request.view_args.get('account_id')
    if account_id and not permission_helper.has_account_permission(user_email, account_id):
        return jsonify({'unauthorized': True}), 401


@nosession_api.route('/accountSetup', methods=['POST'])
def account_setup_init():
    return jsonify({'externalId': AccountSetup.new(user_email)})


@nosession_api.route('/accountSetup', methods=['PUT'])
def account_setup_update():
    request_json = request.get_json()
    if not request_json.get("externalId") or not request_json.get("accountSetupAlias"):
        return jsonify({'error': "Missing required parameters", 'error_code': 'BAD_REQUEST', 'success': False}), 400
    external_id = request_json["externalId"]
    account_setup_name = request_json["accountSetupAlias"]
    account_setup = AccountSetup.get(external_id)
    if account_setup:
        account_setup.alias = account_setup_name
        account_setup.save()
        return jsonify({'success': True})
    return jsonify({'error': "Invalid external_id", 'error_code': 'BAD_REQUEST', 'success': False}), 400


@nosession_api.route('/users/preferences', methods=['GET'])
def get_user_preferences():
    try:
        return jsonify({'success': True, 'preferences': users.get_by_email(user_email)['preferences']})
    except KeyError as e:
        error_stack = traceback.format_exc()
        context_helper.logger().exception("Some exception occurred while getting preferences, message=%s", error_stack)
        return jsonify({"success": False, "error_code": "NO_PREF",
                        "error_message": "Preferences not found. Account not setup yet."})
    except BaseException as e:
        print(traceback.format_exc())
        return jsonify({'success': False, 'error': "User not found", 'error_code': 'USER_NOT_FOUND'})


@nosession_api.route('/users/preferences', methods=['PATCH'])
def update_preferences():
    request_json = request.get_json()
    user = users.get_by_email(user_email)
    current_pref = user['preferences']
    for prop in request_json:
        current_pref[prop] = request_json[prop]
    users.update_preferences(user['id'], user['rootUserId'], current_pref)
    return jsonify({'success': True})


@nosession_api.route('/users/accounts/<account_id>', methods=['GET'])
def get_user_account(account_id):
    root_user = users.get_root_user(user_email)
    csp = cloud_service_provider.get_by_account_id(root_user['id'], account_id, safe=True)
    if csp:
        return jsonify({'success': True, 'account': csp})
    return jsonify({'success': True, 'account': None})


@nosession_api.route('/users/me', methods=['GET'])
def get_user_details():
    try:
        user = users.get_by_email(user_email)
        user_data = {
            "userType": user['userType'],
            "preferences": user['preferences']
        }
        return jsonify({'success': True, 'user': user_data})
    except KeyError as e:
        error_stack = traceback.format_exc()
        context_helper.logger().exception("Some exception occurred while getting preferences, message=%s", error_stack)
        return jsonify({"success": False, "error_code": "NO_PREF",
                        "error_message": "Preferences not found. Account not setup yet."})
    except BaseException as e:
        print(traceback.format_exc())
        return jsonify({'success': False, 'error': "User not found", 'error_code': 'USER_NOT_FOUND'})


@nosession_api.route('/users/accounts', methods=['GET'])
def get_user_accounts():
    try:
        root_user = users.get_root_user(user_email)
        externalId = request.args.get('externalId')
        if externalId:
            csps = cloud_service_provider.get_all_by_user_id(root_user['id'], external_id=externalId)
        else:
            csps = cloud_service_provider.get_all_by_user_id(root_user['id'])
        if csps:
            return jsonify({'success': True, 'accounts': csps})
        return jsonify({'success': True, 'accounts': []})
    except BaseException as e:
        return jsonify({'success': False, 'error': "Accounts not found", 'error_code': 'ACCOUNTS_NOT_FOUND'})


@nosession_api.route('/subusers', methods=['GET'])
def get_subuser_accounts():
    try:
        sub_users = users.get_all_by_root(user_email)
        for sub_user in sub_users:
            if sub_user.get('accessToken'):
                del sub_user['accessToken']
                sub_user['alexaEnabled'] = True
        return jsonify({'success': True, 'sub_users': sub_users})
    except BaseException as e:
        return jsonify({'success': False, 'error': "Accounts not found", 'error_code': 'ACCOUNTS_NOT_FOUND'})


@nosession_api.route('/subusers', methods=['POST'])
def create_subuser():
    try:
        request_json = request.get_json()
        cognito = Cognito()
        response = cognito.create_sub_user(sub_user_data=request_json, root_user=user_email)
        uc_response = users.create_sub_user(request_json, user_email)
        return jsonify({"success": True})
    except ClientError as e:
        return jsonify({'success': False, 'error': e.response["Error"]["Message"], 'error_code': e.response["Error"]["Code"]})
    except BaseException as e:
        import traceback
        print(traceback.format_exc())
        return jsonify({'success': False, 'error': "Could not create Sub User", 'error_code': 'USER_NOT_CREATED'})


@nosession_api.route('/subusers/<user_id>', methods=['PUT'])
def edit_subuser(user_id):
    try:
        root_user = users.get_root_user(user_email)
        externalId = request.args.get('externalId')
        if externalId:
            csps = cloud_service_provider.get_all_by_user_id(root_user['id'], external_id=externalId)
        else:
            csps = cloud_service_provider.get_all_by_user_id(root_user['id'])
        if csps:
            return jsonify({'success': True, 'accounts': csps})
        return jsonify({'success': True, 'accounts': []})
    except BaseException as e:
        return jsonify({'success': False, 'error': "Accounts not found", 'error_code': 'ACCOUNTS_NOT_FOUND'})
