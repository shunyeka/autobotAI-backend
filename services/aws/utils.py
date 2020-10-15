import calendar
import math
from datetime import datetime
from enum import Enum
import re


class Constants:
    autobot_config_rules = ['autobot-autoscaling_group_elb_healthcheck_required', 'autobot-cloud_trail_enabled',
                            'autobot-eip_attached',
                            'autobot-encrypted_volumes', 'autobot-incoming_ssh_disabled', 'autobot-instances_in_vpc',
                            'autobot-rds_storage_encrypted',
                            'autobot-Common-port-security', 'autobot-root_account_mfa_enabled',
                            'autobot-ebs_optimized_instance',
                            'autobot-s3_bucket_versioning_enabled',
                            'autobot-AWS--EC2--InstanceStatusCheckFailed_Instance',
                            'autobot-AWS--RDS--DBClusterCPUUtilization', 'autobot-AWS--EC2--VolumeVolumeQueueLength',
                            'autobot-AWS--EC2--InstanceStatusCheckFailed_System',
                            'autobot-AWS--EC2--InstanceCPUUtilization', 'autobot-AWS--RDS--DBClusterFreeableMemory',
                            'autobot-s3_bucket_public_read_prohibited',
                            'autobot-s3_bucket_public_write_prohibited']

    default_bp_maintenance_dict = {
        'staleSecurityGroups': {
            'count': 0,
            'label': 'Stale Security Groups',
            'severity': 2,
            'itemList': [],
            'fixedItemList': [],
            'canFix': True,
            'alertMessage': 'Are you sure you want to delete this item?'
        },
        'vpcWithoutPrivateSubnet': {
            'count': 0,
            'label': 'VPCs without Private Subnets',
            'severity': 2,
            'itemList': []
        },
        'failingNATGateways': {
            'count': 0,
            'label': 'Failing NAT Gateways',
            'severity': 4,
            'itemList': []
        },
        'vpcWithoutS3Endpoints': {
            'count': 0,
            'label': 'VPCs without S3 Endpoints',
            'severity': 4,
            'itemList': [],
            'fixedItemList': [],
            'canFix': True,
            'alertMessage': 'This will create a new S3 endpoint in the following VPC'
        },
        'classicEC2Instances': {
            'count': 1,
            'label': 'EC2 instances outside VPC',
            'severity': 4,
            'itemList': []
        },
        'ec2WithoutEBSOptimised': {
            'count': 1,
            'label': 'EC2 without EBS Optimized',
            'severity': 2,
            'itemList': [],
            # 'canFix': True,
            # 'alertMessage': 'Are you sure you want to enable EBS optimization for the following instance?'
        },
        'unencryptedVolumes': {
            'count': 1,
            'label': 'Volumes Not Encrypted',
            'severity': 4,
            'itemList': []
        },
        's3BucketsWithoutVersioning': {
            'count': 1,
            'label': 'S3 Buckets without Versioning',
            'severity': 4,
            'itemList': [],
            'fixedItemList': [],
            'canFix': True,
            'alertMessage': 'Are you sure you want to enable versioning for the following bucket?'
        },
        'ipv6VPCWithoutEgressOnlyIGW': {
            'count': 0,
            'label': 'IPv6 VPC without Egress only Internet Gateways',
            'severity': 5,
            'itemList': []
        },
        'ec2NotTerminationProtected': {
            'count': 0,
            'label': 'EC2 Termination Protection Disabled',
            'severity': 1,
            'itemList': [],
            'fixedItemList': [],
            'canFix': True,
            'alertMessage': 'Are you sure you want to enable Termination Protection for the following instance?'
        },
    }

    security_severity_label = {
        1: 'Critical',
        2: 'High',
        3: 'Medium',
        4: 'Low'
    }

    default_security_dict = {
        'usersWithoutMFA': {
            'label': 'Users without MFA',
            'count': 0,
            'severity': 1,
            'itemList': []
        },
        'unusedAccessKeys': {
            'label': 'Unused Keys',
            'severity': 1,
            'count': 0,
            'itemList': [],
            'fixedItemList': [],
            'canFix': True,
            'alertMessage': 'Are you sure you want to delete this Access Key?'
        },
        'unusedIAMUsers': {
            'severity': 1,
            'label': 'Unused IAM Users',
            'count': 0,
            'itemList': [],
        },
        'passwordPolicy': {
            'severity': 1,
            'label': 'Password Strength Policy',
            'score': 0,
            'canFix': True,
            'alertMessage': 'Are you sure you want apply this password policy?'
        },
        'adminUsers': {
            'label': 'Admin IAM Users',
            'severity': 1,
            'count': 0,
            'itemList': []
        },
        'adminRoles': {
            'label': 'Admin IAM Roles',
            'severity': 1,
            'count': 0,
            'itemList': []
        },
        'publicRWS3Buckets': {
            'count': 0,
            'label': 'S3s Public Read/Write Permissions',
            'severity': 1,
            'itemList': []
        },
        'expiredAccessKeys': {
            'severity': 2,
            'label': 'Expired Keys',
            'count': 0,
            'itemList': []
        },
        'insecurePublicPortsSGs': {
            'count': 0,
            'label': 'Security Groups with vulnerable public ports',
            'severity': 2,
            'itemList': []
        },
        'publicSSHAccess': {
            'count': 0,
            'label': 'Security Groups open to world SSH port',
            'severity': 2,
            'itemList': []
        },
        'cloudTrailsNotConfigured': {
            'count': 0,
            'label': 'Regions without CloudTrails',
            'severity': 3,
            'itemList': [],
            'fixedItemList': [],
            'canFix': True,
            'alertMessage': 'Are you sure you want enable CloudTrail for this Region?'
        },
        'rdsDataEncryptionAtRest': {
            'count': 0,
            'label': 'RDSs without Data Encryption',
            'severity': 3,
            'itemList': []
        },
        'publicRDS': {
            'label': 'Admin IAM Users',
            'severity': 3,
            'count': 0,
            'itemList': []
        },
        'rootAccountWithoutMFA': {
            'count': 1,
            'label': 'AWS Root Account without MFA',
            'severity': 3
        },
        'ec2WithoutIAM': {
            'count': 0,
            'label': 'EC2 without IAM Profile',
            'severity': 4,
            'itemList': []
        }
    }

    cost_matrix = {
        'volumes': {
            'io1': {'size': 0.131, 'iops': 0.070},
            'gp2': {'size': 0.114},
            'st1': {'size': 0.051},
            'sc1': {'size': 0.029},
            'standard': {'size': 0.131}
        },
        'eips': 4,
        'vpnGateways': 37.5,
        'elbs': 18.30,
        'albs': 18.30,
        'rdses': {
            'allocatedStorage': 0.095
        }
    }

    datapoint_display_names = {
        'snapshots': 'EBS Snapshot',
        'enis': 'Elastic Network Interface',
        'securityGroups': 'Security Group',
        'amis': 'AMI',
        'ec2s': 'EC2 Instance',
        'routeTables': 'Route Table',
        'internetGateways': 'Internet Gateway',
        'vpnGateways': 'VPN Gateway',
        'elbs': 'ELB',
        'albs': 'Application Load Balancer',
        'targetGroups': 'Target Group',
        'rdses': 'RDS',
        'autoScalingGroups': 'Auto Scaling Group',
        'launchConfigs': 'Launch Config',
        'groups': 'IAM Group',
        'roles': 'IAM Role',
        'users': 'IAM User',
        'cloudTrails': 'Cloud Trail',
        'eips': 'Elastic IP',
        'rdsManualSnapshots': 'RDS Manual Snapshot',
        'volumes': 'EBS Volume',
        'vpcEndpoints': 'VPC Endpoint',
        'vpcs': 'VPC',
        's3Buckets': 'S3 Bucket'
    }
    default_unused_dict = {
        "volumes": {
            'label': "Volume",
            'unused': 0,
            'total': 0,
            'itemList': [],
            'costSaving': 0,
            'fixedItemList': [],
            'canFix': True,
            'alertMessage': 'Are you sure you want delete this volume?'
        }, "eips": {
            'label': "EIP",
            'unused': 0,
            'total': 0,
            'itemList': [],
            'costSaving': 0,
            'fixedItemList': [],
            'canFix': True,
            'alertMessage': 'Are you sure you want release this EIP? You will not be able to get it back once released.'
        }, "vpcs": {
            'label': "VPC",
            'unused': 0,
            'total': 0,
            'itemList': [],
            'costSaving': 0
        }, "snapshots": {
            'label': "Snapshot",
            'unused': 0,
            'total': 0,
            'itemList': [],
            'costSaving': 0,
            'fixedItemList': [],
            'canFix': True,
            'alertMessage': 'Are you sure you want delete this Snapshot?'
        }, "enis": {
            'label': "ENI",
            'unused': 0,
            'total': 0,
            'itemList': [],
            'costSaving': 0,
            'fixedItemList': [],
            'canFix': True,
            'alertMessage': 'Are you sure you want delete this ENI?'
        }, "securityGroups": {
            'label': "Security Group",
            'unused': 0,
            'total': 0,
            'itemList': [],
            'unusedSecurityGroups': [],
            'costSaving': 0,
            'fixedItemList': [],
            'canFix': True,
            'alertMessage': 'Are you sure you want delete this SecurityGroup?'
        }, "amis": {
            'label': "AMI",
            'unused': 0,
            'total': 0,
            'itemList': [],
            'costSaving': 0,
            'fixedItemList': [],
            'canFix': True,
            'alertMessage': 'Are you sure you want de-register this AMI?'
        }, "ec2s": {
            'label': "EC2",
            'unused': 0,
            'total': 0,
            'itemList': [],
            'costSaving': 0,
            # 'fixedItemList': [],
            # 'canFix': True,
            # 'alertMessage': 'Are you sure you want terminate this Instance?'
        }, "routeTables": {
            'label': "Route Table",
            'unused': 0,
            'total': 0,
            'itemList': [],
            'costSaving': 0,
            'fixedItemList': [],
            'canFix': True,
            'alertMessage': 'Are you sure you want delete this RouteTable?'
        }, "internetGateways": {
            'label': "Internet Gateway",
            'unused': 0,
            'total': 0,
            'itemList': [],
            'costSaving': 0,
            'fixedItemList': [],
            'canFix': True,
            'alertMessage': 'Are you sure you want delete this InternetGateway?'
        }, "vpnGateways": {
            'label': "VPN Gateway",
            'unused': 0,
            'total': 0,
            'itemList': [],
            'costSaving': 0,
            'fixedItemList': [],
            'canFix': True,
            'alertMessage': 'Are you sure you want delete this VPN Gateway?'
        }, "elbs": {
            'label': "ELB",
            'unused': 0,
            'total': 0,
            'itemList': [],
            'costSaving': 0,
            'fixedItemList': [],
            'canFix': True,
            'alertMessage': 'Are you sure you want delete this ELB?'
        }, "albs": {
            'label': "ALB",
            'unused': 0,
            'total': 0,
            'itemList': [],
            'costSaving': 0,
            'fixedItemList': [],
            'canFix': True,
            'alertMessage': 'Are you sure you want delete this ALB?'
        }, "targetGroups": {
            'label': "Target Group",
            'unused': 0,
            'total': 0,
            'itemList': [],
            'costSaving': 0,
            # 'fixedItemList': [],
            # 'canFix': True,
            # 'alertMessage': 'Are you sure you want delete this TargetGroup?'
        }, "rdses": {
            'label': "RDS",
            'unused': 0,
            'total': 0,
            'itemList': [],
            'costSaving': 0,
            # 'fixedItemList': [],
            # 'canFix': True,
            # 'alertMessage': 'Are you sure you want terminate this RDS?'
        }, "autoScalingGroups": {
            'label': "Auto Scaling Group",
            'unused': 0,
            'total': 0,
            'itemList': [],
            'costSaving': 0,
            # 'fixedItemList': [],
            # 'canFix': True,
            # 'alertMessage': 'Are you sure you want delete this AutoScaling Group?'
        }, "launchConfigs": {
            'label': "Launch Config",
            'unused': 0,
            'total': 0,
            'itemList': [],
            'costSaving': 0,
            # 'fixedItemList': [],
            # 'canFix': True,
            # 'alertMessage': 'Are you sure you want delete this Launch Config?'

        }
    }

    cw_agent_policy_doc = """
        {
          "Version": "2012-10-17",
          "Statement": [
            {
              "Effect": "Allow",
              "Principal": {
                "Service": "ec2.amazonaws.com"
              },
              "Action": "sts:AssumeRole"
            }
          ]
        }
        """
    cw_agent_policy_arn = "arn:aws:iam::aws:policy/CloudWatchAgentServerPolicy"

    class UserTypes(Enum):
        ROOT = 'ROOT'
        SUB_USER = 'SUBUSER'

    class CSPTypes(Enum):
        AWS = 'aws'
        GCLOUD = 'gcloud'

    class AWSRegions(Enum):
        VIRGINIA = 'us-east-1'
        MUMBAI = 'ap-south-1'
        SINGAPORE = 'ap-southeast-1'
        OHIO = 'us-east-2'
        CALIFORNIA = 'us-west-1'
        OREGON = 'us-west-2'
        CANADA = 'ca-central-1'
        IRELAND = 'eu-west-1'
        FRANKFURT = 'eu-central-1'
        LONDON = 'eu-west-2'
        TOKYO = 'ap-northeast-1'
        SEOUL = 'ap-northeast-2'
        SYDNEY = 'ap-southeast-2'
        PARIS = 'eu-west-3'
        SOUTH_AMERICA = 'sa-east-1'
        CHINA = 'cn-north-1'

    class Intents(Enum):
        ALL_RESOURCES = 'AllResources'

    class Budgets(Enum):
        MONTHLY = 'AIMonthlyBudget'
        ANNUAL = 'AIAnnualBudget'
        QUARTER = 'AIQuarterBudget'

        @classmethod
        def has_value(cls, value):
            return any(value == item.value for item in cls)

    class ContextualCSSClasses(Enum):
        DANGER = 'danger'
        SUCCESS = 'success'
        WARNING = 'warning'


