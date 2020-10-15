import traceback

from botocore.exceptions import ClientError

from autobot_helpers import boto3_helper, context_helper
from services.aws.utils import Constants


class SSM:
    CW_DISK_MEM_LINUX_PARAM_STORE_DOC = """
        {
        "metrics": {
            "append_dimensions": {
                "AutoScalingGroupName": "${aws:AutoScalingGroupName}",
                "ImageId": "${aws:ImageId}",
                "InstanceId": "${aws:InstanceId}",
                "InstanceType": "${aws:InstanceType}"
            },
            "metrics_collected": {			
                "disk": {
                    "measurement": [
                        "used_percent",
                        "inodes_free"
                    ],
                    "metrics_collection_interval": 60,
                    "resources": [
                        "*"
                    ]
                },
                "diskio": {
                    "measurement": [
                        "io_time"
                    ],
                    "metrics_collection_interval": 60,
                    "resources": [
                        "*"
                    ]
                },
                "mem": {
                    "measurement": [
                        "mem_used_percent"
                    ],
                    "metrics_collection_interval": 60
                },
                "swap": {
                    "measurement": [
                        "swap_used_percent"
                    ],
                    "metrics_collection_interval": 60
                }
            }
        }
    }"""

    CW_DISK_MEM_WINDOWS_PARAM_STORE_DOC = """
    {
        "metrics": {
            "append_dimensions": {
                "AutoScalingGroupName": "${aws:AutoScalingGroupName}",
                "ImageId": "${aws:ImageId}",
                "InstanceId": "${aws:InstanceId}",
                "InstanceType": "${aws:InstanceType}"
            },
            "metrics_collected": {
                "LogicalDisk": {
                    "measurement": [
                        "% Free Space"
                    ],
                    "metrics_collection_interval": 60,
                    "resources": [
                        "*"
                    ]
                },
                "Memory": {
                    "measurement": [
                        "% Committed Bytes In Use"
                    ],
                    "metrics_collection_interval": 60
                },
                "Paging File": {
                    "measurement": [
                        "% Usage"
                    ],
                    "metrics_collection_interval": 60,
                    "resources": [
                        "*"
                    ]
                },
                "PhysicalDisk": {
                    "measurement": [
                        "% Disk Time"
                    ],
                    "metrics_collection_interval": 60,
                    "resources": [
                        "*"
                    ]
                }
            }
        }
    }"""


    def __init__(self, region_name=Constants.AWSRegions.VIRGINIA.value):
        self.client = boto3_helper.get_client('ssm', region_name=region_name)
        self.region_name = region_name

    def run_command(self, instance_ids, doc_name, params, plugin_name=None):
        ssm_response = self.client.send_command(InstanceIds=instance_ids,
                                                DocumentName=doc_name,
                                                Parameters=params)
        cmd_id = ssm_response['Command']['CommandId']
        instances_cmd_status = []
        import time
        time.sleep(10)

        def get_cmd_status(cmd_id, instance_id, plugin_name):
            if plugin_name:
                return self.client.get_command_invocation(
                    CommandId=cmd_id,
                    InstanceId=instance_id,
                    PluginName=plugin_name
                )
            else:
                return self.client.get_command_invocation(
                    CommandId=cmd_id,
                    InstanceId=instance_id
                )

        for instance_id in instance_ids:
            ssm_cmd_status = get_cmd_status(cmd_id, instance_id, plugin_name)
            while ssm_cmd_status['Status'] in ['Pending', 'InProgress', 'Delayed', 'Cancelling']:
                ssm_cmd_status = get_cmd_status(cmd_id, instance_id, plugin_name)
            instances_cmd_status.append({'instanceId': instance_id, 'status': ssm_cmd_status['Status'],
                                         'statusDetails': ssm_cmd_status['StatusDetails']})
        return instances_cmd_status

    def setup_cw_agent(self, instance_ids, config_location):
        try:
            if not isinstance(instance_ids, list):
                instance_ids = [instance_ids]
            instances_cmd_status_agent_install = self.run_command(instance_ids, doc_name="AWS-ConfigureAWSPackage",
                                                                  params={'action': ['Install'],
                                                                          "name": ["AmazonCloudWatchAgent"]})
            instances_cmd_status_agent_config = self.run_command(instance_ids, doc_name="AmazonCloudWatch-ManageAgent",
                                                                 params={"action": ["configure"],
                                                                         "mode": ["ec2"],
                                                                         "optionalConfigurationSource": ["ssm"],
                                                                         "optionalRestart": ["yes"],
                                                                         "optionalConfigurationLocation": [
                                                                             config_location]},
                                                                 plugin_name="ControlCloudWatchAgentLinux")
            return {'success': True, 'installStatus': instances_cmd_status_agent_install,
                    'configStatus': instances_cmd_status_agent_config}
        except BaseException as e:
            err_str = traceback.format_exc()
            context_helper.logger().exception("Some exception occurred while setting up cw agent=%s", err_str)
            return {'success': False, 'error_code': 'EXCEPTION', 'message': err_str}

    def upload_to_param_store(self, name, doc):
        try:
            self.client.put_parameter(
                Name=name,
                Value=doc,
                Type='String',
            )
            return {'success': True}
        except ClientError as e:
            if 'ParameterAlreadyExists' in str(e):
                return {'success': True}
        except BaseException as e:
            err_str = traceback.format_exc()
            context_helper.logger().exception("Some exception occurred while adding param to store=%s", err_str)
            return {'success': False, 'error_code': 'EXCEPTION', 'message': err_str}

    def get_instances(self):
        results = []
        response = self.client.describe_instance_information()
        results.extend(response['InstanceInformationList'])
        while 'NextToken' in response:
            next_token = response['NextToken']
            response = self.client.describe_instance_information(NextToken=next_token)
            results.extend(response['InstanceInformationList'])
            next_token = response['NextToken'] if response.get('NextToken') else False
        return results


