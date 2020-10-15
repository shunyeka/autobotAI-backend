from autobot_helpers import context_helper
from models import aws_datapoint_history, aws_intent_history, aws_fix_history
from services.aws.utils import Constants
from services.aws.ec2 import EC2
from services.aws.s3 import S3
from datetime import datetime
import copy


class MaintenanceTasksService:

    @staticmethod
    def get_maintenance_tasks(maintenance_resources, account_id, timestamp):
        if not maintenance_resources:
            return {'success': False, 'error_code': 'UNR_EMPTY_RESOURCE_LIST', 'error': "Resource list is empty"}

        resource_ids = []
        for resource_type in maintenance_resources:
            if maintenance_resources[resource_type].get('count'):
                for resource_id in maintenance_resources[resource_type]['itemList']:
                    resource_ids.append(resource_id)
        resource_ids = list(set(resource_ids))

        resource_list = aws_datapoint_history.get_datapoints_by_ids(
            account_number=account_id,
            timestamp=timestamp,
            resource_ids=resource_ids)
        resource_list_with_issue = []
        for resource_type in maintenance_resources:
            if maintenance_resources[resource_type].get('count'):
                for resource_id in maintenance_resources[resource_type]['itemList']:
                    resource_item = None
                    for resource in resource_list:
                        if resource['id'] == resource_id:
                            resource_item = copy.deepcopy(resource)
                            break
                    if resource_item:
                        resource_item['issue'] = Constants.default_bp_maintenance_dict[resource_type].get('label')
                        resource_item['alertMessage'] = Constants.default_bp_maintenance_dict[resource_type].\
                            get('alertMessage')
                        resource_list_with_issue.append(resource_item)
        return {'success': True, 'resource_list': resource_list_with_issue}

    @staticmethod
    def fix_maintenance_task(data):
        issue = data['issue']
        result = None
        if issue == Constants.default_bp_maintenance_dict['staleSecurityGroups']['label']:
            ec2 = EC2(region_name=data['region'])
            result = ec2.delete_security_group(data['id'])
        elif issue == Constants.default_bp_maintenance_dict['vpcWithoutS3Endpoints']['label']:
            ec2 = EC2(region_name=data['region'])
            result = ec2.create_s3_endpoint(vpc_id=data['id'], region_id=data['region'])
        elif issue == Constants.default_bp_maintenance_dict['s3BucketsWithoutVersioning']['label']:
            s3 = S3()
            result = s3.enable_versioning(bucket_name=data['name'])
        elif issue == Constants.default_bp_maintenance_dict['ec2NotTerminationProtected']['label']:
            ec2 = EC2(region_name=data['region'])
            result = ec2.enable_termination_protection(instance_id=data['id'])
        # elif issue == Constants.default_bp_maintenance_dict['ec2WithoutEBSOptimised']['label']:
        #     ec2 = EC2(region_name=data['region'])
        #     result = ec2.enable_ebs_optimise(instance_id=data['id'])
        MaintenanceTasksService.__save_fix_history(data, result['success'], result.get('message'))
        return result

    @staticmethod
    def __save_fix_history(data, success=True, error_message=None):
        account_number = context_helper.get_current_session()['attributes']['accountNumber']
        timestamp = data['intentId'].split("_")[1]
        if success:
            intent_data = aws_intent_history.get_by_intent_id(timestamp=timestamp, account_id=account_number)
            for maintenance_issue in intent_data['data']['maintenance']:
                if intent_data['data']['maintenance'][maintenance_issue]['label'] == data['issue']:
                    maintenance_issue_dict = intent_data['data']['maintenance'][maintenance_issue]
                    maintenance_issue_dict['itemList'].remove(data['id'])
                    maintenance_issue_dict['count'] -= 1
                    maintenance_issue_dict['fixedItemList'].append(data['id'])
                    aws_intent_history.update_metadata(timestamp=timestamp, account_id=account_number,
                                                       metadata=maintenance_issue_dict, intent_type='maintenance',
                                                       issue_type=maintenance_issue)
                    aws_fix_history.save(account_number,
                                         timestamp=datetime.utcnow().isoformat(), data=data, fix_type='maintenance')
                    return
        else:
            aws_fix_history.save(context_helper.get_current_session()['attributes']['accountNumber'],
                                 timestamp=datetime.utcnow().isoformat(), success=False,
                                 error_message=error_message, data=data, fix_type='maintenance')
            return



