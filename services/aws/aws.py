from autobot_helpers import context_helper, boto3_helper
from models import aws_intent_history, aws_datapoint_history
from services.aws.utils import Constants
from models import cloud_service_provider
from services.aws.iam import IAM
from services.aws.ec2 import EC2
from services.aws.ssm import SSM
import traceback


class AWS:
    answer = ["check the security compliance", "check unused resources", "cleanup unused resources", "Check the bill",
              "Check the status of my yearly budget",
              "check s three storage utilisation", "check number of running development instances",
              "check the status of my quarterly budget",
              "verify cloudwatch alarm configuration", "check the elastic block storage utilisation",
              "configure auto recovery", "update monthly budget to $5000"]

    def __init__(self):
        pass

    @staticmethod
    def get_dashboard_data(account_id):
        last_intent_history = aws_intent_history.get_latest_by_account_id(account_id)
        if not last_intent_history:
            return {'success': False, 'error': "Data not found", 'error_code': 'AWS_DATA_NOT_FOUND'}
        return {'success': True, 'data': last_intent_history['data'], 'timestamp': last_intent_history['timestamp']}

    @staticmethod
    def get_regional_preference_details(user_id, account_id):
        csp = cloud_service_provider.get_by_account_id(user_id, account_id)
        return {
            'allRegions': boto3_helper.regions,
            'defaultRegion': boto3_helper.get_region_details_by_name(csp.get('defaultRegion')),
            'activeRegions': boto3_helper.get_regions_details_by_names(csp.get('activeRegions'))
        }

    @staticmethod
    def save_region_preference(account_id, data):
        cloud_service_provider.update_region_preference(context_helper.get_current_session()['attributes']['rootUserId'], account_id,
                                                        data['defaultRegion'], data['activeRegions'])
        return {'success': True}

    @staticmethod
    def refresh_access_policy_for_current_account():
        iam = IAM()
        iam.apply_pending_autobot_policies()
        context_helper.refresh_sts_creds(context_helper.get_current_session())

    @staticmethod
    def setup_cw_agent(instance_ids, region):
        param_doc_name_linux = "AmazonCloudWatch-autobotAI-linux"
        if not instance_ids or not region:
            return {'success': False, 'error': "Instance IDs are region name is required", 'error_code': 'AWS_REQUIRED_MISSING'}
        ec2 = EC2(region_name=region)
        instances = ec2.get_instances_details(instance_ids=instance_ids)
        if not instances:
            return {'success': False, 'error': "No instances found", 'error_code': 'AWS_INSTANCES_NOT_FOUND'}
        iam = IAM()
        ssm = SSM(region_name=region)
        param_status_response = ssm.upload_to_param_store(param_doc_name_linux,
                                                          SSM.CW_DISK_MEM_LINUX_PARAM_STORE_DOC)
        if not param_status_response['success']:
            return param_status_response
        eligible_instances = []
        for instance in instances:
            if instance["iamProfileId"]:
                eligible_instances.append(instance['id'])
                role_name = iam.get_instance_profile_role(instance["iamProfileId"]['Arn'].split("instance-profile/")[1])
                try:
                    iam.attach_policy_to_role(role_name=role_name, arn=Constants.cw_agent_policy_arn)
                    ec2.set_instance_tags(instance['id'], [{'Key': 'cw_agent_enabled', 'Value': "true"}])
                except BaseException as e:
                    print("Some exception occurred while attaching CWAgent policy to role", traceback.format_exc())
        response = ssm.setup_cw_agent(instance_ids=eligible_instances, config_location=param_doc_name_linux)
        return response

    @staticmethod
    def get_ssm_instances(account_id):
        intent_history = aws_intent_history.get_latest_by_account_id(account_id)
        instances = aws_datapoint_history.get_datapoints_by_type(account_id, intent_history['timestamp'], "ec2s")
        region_ssm_instances = {}

        def is_ssm_managed(region, instance_id):
            if not region_ssm_instances.get(region):
                region_ssm_instances[region] = SSM(region_name=region).get_instances()
            if next((instance for instance in region_ssm_instances[region] if instance["InstanceId"] == instance_id), None):
                return True
            return False
        ssm_instances = []
        for instance in instances:
            if not next((tag for tag in instance['tags'] if tag["Key"] == "cw_agent_enabled" and tag["Value"]), None) \
                    and is_ssm_managed(instance['region'], instance['id']):
                ssm_instances.append(instance)
        return ssm_instances
