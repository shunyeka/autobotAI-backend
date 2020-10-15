from autobot_helpers import context_helper, boto3_helper
from datetime import datetime
from services.aws.utils import Constants

class ELB:

    def __init__(self, region_name=Constants.AWSRegions.VIRGINIA.value):
        self.client_v1 = boto3_helper.get_client('elb', region_name=region_name)
        self.client_v2 = boto3_helper.get_client('elbv2', region_name=region_name)

    def get_elb_details(self):
        results = []
        response = self.client_v1.describe_load_balancers()
        results.extend(response['LoadBalancerDescriptions'])
        while 'NextMarker' in response:
            next_token = response['NextMarker']
            response = self.client_v1.describe_load_balancers(Marker=next_token)
            results.extend(response['LoadBalancerDescriptions'])
            next_token = response['NextMarker'] if response.get('NextMarker') else False

        clbs = []
        for elb in results:
            try:
                elb_detail = {'id': elb['LoadBalancerName'], 'name': elb['LoadBalancerName'],
                              'createdOn': elb['CreatedTime'].isoformat(), 'version': 'v1'}

                if 'VPCId' in elb:
                    elb_detail['vpcId'] = elb['VPCId']
                    elb_detail['subnets'] = elb['Subnets']
                    elb_detail['availabilityZones'] = elb['AvailabilityZones']
                if 'Instances' in elb:
                    elb_detail['instances'] = elb['Instances']
                if 'SecurityGroups' in elb:
                    elb_detail['securityGroups'] = elb['SecurityGroups']
                clbs.append(elb_detail)
            except BaseException as e:
                context_helper.logger().exception("Some exception occurred while getting ClassicELB=%s, %s", elb['LoadBalancerName'], e)
        return clbs if clbs else None

    def __get_listener_detail_for_elb(self, elb_arn):
        response = self.client_v2.describe_listeners(LoadBalancerArn=elb_arn)
        listeners = []
        for listener in response['Listeners']:
            try:
                listener_detail = {'arn': listener['ListenerArn'], 'port': listener['Port'],
                                   'protocol': listener['Protocol'], 'targetGroups': []}
                for target_group in listener['DefaultActions']:
                    listener_detail['targetGroups'].append({'arn': target_group['TargetGroupArn']})
                listeners.append(listener_detail)
            except BaseException as e:
                context_helper.logger().exception("Some exception occurred while getting ELBListener=%s, %s", listener['ListenerArn'], e)
        return listeners

    def get_alb_details(self):
        results = []
        response = self.client_v2.describe_load_balancers()
        results.extend(response['LoadBalancers'])
        while 'NextMarker' in response:
            next_token = response['NextMarker']
            response = self.client_v2.describe_load_balancers(Marker=next_token)
            results.extend(response['LoadBalancers'])
            next_token = response['NextMarker'] if response.get('NextMarker') else False
        albs = []
        for elb in response['LoadBalancers']:
            try:
                elb_detail = {'id': elb['LoadBalancerName'], 'name': elb['LoadBalancerName'],
                              'createdOn': elb['CreatedTime'].isoformat(), 'arn': elb['LoadBalancerArn'],
                              'state': elb['State'], 'type': elb['Type'], 'version': 'v2'}

                if 'VpcId' in elb:
                    elb_detail['vpcId'] = elb['VpcId']
                    elb_detail['availabilityZones'] = elb['AvailabilityZones']
                if 'Instances' in elb:
                    elb_detail['instances'] = elb['Instances']
                if 'SecurityGroups' in elb:
                    elb_detail['securityGroups'] = elb['SecurityGroups']
                elb_detail['listeners'] = self.__get_listener_detail_for_elb(elb['LoadBalancerArn'])
                albs.append(elb_detail)
            except BaseException as e:
                context_helper.logger().exception("Some exception occurred while getting ELB=%s, %s", elb['LoadBalancerName'], e)
        return albs if albs else None

    def get_target_groups_details(self):
        response = self.client_v2.describe_target_groups()
        target_groups = []
        for target_group in response['TargetGroups']:
            try:
                target_group_detail = {'id': target_group['TargetGroupName'], 'name': target_group['TargetGroupName'],
                                       'vpcId': target_group['VpcId'], 'arn': target_group['TargetGroupArn'],
                                       'loadBalancerArns': target_group['LoadBalancerArns'], 'instanceHealth': [],
                                       'protocol': target_group['Protocol'], 'port': target_group['Port']}
                target_group_healths = self.client_v2.describe_target_health(TargetGroupArn=target_group['TargetGroupArn'])
                for target_group_health in target_group_healths['TargetHealthDescriptions']:
                    tg_health_detail = {'instanceId': target_group_health['Target']['Id'],
                                        'port': target_group_health['Target']['Port'],
                                        'state': target_group_health['TargetHealth']['State']}
                    if 'AvailabilityZone' in target_group_health['Target']:
                        tg_health_detail['availabilityZone'] = target_group_health['Target']['AvailabilityZone']
                    target_group_detail['instanceHealth'].append(tg_health_detail)
                target_groups.append(target_group_detail)
            except BaseException as e:
                context_helper.logger().exception("Some exception occurred while getting TargetGroup=%s, %s", target_group['TargetGroupName'], e)
        return target_groups

    def delete_elb(self, elb_name):
        if not elb_name:
            return {'success': False, 'error_code': 'VALUE_ERROR', 'message': 'ELBName not provided'}
        try:
            self.client_v1.delete_load_balancer(
                LoadBalancerName=elb_name
            )
            return {'success': True}
        except BaseException as e:
            context_helper.logger().exception("Some exception occurred while deleting ELB=%s, %s",
                                              elb_name, e)
            return {'success': False, 'error_code': 'EXCEPTION', 'message': repr(e)}

    def delete_alb(self, alb_arn):
        if not alb_arn:
            return {'success': False, 'error_code': 'VALUE_ERROR', 'message': 'ALBArn not provided'}
        try:
            self.client_v2.delete_load_balancer(
                LoadBalancerArn=alb_arn
            )
            return {'success': True}
        except BaseException as e:
            context_helper.logger().exception("Some exception occurred while deleting ALB=%s, %s",
                                              alb_arn, e)
            return {'success': False, 'error_code': 'EXCEPTION', 'message': repr(e)}

    @staticmethod
    def get_unused_elb_count(elbs):
        unused_count = 0
        unused_list = []
        cost = 0
        for elb in elbs:
            if len(elb['instances']) == 0:
                unused_count += 1
                unused_list.append(elb['id'])
                cost += Constants.cost_matrix['elbs']
        return unused_count, unused_list, cost


    @staticmethod
    def get_unused_alb_count(albs, target_groups):
        unused_count = 0
        unused_list = []
        cost = 0
        for alb in albs:
            unused_tg_count = 0
            total_listeners = len(alb['listeners'])
            if alb['listeners']:
                for listener in alb['listeners']:
                    for target_group in listener['targetGroups']:
                        for tg_group in target_groups:
                            if target_group['arn'] == tg_group['arn'] and not tg_group['instanceHealth']:
                                unused_tg_count = unused_tg_count + 1
                                if unused_tg_count >= total_listeners:
                                    unused_count += 1
                                    unused_list.append(alb['id'])
                                    cost += Constants.cost_matrix['albs']
            else:
                unused_count += 1
                unused_list.append(alb['id'])
                cost += Constants.cost_matrix['albs']
        return unused_count, unused_list, cost

