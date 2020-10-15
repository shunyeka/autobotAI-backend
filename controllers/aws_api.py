from flask import Blueprint, jsonify, json, request, render_template
from flask import current_app as app
from flask_cors import CORS

from autobot_helpers import context_helper, permission_helper
import traceback
from services.aws.aws import AWS
from services.aws.cost_governance import CostGovernance
from services.aws.data_fetch_service import DataFetchService
from services.aws.instance_scheduler import InstanceScheduler
from services.aws.maintenance_tasks_service import MaintenanceTasksService
from services.aws.security_issues_service import SecurityIssuesServices
from services.aws.unused_resources_service import UnusedResourcesServices
from models import aws_intent_history, aws_datapoint_history
from services.aws.utils import Constants, Helpers
from urllib.parse import unquote

aws_api = Blueprint('aws_api', __name__)
CORS(aws_api, resources={r"/*": {"origins": "*"}})


@aws_api.before_request
def init():
    if app.config["ENVIRONMENT"] != "local":
        try:
            user_email = request.environ['API_GATEWAY_AUTHORIZER']['claims']['email']
        except:
            return jsonify({"success": False, "error_code": "UNAUTHORIZED",
                            "error_message": "Not authorized"})
    else:
        user_email = "amit@shunyeka.com"
    account_id = request.view_args.get('account_id')
    if not permission_helper.has_account_permission(user_email, account_id):
        return jsonify({'unauthorized': True}), 401
    if 'attributes' not in context_helper.get_current_session() or \
            context_helper.get_current_session()['attributes']['email'] != user_email or\
            context_helper.get_current_session()['attributes']['accountNumber'] != account_id:
        result = context_helper.initialize(user_email, account_id)
        if not result['success']:
            return jsonify(result)


@aws_api.route('/<account_id>/insights/unusedResources', methods=['GET'])
def unused_resources(account_id):
    response = AWS.get_dashboard_data(account_id)
    if not response['success']:
        return jsonify(response)
    unused_resource_list = UnusedResourcesServices.get_unused_resources(response['data']['unusedResources'], account_id,
                                                                        response['timestamp'])
    return jsonify(unused_resource_list)


@aws_api.route('/<account_id>/insights/securityIssues', methods=['GET'])
def security_issues(account_id):
    response = AWS.get_dashboard_data(account_id)
    if not response['success']:
        return jsonify(response)
    security_issue_list = SecurityIssuesServices.get_security_issues(response['data']['securityIssues'], account_id,
                                                                     response['timestamp'])
    return jsonify(security_issue_list)


@aws_api.route('/<account_id>/insights/maintenanceTasks', methods=['GET'])
def maintenance_tasks(account_id):
    response = AWS.get_dashboard_data(account_id)
    if not response['success']:
        return jsonify(response)
    maintenance_task_list = MaintenanceTasksService.get_maintenance_tasks(response['data']['maintenance'], account_id,
                                                                          response['timestamp'])
    return jsonify(maintenance_task_list)


@aws_api.route('/<account_id>/insights/cost', methods=['GET'])
def cost_dashboard(account_id):
    response = CostGovernance.get_ri_and_budget_details(account_id)
    return jsonify(response)


@aws_api.route('/<account_id>/insights', methods=['GET', 'POST'])
def insights(account_id):
    response = AWS.get_dashboard_data(account_id)
    return jsonify(response)


@aws_api.route('/<account_id>/fixes/maintenanceTasks', methods=['POST'])
def fix_maintenance(account_id):
    request_json = request.get_json()
    result = MaintenanceTasksService.fix_maintenance_task(data=request_json)
    return jsonify(result)


@aws_api.route('/<account_id>/fixes/unusedResources', methods=['POST'])
def fix_unused_resource(account_id):
    request_json = request.get_json()
    result = UnusedResourcesServices.clean_unused_resource(data=request_json)
    return jsonify(result)


@aws_api.route('/<account_id>/fixes/securityIssues', methods=['POST'])
def fix_security_issues(account_id):
    request_json = request.get_json()
    result = SecurityIssuesServices.fix_security_issues(request_json)
    return jsonify(result)


