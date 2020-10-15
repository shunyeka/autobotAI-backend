import copy
from datetime import datetime

from autobot_helpers import context_helper
from models import aws_datapoint_history
from models import aws_fix_history
from models import aws_intent_history
from services.aws.cloud_trail import CloudTrail
from services.aws.iam import IAM
from services.aws.utils import Constants


class SecurityIssuesServices:

    @staticmethod
    def get_security_issues(security_issues, account_id, timestamp):
        if not security_issues:
            return {'success': False, 'error_code': 'UNR_EMPTY_RESOURCE_LIST', 'error': "Resource list is empty"}

        resource_ids = []
        for resource_type in security_issues:
            if security_issues[resource_type].get('count') and 'itemList' in security_issues[resource_type]:
                for resource_id in security_issues[resource_type]['itemList']:
                    resource_ids.append(resource_id)
        resource_list = aws_datapoint_history.get_datapoints_by_ids(
            account_number=account_id,
            timestamp=timestamp,
            resource_ids=resource_ids)
        resource_list_with_issue = []
        for resource_type in security_issues:
            if security_issues[resource_type].get('count') and 'itemList' in security_issues[resource_type]:
                for resource_id in security_issues[resource_type]['itemList']:
                    resource_item = None
                    for resource in resource_list:
                        if resource['id'] == resource_id:
                            resource_item = copy.deepcopy(resource)
                            break
                    if resource_item:
                        resource_item['issue'] = Constants.default_security_dict[resource_type].get('label')
                        resource_item['alertMessage'] = Constants.default_security_dict[resource_type]. \
                            get('alertMessage')
                        resource_item['priority'] = \
                            Constants.security_severity_label[Constants.default_security_dict[resource_type].
                                get('severity')]
                        resource_list_with_issue.append(resource_item)
        return {'success': True, 'resource_list':
                resource_list_with_issue + get_derived_security_issues(security_issues, timestamp)}

    @staticmethod
    def fix_security_issues(data):
        issue = data['issue']
        result = None
        if issue == Constants.default_security_dict['unusedAccessKeys']['label']:
            iam = IAM()
            result = iam.delete_access_key(data['id'], data['userId'])
        elif issue == Constants.default_security_dict['unusedIAMUsers']['label']:
            iam = IAM()
            result = iam.delete_user(data['name'])
        elif issue == Constants.default_security_dict['passwordPolicy']['label']:
            iam = IAM()
            result = iam.set_password_policy()
        elif issue == Constants.default_security_dict['cloudTrailsNotConfigured']['label']:
            cloud_trail = CloudTrail(data['name'])
            result = cloud_trail.create_cloud_trail(data['name'])
        SecurityIssuesServices.__save_fix_history(data, result['success'], result.get('message'))
        return result

    @staticmethod
    def __save_fix_history(data, success=True, error_message=None):
        account_number = context_helper.get_current_session()['attributes']['accountNumber']
        timestamp = data.get('timestamp') if data.get('timestamp') else data['intentId'].split("_")[1]
        if success:
            intent_data = aws_intent_history.get_by_intent_id(timestamp=timestamp, account_id=account_number)
            for security_issue in intent_data['data']['securityIssues']:
                if intent_data['data']['securityIssues'][security_issue]['label'] == data['issue']:
                    security_issue_dict = None
                    if intent_data['data']['securityIssues'][security_issue].get('count'):
                        security_issue_dict = intent_data['data']['securityIssues'][security_issue]
                        security_issue_dict['itemList'].remove(data['id'])
                        security_issue_dict['count'] -= 1
                        security_issue_dict['fixedItemList'].append(data['id'])
                    else:
                        security_issue_dict = intent_data['data']['securityIssues'][security_issue]
                        security_issue_dict['score'] = 8
                    aws_intent_history.update_metadata(timestamp=timestamp, account_id=account_number,
                                                       metadata=security_issue_dict, intent_type='securityIssues',
                                                       issue_type=security_issue)
                    aws_fix_history.save(account_number,
                                         timestamp=datetime.utcnow().isoformat(), data=data, fix_type='securityIssues')
                    return
        else:
            aws_fix_history.save(context_helper.get_current_session()['attributes']['accountNumber'],
                                 timestamp=datetime.utcnow().isoformat(), success=False,
                                 error_message=error_message, data=data, fix_type='securityIssues')
            return


def get_derived_security_issues(security_issues, timestamp):
    users = None

    def get_all_users():
        nonlocal users
        if users:
            return users
        else:
            users = aws_datapoint_history.get_datapoints_by_type(account_number=context_helper.get_current_session()
            ['attributes']['accountNumber'], timestamp=timestamp, data_type='users')
            return users
    resource_list_with_issue = []
    for resource_type in security_issues:
        if security_issues[resource_type].get('count'):
            if resource_type == 'unusedAccessKeys':
                for user in get_all_users():
                    for access_key in user['accessKeys']:
                        if access_key['id'] in security_issues[resource_type]['itemList']:
                            access_key_local = copy.deepcopy(access_key)
                            access_key_local['type'] = "Access Key"
                            access_key_local['issue'] \
                                = Constants.default_security_dict[resource_type].get('label')
                            access_key_local['alertMessage'] \
                                = Constants.default_security_dict[resource_type].get('alertMessage')
                            access_key_local['userId'] = user['id']
                            access_key_local['timestamp'] = timestamp
                            access_key_local['priority'] = \
                                Constants.security_severity_label[Constants.default_security_dict[resource_type].
                                    get('severity')]
                            resource_list_with_issue.append(access_key_local)
            elif resource_type == 'expiredAccessKeys':
                for user in get_all_users():
                    for access_key in user['accessKeys']:
                        if access_key['id'] in security_issues[resource_type]['itemList']:
                            access_key_local = copy.deepcopy(access_key)
                            access_key_local['type'] = "Access Key"
                            access_key_local['issue'] \
                                = Constants.default_security_dict[resource_type].get('label')
                            access_key_local['userId'] = user['id']
                            access_key_local['alertMessage'] \
                                = Constants.default_security_dict[resource_type].get('alertMessage')
                            access_key_local['timestamp'] = timestamp
                            access_key_local['priority'] = \
                                Constants.security_severity_label[Constants.default_security_dict[resource_type].
                                    get('severity')]
                            resource_list_with_issue.append(access_key_local)
            elif resource_type == 'rootAccountWithoutMFA':
                if security_issues[resource_type].get('count'):
                    root_account_mfa = {'id': 'NA', 'name': 'Root Account',
                                        'issue': Constants.default_security_dict[resource_type].get('label'),
                                        'type': "Root Account Security",
                                        'timestamp': timestamp,
                                        'priority': Constants.security_severity_label
                                        [Constants.default_security_dict[resource_type].get('severity')],
                                        'alertMessage': Constants.default_security_dict[resource_type].get('alertMessage')
                                        }
                    resource_list_with_issue.append(root_account_mfa)
        elif resource_type == 'passwordPolicy':
            if security_issues[resource_type].get('score') < 8:
                password_policy = {'id': 'NA', 'name': 'Password Policy',
                                   'issue': Constants.default_security_dict[resource_type].get('label'),
                                   'type': "Password Policy",
                                   'timestamp': timestamp,
                                   'alertMessage': Constants.default_security_dict[resource_type].get('alertMessage'),
                                   'priority': Constants.security_severity_label
                                        [Constants.default_security_dict[resource_type].get('severity')]}
                resource_list_with_issue.append(password_policy)
    return resource_list_with_issue