def refresh_checks(self):
    try:
        ta_checks = self.client.describe_trusted_advisor_checks(language='en')
        for checks in ta_checks['checks']:
            try:
                self.client.refresh_trusted_advisor_check(checkId=checks['id'])
            except ClientError as e:
                print('Cannot refresh check: ' + checks['name'])
                print("Not able to refresh the trusted adviser check: " + traceback.format_exc() +
                      ": Check name:" + checks['name'])
                continue
        return {'success': True}
    except BaseException as e:
        err_str = traceback.format_exc()
        context_helper.logger().exception("Some exception occurred while refreshing checks=%s", err_str)
        return {'success': False, 'error_code': 'EXCEPTION', 'message': err_str}


def generate_report(self):
    try:
        ta_checks = self.client.describe_trusted_advisor_checks(language='en')
        checks_list = {ctgs: [] for ctgs in list(set([checks['category'] for checks in ta_checks['checks']]))}
        check_summary_list = []
        for checks in ta_checks['checks']:
            try:
                check_summary = self.client.describe_trusted_advisor_check_summaries(
                    checkIds=[checks['id']])['summaries'][0]
                check_summary_list.append(check_summary)
                if check_summary['status'] != 'not_available':
                    checks_list[checks['category']].append(
                        [checks['name'], check_summary['status'],
                         str(check_summary['resourcesSummary']['resourcesProcessed']),
                         str(check_summary['resourcesSummary']['resourcesFlagged']),
                         str(check_summary['resourcesSummary']['resourcesSuppressed']),
                         str(check_summary['resourcesSummary']['resourcesIgnored'])])
            except BaseException as e:
                print('Failed to get check: ' + checks['id'] + ' --- ' + checks['name'])
                traceback.print_exc()
                continue
        return {'success': True, 'response': check_summary_list}
    except BaseException as e:
        err_str = traceback.format_exc()
        context_helper.logger().exception("Some exception occurred while generating report=%s", err_str)
        return {'success': False, 'error_code': 'EXCEPTION', 'message': err_str}
