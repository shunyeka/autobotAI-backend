from autobot_helpers import context_helper, boto3_helper
from services.aws.utils import Constants


class AutoScaling:

    def __init__(self, region_name=Constants.AWSRegions.VIRGINIA.value):
        context_helper.logger().debug("Instance created for region=%s", region_name)
        self.client = boto3_helper.get_client('autoscaling', region_name=region_name)

    # TODO: Pagination pending
    def get_launchconfig_details(self):
        response = self.client.describe_launch_configurations()
        launch_configurations = []
        for launch_config in response['LaunchConfigurations']:
            try:
                launch_configuration = {'id': launch_config['LaunchConfigurationName'],
                                        'name': launch_config['LaunchConfigurationName'],
                                        'arn': launch_config['LaunchConfigurationARN']
                                        }
                launch_configurations.append(launch_configuration)
            except BaseException as e:
                context_helper.logger().exception("Some exception occurred while getting LaunchConfig=%s", launch_config['LaunchConfigurationName'])
        return launch_configurations

    # TODO: Pagination pending
    def get_autoscaling_group_details(self):
        response = self.client.describe_auto_scaling_groups()
        autoscaling_groups = []
        for as_group in response['AutoScalingGroups']:
            try:
                autoscaling_group = {'id': as_group['AutoScalingGroupName'], 'name': as_group['AutoScalingGroupName'],
                                     'arn': as_group['AutoScalingGroupARN'], 'instances': [],
                                     'createdOn': as_group['CreatedTime'].isoformat()}
                if 'Status' in as_group:
                    autoscaling_group['status'] = as_group['Status']
                if 'LaunchConfigurationName' in as_group:
                    autoscaling_group['launchConfigName'] = as_group['LaunchConfigurationName']
                if 'LaunchTemplate' in as_group:
                    autoscaling_group['launchTemplateId'] = as_group['LaunchTemplate']['LaunchTemplateId']
                    autoscaling_group['launchTemplateName'] = as_group['LaunchTemplate']['LaunchTemplateName']
                if 'AvailabilityZones' in as_group:
                    autoscaling_group['availabilityZones'] = as_group['AvailabilityZones']
                if 'LoadBalancerNames' in as_group:
                    autoscaling_group['loadBalancerNames'] = as_group['LoadBalancerNames']
                if 'TargetGroupARNs' in as_group:
                    autoscaling_group['targetGroupARNs'] = as_group['TargetGroupARNs']
                if 'Tags' in as_group:
                    autoscaling_group['tags'] = as_group['Tags']
                if 'DesiredCapacity' in as_group:
                    autoscaling_group['desiredCapacity'] = as_group['DesiredCapacity']
                for instance in as_group['Instances']:
                    autoscaling_group['instances'].append(
                        {'id': instance['InstanceId'],
                         'launchConfigName': instance['LaunchConfigurationName']
                         if instance.get('LaunchConfigurationName') else None})
                autoscaling_groups.append(autoscaling_group)
            except:
                context_helper.logger().error("Some exception occurred while getting AutoScalingGroup=%s",
                                 autoscaling_group['AutoScalingGroupName'])
                pass
        return autoscaling_groups

    def delete_launchconfig(self, launch_config_name):
        if not launch_config_name:
            return {'success': False, 'error_code': 'AS_NO_LAUNCHCONFIG', 'message': 'Launch config name not provided'}
        try:
            self.client.delete_launch_configuration(LaunchConfigurationName=launch_config_name)
            return {'success': True}
        except BaseException as e:
            context_helper.logger().exception("Some exception occurred while deleting LaunchConfig=%s, %s",
                                                              launch_config_name, repr(e))
            return {'success': False, 'error_code': 'AS_DELETE_FAILED', 'message': repr(e)}

    def delete_autoscaling_group(self, as_group_name):
        if not as_group_name:
            return {'success': False, 'error_code': 'AS_NO_ASGROUP', 'message': 'AutoScaling group name not provided'}
        try:
            self.client.delete_auto_scaling_group(
                AutoScalingGroupName=as_group_name,
                ForceDelete=False
            )
            return {'success': True}
        except BaseException as e:
            context_helper.logger().exception("Some exception occurred while deleting AutoScalingGroup=%s, %s",
                                                              as_group_name, repr(e))
            return {'success': False, 'error_code': 'AS_DELETE_FAILED', 'message': repr(e)}


    @staticmethod
    def get_unused_lanuchconfigs(launch_configs, autoscaling_groups):
        unused_count = 0
        unused_list = []
        for launch_config in launch_configs:
            is_used = False
            for autoscaling_group in autoscaling_groups:
                if autoscaling_group.get('launchConfigName') == launch_config['name']:
                    is_used = True
            if not is_used:
                unused_count += 1
                unused_list.append(launch_config['id'])
        return unused_count, unused_list

    @staticmethod
    def get_unused_autoscaling_groups(autoscaling_groups):
        unused_count = 0
        unused_list = []
        for autoscaling_group in autoscaling_groups:
            if 'desiredCapacity' not in autoscaling_group or autoscaling_group['desiredCapacity'] == 0:
                unused_count += 1
                unused_list.append(autoscaling_group['id'])
        return unused_count, unused_list
