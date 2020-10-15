import traceback

from autobot_helpers import context_helper, boto3_helper
from services.aws.ec2 import EC2
from services.aws.utils import Constants


class CloudWatch:

    def __init__(self, region_name=Constants.AWSRegions.VIRGINIA.value):
        self.client = boto3_helper.get_client('cloudwatch', region_name=region_name)
        self.region_name = region_name

    def enable_auto_recovery(self, instance_ids, minutes):
        if not instance_ids:
            return {'success': False, 'error_code': 'EC2_NO_INSTANCE_ID', 'message': 'InstanceID(s) not provided'}
        if not isinstance(instance_ids, list):
            instance_ids = [instance_ids]
        try:
            ec2 = EC2(self.region_name)
            instances = ec2.get_instances_details(instance_ids)
            errors = []
            for instance in instances:
                try:
                    self.client.put_metric_alarm(
                        AlarmName=instance.get('name', instance.get('id'))+'_AutoRecovery',
                        ComparisonOperator='GreaterThanOrEqualToThreshold',
                        EvaluationPeriods=5,
                        MetricName='StatusCheckFailed_System',
                        Namespace='AWS/EC2',
                        Period=300,
                        Statistic='Average',
                        Threshold=1,
                        AlarmActions=[
                            "arn:aws:automate:"+self.region_name+":ec2:recover"
                        ],
                        AlarmDescription='AutoRecovery Alarm for '+instance.get('name', '')+'_'+instance.get('id'),
                        Dimensions=[
                            {
                                'Name': 'InstanceId',
                                'Value': instance['id']
                            },
                        ],
                    )
                except BaseException as e:
                    errors.append({'instanceId': instance['id'], 'error': traceback.format_exc()})
                    context_helper.logger().exception("Some exception occurred while enabling autorecovery for"
                                                      " Instance=%s, %s",
                                                      instance['id'], traceback.format_exc())
            return {'success': True, 'failures': errors}
        except BaseException as e:
            context_helper.logger().exception("Some exception occurred while enabling autorecovery Instances=%s, %s",
                                              ''.join(instance_ids), e)
            return {'success': False, 'error_code': 'EXCEPTION', 'message': traceback.format_exc()}

    def get_alarm(self):
        response = self.client.describe_alarms(
            AlarmNames=[
                'frontline.perf3.trexglobal.com_AutoRecovery',
            ],
        )
        return response