class Helpers:

    @staticmethod
    def month_elapsed():
        today_date = datetime.today()
        month_start_weekday, this_month_end = calendar.monthrange(today_date.year, today_date.month)
        elapse_percent = (today_date.date().day * 100.0) / this_month_end
        return elapse_percent

    @staticmethod
    def year_elapsed():
        today_date = datetime.today()
        year_start = datetime.today().replace(month=1, day=1)
        timedelta = today_date - year_start
        return timedelta.days * 100 / 365

    @staticmethod
    def quarter_elapsed():
        today_date = datetime.today()
        quarter_month = {1: 1, 2: 4, 3: 7, 4: 10}
        quarter = int(math.ceil(today_date.month / 3.))
        q_state_date = datetime.today().replace(year=today_date.year, month=quarter_month[quarter], day=1)
        if quarter == 4:
            q_end_date = datetime.today().replace(year=today_date.year + 1, month=1, day=1)
        else:
            q_end_date = datetime.today().replace(year=today_date.year, month=quarter_month[quarter + 1], day=1)

        noof_days_inq = (q_end_date - q_state_date).days
        current_day = (today_date - q_state_date).days
        return (current_day * 100.0) / noof_days_inq

    @staticmethod
    def parse_snapshot_description(description):
        regex = r"^Created by CreateImage\((.*?)\) for (.*?) "
        matches = re.finditer(regex, description, re.MULTILINE)
        for matchNum, match in enumerate(matches):
            return match.groups()
        return '', ''

    @staticmethod
    def fromisoformat(strdate):
        try:
            return datetime.strptime(strdate, "%Y-%m-%dT%H:%M:%S.%f")
        except:
            return datetime.strptime(strdate, "%Y-%m-%dT%H:%M:%S")

    @staticmethod
    def clean_dict_for_dynamo(data):
        def walk_dict(d):
            for i in d.keys():
                if isinstance(d[i], dict):
                    walk_dict(d[i])
                else:
                    if isinstance(d[i], list):
                        for lvi in range(len(d[i])):
                            if isinstance(d[i][lvi], dict):
                                walk_dict(d[i][lvi])
                            else:
                                if isinstance(d[i][lvi], str) and not d[i][lvi].strip():
                                    print('EmptyValueFor=' + i)
                                    d[i][lvi] = None
                    if isinstance(d[i], str) and not d[i].strip():
                        print('EmptyValueFor='+i)
                        d[i] = None
        walk_dict(data)

    @staticmethod
    def arn(account_id):
        from autobot_helpers import context_helper
        if context_helper.app().config["ENVIRONMENT"] != "live":
            return 'arn:aws:iam::' + account_id + ':role/AutobotAIRoleStaging'
        else:
            return 'arn:aws:iam::' + account_id + ':role/AutobotAIRoleLive'

    @staticmethod
    def env_name():
        from autobot_helpers import context_helper
        if context_helper.app().config["ENVIRONMENT"] != "live":
            return "Staging"
        else:
            return "Live"

    @staticmethod
    def role_from_arn(arn):
        if arn:
            return arn.split("/")[1]
        return "AutobotAIRole"


    @staticmethod
    def parse_snapshot_description(description):
        regex = r"^Created by CreateImage\((.*?)\) for (.*?) "
        matches = re.finditer(regex, description, re.MULTILINE)
        for matchNum, match in enumerate(matches):
            return match.groups()
        return '', ''

    @staticmethod
    def parse_paypal_paydate(date_str):
        from pytz import timezone
        import urllib.parse
        import datetime
        unquoted_date_str = urllib.parse.unquote_plus(date_str)
        paydate_pacific = datetime.datetime.strptime(unquoted_date_str[:-4], "%H:%M:%S %b %d, %Y").replace(
            tzinfo=timezone('US/Pacific'))
        return paydate_pacific.astimezone(timezone('UTC'))

    @staticmethod
    def timestamp():
        return datetime.utcnow().isoformat()

    @staticmethod
    def removekey(d, key):
        r = dict(d)
        del r[key]
        return r


    @staticmethod
    def is_uuid(uuid):
        from uuid import UUID
        try:
            UUID(uuid)
            return True
        except ValueError:
            return False
