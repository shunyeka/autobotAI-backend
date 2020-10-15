import copy

from services.aws.ec2 import EC2
from services.aws.s3 import S3
from services.aws.utils import Constants


class MaintenanceAnalyser:

    def __init__(self):
        pass

    @staticmethod
    def analyse_data(dataset):
        maintenance_issues = copy.deepcopy(Constants.default_bp_maintenance_dict)
        MaintenanceAnalyser.__analyse_global_data(dataset['globalData'], maintenance_issues)
        for region in dataset['regionalData']:
            for datapoint in dataset['regionalData'][region]['datapoints']:
                if dataset['regionalData'][region]['datapoints'][datapoint] is not None and dataset['regionalData'][region]['datapoints'][datapoint]:

                    if datapoint == 'ec2s':
                        count, item_list = EC2.get_ec2s_without_TP(dataset['regionalData'][region]['datapoints'][datapoint])
                        maintenance_issues['ec2NotTerminationProtected']['count'] += count
                        maintenance_issues['ec2NotTerminationProtected']['itemList'].extend(item_list)

                        count, item_list = EC2.get_classic_ec2s(dataset['regionalData'][region]['datapoints'][datapoint])
                        maintenance_issues['classicEC2Instances']['count'] += count
                        maintenance_issues['classicEC2Instances']['itemList'].extend(item_list)

                        count, item_list = EC2.filter_ec2s_wo_ebs_optimised(dataset['regionalData'][region]['datapoints'][datapoint])
                        maintenance_issues['ec2WithoutEBSOptimised']['count'] += count
                        maintenance_issues['ec2WithoutEBSOptimised']['itemList'].extend(item_list)

                    elif datapoint == 'volumes':
                        count, item_list = EC2.filter_volumes_unencrypted(dataset['regionalData'][region]['datapoints'][datapoint])
                        maintenance_issues['unencryptedVolumes']['count'] += count
                        maintenance_issues['unencryptedVolumes']['itemList'].extend(item_list)

                    elif datapoint == 'vpcs':
                        count, item_list = EC2.get_stale_sec_groups(dataset['regionalData'][region]['datapoints']['vpcs'])
                        maintenance_issues['staleSecurityGroups']['count'] += count
                        maintenance_issues['staleSecurityGroups']['itemList'].extend(item_list)

                        count, item_list = EC2.get_failing_nat_gateways(dataset['regionalData'][region]['datapoints']['vpcs'])
                        maintenance_issues['failingNATGateways']['count'] += count
                        maintenance_issues['failingNATGateways']['itemList'].extend(item_list)

                        count, item_list = EC2.get_vpcs_without_s3_endpoints(dataset['regionalData'][region]['datapoints']['vpcs'], dataset['regionalData'][region]['datapoints']['vpcEndpoints'])
                        maintenance_issues['vpcWithoutS3Endpoints']['count'] += count
                        maintenance_issues['vpcWithoutS3Endpoints']['itemList'].extend(item_list)

                        count, item_list = EC2.get_ipv6_vpc_wo_egress_igw(dataset['regionalData'][region]['datapoints']['vpcs'])
                        maintenance_issues['ipv6VPCWithoutEgressOnlyIGW']['count'] += count
                        maintenance_issues['ipv6VPCWithoutEgressOnlyIGW']['itemList'].extend(item_list)

                        count, item_list = EC2.get_vpc_wo_private_subnet(dataset['regionalData'][region]['datapoints']['vpcs'])
                        maintenance_issues['vpcWithoutPrivateSubnet']['count'] += count
                        maintenance_issues['vpcWithoutPrivateSubnet']['itemList'].extend(item_list)
        return maintenance_issues

    @staticmethod
    def __analyse_global_data(global_data, insecure_resources):

        if global_data['datapoints'].get('s3Buckets'):
            count, item_list = S3.filter_buckets_wo_versioning(global_data['datapoints']['s3Buckets'])
            insecure_resources['s3BucketsWithoutVersioning']['count'] += count
            insecure_resources['s3BucketsWithoutVersioning']['itemList'].extend(item_list)

