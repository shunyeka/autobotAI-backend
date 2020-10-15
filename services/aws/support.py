from autobot_helpers import boto3_helper, context_helper
from botocore.exceptions import ClientError
import traceback


class Support:

    def __init__(self):
        self.client = boto3_helper.get_client('support')

    def refresh_checks(self):
        try:
            ta_checks = self.client.describe_trusted_advisor_checks(language='en')
            for checks in ta_checks['checks']:
                try:
                    self.client.refresh_trusted_advisor_check(checkId=checks['id'])
                except ClientError as e:
                    print('Cannot refresh check: ' + checks['name'])
                    print("Not able to refresh the trusted adviser check: " + traceback.format_exc() +
                          ": Check name:" +checks['name'])
                    continue
            return {'success': True}
        except BaseException as e:
            err_str = traceback.format_exc()
            context_helper.logger().exception("Some exception occurred while refreshing checks=%s", err_str)
            return {'success': False, 'error_code': 'EXCEPTION', 'message': err_str}

    def generate_report(self):
        try:
            ta_checks = self.client.describe_trusted_advisor_checks(language='en')
            check_summary_list = {}
            for checks in ta_checks['checks']:
                try:
                    check_summary = self.client.describe_trusted_advisor_check_summaries(
                        checkIds=[checks['id']])['summaries'][0]
                    if check_summary['status'] != 'not_available':
                        if checks['category'] not in check_summary_list:
                            check_summary_list[checks['category']] = []
                        check_summary_list[checks['category']].append({
                            'name': checks['name'],
                            'status': check_summary['status'],
                            'resourcesProcessed': str(check_summary['resourcesSummary']['resourcesProcessed']),
                            'resourcesFlagged': str(check_summary['resourcesSummary']['resourcesFlagged']),
                            'resourcesSuppressed': str(check_summary['resourcesSummary']['resourcesSuppressed']),
                            'resourcesIgnored': str(check_summary['resourcesSummary']['resourcesIgnored']),
                        })
                except BaseException as e:
                    print('Failed to get check: ' + checks['id'] + ' --- ' + checks['name'])
                    traceback.print_exc()
                    continue
            for k1, v1 in check_summary_list.items():
                if isinstance(v1, (dict, list)) and len(v1) != 0:
                    for dict_val_v1 in v1:
                        if dict_val_v1['status'] == 'error':
                            v1[v1.index(dict_val_v1)] = (dict_val_v1, 1)

                        elif dict_val_v1['status'] == 'warning':
                            v1[v1.index(dict_val_v1)] = (dict_val_v1, 2)

                        elif dict_val_v1['status'] == 'ok':
                            v1[v1.index(dict_val_v1)] = (dict_val_v1, 3)
                        else:
                            v1[v1.index(dict_val_v1)] = (dict_val_v1, 4)
                v1.sort(key=lambda x: x[1])
            return {'success': True, 'response': check_summary_list}
        except BaseException as e:
            err_str = traceback.format_exc()
            context_helper.logger().exception("Some exception occurred while generating report=%s", err_str)
            if 'SubscriptionRequiredException' in err_str:
                return {'success': False, 'error_code': 'NO_PREMIUM_SUBSCRIPTION',
                        'message': "AWS Premium Support Subscription is required to generate this report."}
            return {'success': False, 'error_code': 'EXCEPTION', 'message': err_str}


