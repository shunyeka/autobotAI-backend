import copy

from services.aws.ec2 import EC2
from services.aws.iam import IAM
from services.aws.rds import RDS
from services.aws.s3 import S3
from services.aws.utils import Constants


class SecurityAnalyser:

    def __init__(self):
        pass

    @staticmethod
    def analyse_data_for_security(dataset):
        insecure_resources = copy.deepcopy(Constants.default_security_dict)
        SecurityAnalyser.__analyse_global_data_for_security(dataset['globalData'], insecure_resources)
        for region in dataset['regionalData']:
            for datapoint in dataset['regionalData'][region]['datapoints']:
                if dataset['regionalData'][region]['datapoints'][datapoint] or datapoint == 'cloudTrails':

                    if datapoint == 'rdses':
                        count, item_list = RDS.get_public_rds(dataset['regionalData'][region]['datapoints'][datapoint])
                        insecure_resources['publicRDS']['count'] += count
                        insecure_resources['publicRDS']['itemList'].extend(item_list)

                        count, item_list = RDS.get_rds_without_encryption(dataset['regionalData'][region]['datapoints'][datapoint])
                        insecure_resources['rdsDataEncryptionAtRest']['count'] += count
                        insecure_resources['rdsDataEncryptionAtRest']['itemList'].extend(item_list)
                    elif datapoint == 'ec2s':
                        count, item_list = EC2.get_ec2_without_iams(dataset['regionalData'][region]['datapoints'][datapoint])
                        insecure_resources['ec2WithoutIAM']['count'] += count
                        insecure_resources['ec2WithoutIAM']['itemList'].extend(item_list)
                    elif datapoint == 'securityGroups':
                        count, item_list = EC2.get_security_groups_with_insecure_open_ports(
                            dataset['regionalData'][region]['datapoints'][datapoint])
                        insecure_resources['insecurePublicPortsSGs']['count'] += count
                        insecure_resources['insecurePublicPortsSGs']['itemList'].extend(item_list)

                        count, item_list = EC2.get_security_groups_with_open_ssh_port(
                            dataset['regionalData'][region]['datapoints'][datapoint])
                        insecure_resources['publicSSHAccess']['count'] += count
                        insecure_resources['publicSSHAccess']['itemList'].extend(item_list)
                    elif datapoint == 'cloudTrails':
                        if not dataset['regionalData'][region]['datapoints'][datapoint]:
                            insecure_resources['cloudTrailsNotConfigured']['count'] += 1
                            insecure_resources['cloudTrailsNotConfigured']['itemList'].append(region)
        return insecure_resources

    @staticmethod
    def __analyse_global_data_for_security(global_data, insecure_resources):
        if global_data['datapoints'].get('users'):
            count, item_list = IAM.get_users_without_mfa(global_data['datapoints']['users'])
            insecure_resources['usersWithoutMFA']['count'] += count
            insecure_resources['usersWithoutMFA']['itemList'].extend(item_list)

            count, item_list = IAM.get_admin_users(global_data['datapoints']['users'], global_data['datapoints']['groups'])
            insecure_resources['adminUsers']['count'] += count
            insecure_resources['adminUsers']['itemList'].extend(item_list)

            count, item_list = IAM.get_unused_access_keys(global_data['datapoints']['users'])
            insecure_resources['unusedAccessKeys']['count'] += count
            insecure_resources['unusedAccessKeys']['itemList'].extend(item_list)

            count, item_list = IAM.get_expired_access_keys(global_data['datapoints']['users'])
            insecure_resources['expiredAccessKeys']['count'] += count
            insecure_resources['expiredAccessKeys']['itemList'].extend(item_list)

            count, item_list = IAM.get_unused_iam_users(global_data['datapoints']['users'])
            insecure_resources['unusedIAMUsers']['count'] += count
            insecure_resources['unusedIAMUsers']['itemList'].extend(item_list)

        if global_data['datapoints'].get('accountSummary'):
            if global_data['datapoints']['accountSummary']['accountMFAEnabled']:
                insecure_resources['rootAccountWithoutMFA']['count'] = 0

        if global_data['datapoints'].get('roles'):
            count, item_list = IAM.get_admin_roles(global_data['datapoints']['roles'])
            insecure_resources['adminRoles']['count'] += count
            insecure_resources['adminRoles']['itemList'].extend(item_list)

        if global_data['datapoints'].get('s3Buckets'):
            count, item_list = S3.get_public_rw_buckets(global_data['datapoints']['s3Buckets'])
            insecure_resources['publicRWS3Buckets']['count'] += count
            insecure_resources['publicRWS3Buckets']['itemList'].extend(item_list)

        if global_data['datapoints'].get('passwordPolicy'):
            insecure_resources['passwordPolicy']['score'] = global_data['datapoints']['passwordPolicy']['score']