@aws_api.route('/<account_id>/preferences/regions', methods=['GET'])
def get_region_preference(account_id):
    region_preference = AWS.get_regional_preference_details(context_helper.get_current_session()['attributes']['rootUserId'], account_id)
    return jsonify({'success': True, 'regionPreferences': region_preference})


@aws_api.route('/<account_id>/preferences/regions', methods=['POST', 'PUT'])
def save_region_preference(account_id):
    request_json = request.get_json()
    response = AWS.save_region_preference(account_id, request_json)
    return jsonify(response)


@aws_api.route('/<account_id>/reports/optimization', methods=['GET'])
def generate_optimization_report(account_id):
    from services.aws.support import Support
    support = Support()
    response = support.generate_report()
    if response['success']:
        return jsonify({'success': True, 'reportHtml': render_template("optimization_report.html",
                                                                       dict_data=response['response'])})
    else:
        return jsonify(response)


@aws_api.route('/<account_id>/instances', methods=['GET'])
def get_ssm_instances(account_id):
    try:
        filters = None
        try:
            filters = json.loads(unquote(request.args.get('filters')))
        except BaseException as e:
            print(e)
        if filters and filters.get('ssm'):
            aws = AWS()
            return jsonify({'success': True, 'resource_list': aws.get_ssm_instances(account_id)})
        else:
            intent_history = aws_intent_history.get_latest_by_account_id(account_id)
            instances = aws_datapoint_history.get_datapoints_by_type(account_id, intent_history['timestamp'], "ec2s")
            return jsonify({'success': True, 'resource_list': instances})
    except BaseException as e:
        print(traceback.format_exc())
        return jsonify({'success': False, 'error': "Some exception while loading instances",
                        'error_code': 'SOME_EXCEPTION'})


@aws_api.route('/<account_id>/baseline/fetchSchedule', methods=['POST'])
def initiate_data_fetch(account_id):
    email = context_helper.get_current_session()['attributes']['email']
    response = DataFetchService.schedule_data_fetch_for_account(email, account_id)
    return jsonify(response)


@aws_api.route('/<account_id>/instances', methods=['PUT'])
def enable_cw_for_instance(account_id):
    try:
        request_json = request.get_json()
        if not request_json['instanceIds']:
            return jsonify({'success': False, 'error_code': 'INVALID_PARAMS',
                            'message': "Instances IDs are required."})
        intent_history = aws_intent_history.get_latest_by_account_id(account_id)
        responses = []
        success = False
        for instance_id in request_json['instanceIds']:
            instance = aws_datapoint_history.get_datapoints_by_id(account_id, intent_history['timestamp'], instance_id)
            response = AWS.setup_cw_agent([instance_id], instance['region'])
            responses.append(response)
            if response["success"]:
                success = True
        return jsonify({"success": success, 'responses': responses})
    except BaseException as e:
        return jsonify({"success": False})

@aws_api.route('/<account_id>/instanceSchedules', methods=['POST', 'PUT'])
def create_instance_schedule(account_id):
    request_json = request.get_json()
    instance_scheduler = InstanceScheduler()
    response = instance_scheduler.create_schedule(account_id, request_json)
    return jsonify(response)

@aws_api.route('/<account_id>/instanceSchedules', methods=['GET'])
def get_instance_schedules(account_id):
    instance_scheduler = InstanceScheduler()
    response = instance_scheduler.list_schedules(account_id)
    if response:
        return jsonify({"success": True, "schedules": response})
    return jsonify({"success": True})


@aws_api.route('/<account_id>/instanceSchedules/<schedule_id>', methods=['DELETE'])
def delete_instance_schedule(account_id, schedule_id):
    instance_scheduler = InstanceScheduler()
    response = instance_scheduler.delete_schedule(account_id, schedule_id)
    return jsonify(response)

@aws_api.route("/<account_id>/test")
def test(account_id):
    AWS.refresh_access_policy_for_current_account();
    return jsonify({"success": True})




