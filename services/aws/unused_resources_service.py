import copy
from datetime import datetime

from autobot_helpers import context_helper
from models import aws_datapoint_history
from models import aws_fix_history
from models import aws_intent_history
from services.aws.ec2 import EC2
from services.aws.elb import ELB
from services.aws.utils import Constants


class UnusedResourcesServices:

    @staticmethod
    def get_unused_resources(unused_resources, account_id, timestamp):
        if not unused_resources:
            return {'success': False, 'error_code': 'UNR_EMPTY_RESOURCE_LIST', 'error': "Resource list is empty"}
        resource_ids = []
        for resource_type in unused_resources:
            if unused_resources[resource_type]['unused']:
                for resource_id in unused_resources[resource_type]['itemList']:
                    resource_ids.append(resource_id)

        unused_resources_list = aws_datapoint_history.get_datapoints_by_ids(
            account_number=account_id,
            timestamp=timestamp, resource_ids=resource_ids)

        unused_resources_list_with_issue = []
        for resource_type in unused_resources:
            if unused_resources[resource_type].get('unused'):
                for resource_id in unused_resources[resource_type]['itemList']:
                    resource_item = None
                    for resource in unused_resources_list:
                        if resource['itemId'] == resource_type+"_"+resource_id:
                            resource_item = copy.deepcopy(resource)
                            break
                    if resource_item:
                        resource_item['issue'] = Constants.default_unused_dict[resource_type].get('label')
                        resource_item['alertMessage'] = Constants.default_unused_dict[resource_type]. \
                            get('alertMessage')
                        unused_resources_list_with_issue.append(resource_item)
        return {'success': True, 'resource_list': unused_resources_list_with_issue}

    @staticmethod
    def clean_unused_resource(data):
        issue = data['issue']
        result = None
        if issue == Constants.default_unused_dict['volumes']['label']:
            ec2 = EC2(data['region'])
            result = ec2.delete_volume(data['id'])
        elif issue == Constants.default_unused_dict['eips']['label']:
            ec2 = EC2(data['region'])
            result = ec2.delete_eip(data['ip'], data.get('allocationId'))
        elif issue == Constants.default_unused_dict['snapshots']['label']:
            ec2 = EC2(data['region'])
            result = ec2.delete_snapshot(data['id'])
        elif issue == Constants.default_unused_dict['enis']['label']:
            ec2 = EC2(data['region'])
            result = ec2.delete_eni(data['id'])
        elif issue == Constants.default_unused_dict['securityGroups']['label']:
            ec2 = EC2(data['region'])
            result = ec2.delete_security_group(data['id'])
        elif issue == Constants.default_unused_dict['amis']['label']:
            ec2 = EC2(data['region'])
            result = ec2.delete_ami(data['id'])
            for snapshot_id in data.get('snapshots'):
                ec2.delete_snapshot(snapshot_id)
        elif issue == Constants.default_unused_dict['ec2s']['label']:
            ec2 = EC2(data['region'])
            result = ec2.terminate_instances(data['id'])
        elif issue == Constants.default_unused_dict['routeTables']['label']:
            ec2 = EC2(data['region'])
            result = ec2.delete_route_table(data['id'])
        elif issue == Constants.default_unused_dict['internetGateways']['label']:
            ec2 = EC2(data['region'])
            result = ec2.delete_internet_gateway(data['id'])
        elif issue == Constants.default_unused_dict['vpnGateways']['label']:
            ec2 = EC2(data['region'])
            result = ec2.delete_vpn_gateway(data['id'])
        elif issue == Constants.default_unused_dict['elbs']['label']:
            elb = ELB(data['region'])
            result = elb.delete_elb(data['id'])
        elif issue == Constants.default_unused_dict['albs']['label']:
            elb = ELB(data['region'])
            result = elb.delete_alb(data['arn'])
        UnusedResourcesServices.__save_fix_history(data, result['success'], result.get('message'))
        return result

    @staticmethod
    def __save_fix_history(data, success=True, error_message=None):
        account_number = context_helper.get_current_session()['attributes']['accountNumber']
        timestamp = data['intentId'].split("_")[1]
        if success:
            intent_data = aws_intent_history.get_by_intent_id(timestamp=timestamp, account_id=account_number)
            for unused_resource_type in intent_data['data']['unusedResources']:
                if intent_data['data']['unusedResources'][unused_resource_type]['label'] == data['issue']:
                    unused_resource_dict = intent_data['data']['unusedResources'][unused_resource_type]
                    unused_resource_dict['itemList'].remove(data['id'])
                    unused_resource_dict['unused'] -= 1
                    unused_resource_dict['fixedItemList'].append(data['id'])
                    aws_intent_history.update_metadata(timestamp=timestamp, account_id=account_number,
                                                       metadata=unused_resource_dict, intent_type='unusedResources',
                                                       issue_type=unused_resource_type)
                    aws_fix_history.save(account_number,
                                         timestamp=datetime.utcnow().isoformat(), data=data, fix_type='unusedResources')
                    return
        else:
            aws_fix_history.save(context_helper.get_current_session()['attributes']['accountNumber'],
                                 timestamp=datetime.utcnow().isoformat(), success=False,
                                 error_message=error_message, data=data, fix_type='unusedResources')
            return
