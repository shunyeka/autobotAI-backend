from autobot_helpers import context_helper, boto3_helper, policy_helper
from services.aws.utils import Constants
from services.aws.s3 import S3
import random
import string
from datetime import datetime
import dateutil.parser


class CloudTrail:

    def __init__(self, region_name=Constants.AWSRegions.VIRGINIA.value):
        self.client = boto3_helper.get_client('cloudtrail', region_name=region_name)
        self.region_name = region_name

    def get_cloud_trail_details(self):
        response = self.client.describe_trails()
        trail_list = []
        for trail in response['trailList']:
            try:
                trail_data = {'id': trail['Name']+'_'+self.region_name, 'name': trail['Name'], 'arn': trail['TrailARN']}
                trail_list.append(trail_data)
            except BaseException as e:
                context_helper.logger().exception("Some exception occurred while getting CloudTrail=%s, %s",
                                                  trail['Name'], e)
        return trail_list

    def create_cloud_trail(self, region_name):
        if not region_name:
            return {'success': False, 'error_code': 'VALUE_ERROR', 'message': 'Region not provided'}

        trail_random = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
        trail_bucket_name = 'autobotAI_trail_'+region_name+'_'+trail_random
        trail_name = 'autobotAI_trail_' + region_name + '_' + trail_random

        s3 = S3()
        result = s3.create_bucket(trail_bucket_name)
        if not result['success']:
            return result
        try:
            self.client.create_trail(
                Name=trail_name,
                S3BucketName=trail_bucket_name,
                IncludeGlobalServiceEvents=True,
                IsMultiRegionTrail=False
            )
            return {'success': True}
        except BaseException as e:
            context_helper.logger().exception("Some exception occurred while creating CloudTrail for Region=%s, %s",
                                              region_name, repr(e))
            return {'success': False, 'error_code': 'EXCEPTION', 'message': repr(e)}
