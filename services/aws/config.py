from services.aws.utils import Constants
from autobot_helpers import boto3_helper, context_helper


class Config:

    def __init__(self, region_name=Constants.AWSRegions.VIRGINIA):
        self.client = boto3_helper.get_client(region_name=region_name)

    def get_config_details(self):
        config_recorders = self.client.describe_configuration_recorders()

        config_details = {'recorderExists': False, 'unencryptedVolumes': [], 'unencryptedRds': [], 'sshDisabled': [],
                          'recorderMissingRule': [], 's3BucketVersioningDisabled': [], 'rootAccountMFADisabled': [],
                          'vpcCloudTrailDisabled': [], 'ec2InstancesNotInVPC': [], 'commonPortInSecure': [],
                          'ebsNotOptimised': [], 's3BucketsPublicRead': [], 's3BucketsPublicWrite': []}
        if len(config_recorders['ConfigurationRecorders']) == 0:
            config_details['recorderExists'] = False

        for autobot_config_rule in Constants.autobot_config_rules:
            try:
                response = self.client.get_compliance_details_by_config_rule(
                    ConfigRuleName=autobot_config_rule,
                    ComplianceTypes=['NON_COMPLIANT'],
                    Limit=100
                )

                for evalresult in response['EvaluationResults']:

                    if evalresult['EvaluationResultIdentifier']['EvaluationResultQualifier']['ConfigRuleName'] \
                            == 'autobot-encrypted_volumes':
                        config_details['unencryptedVolumes'].append(
                            evalresult['EvaluationResultIdentifier']['EvaluationResultQualifier']['ResourceId'])
                    elif evalresult['EvaluationResultIdentifier']['EvaluationResultQualifier'][
                            'ConfigRuleName'] == 'autobot-incoming_ssh_disabled':
                        config_details['sshDisabled'].append(
                            evalresult['EvaluationResultIdentifier']['EvaluationResultQualifier']['ResourceId'])
                    elif evalresult['EvaluationResultIdentifier']['EvaluationResultQualifier'][
                            'ConfigRuleName'] == 'autobot-rds_storage_encrypted':
                        config_details['unencryptedRds'].append(
                            evalresult['EvaluationResultIdentifier']['EvaluationResultQualifier']['ResourceId'])
                    elif evalresult['EvaluationResultIdentifier']['EvaluationResultQualifier'][
                            'ConfigRuleName'] == 'autobot-s3_bucket_versioning_enabled':
                        config_details['s3BucketVersioningDisabled'].append(
                            evalresult['EvaluationResultIdentifier']['EvaluationResultQualifier']['ResourceId'])
                    elif evalresult['EvaluationResultIdentifier']['EvaluationResultQualifier'][
                            'ConfigRuleName'] == 'autobot-root_account_mfa_enabled':
                        config_details['rootAccountMFADisabled'].append(
                            evalresult['EvaluationResultIdentifier']['EvaluationResultQualifier']['ResourceId'])
                    elif evalresult['EvaluationResultIdentifier']['EvaluationResultQualifier'][
                            'ConfigRuleName'] == 'autobot-cloud_trail_enabled':
                        config_details['vpcCloudTrailDisabled'].append(
                            evalresult['EvaluationResultIdentifier']['EvaluationResultQualifier']['ResourceId'])
                    elif evalresult['EvaluationResultIdentifier']['EvaluationResultQualifier'][
                            'ConfigRuleName'] == 'autobot-instances_in_vpc':
                        config_details['ec2InstancesNotInVPC'].append(
                            evalresult['EvaluationResultIdentifier']['EvaluationResultQualifier']['ResourceId'])
                    elif evalresult['EvaluationResultIdentifier']['EvaluationResultQualifier'][
                            'ConfigRuleName'] == 'autobot-Common-port-security':
                        config_details['commonPortInSecure'].append(
                            evalresult['EvaluationResultIdentifier']['EvaluationResultQualifier']['ResourceId'])
                    elif evalresult['EvaluationResultIdentifier']['EvaluationResultQualifier'][
                            'ConfigRuleName'] == 'autobot-ebs_optimized_instance':
                        config_details['ebsNotOptimised'].append(
                            evalresult['EvaluationResultIdentifier']['EvaluationResultQualifier']['ResourceId'])
                    elif evalresult['EvaluationResultIdentifier']['EvaluationResultQualifier'][
                            'ConfigRuleName'] == 'autobot-s3_bucket_public_read_prohibited':
                        config_details['s3BucketsPublicRead'].append(
                            evalresult['EvaluationResultIdentifier']['EvaluationResultQualifier']['ResourceId'])
                    elif evalresult['EvaluationResultIdentifier']['EvaluationResultQualifier'][
                            'ConfigRuleName'] == 'autobot-s3_bucket_public_write_prohibited':
                        config_details['s3BucketsPublicWrite'].append(
                            evalresult['EvaluationResultIdentifier']['EvaluationResultQualifier']['ResourceId'])
                    else:
                        pass
            except BaseException as e:
                context_helper.logger().exception("Some exception occurred while getting AutobotConfigRule=%s, %s", autobot_config_rule,
                                 e)
        return config_details
