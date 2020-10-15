class Policy:

    def __init__(self):
        self.policy = [{
                "isEnabled": True,
                "auditCheckName": "amiAge",
                "label": "Unused AMI",
                "auditCheckAttributes": {
                    "age": 45
                },
                "auditCheckId": 1
            },
            {
                "isEnabled": True,
                "auditCheckName": "instanceStoppedAge",
                "label": "Unused EC2 Instances",
                "auditCheckAttributes": {
                    "age": 14
                },
                "auditCheckId": 2
            },
            {
                "isEnabled": True,
                "auditCheckName": "rdsSnapshotAge",
                "label": "Unused EC2 Instances",
                "auditCheckAttributes": {
                    "age": 45
                },
                "auditCheckId": 3
            },
            {
                "isEnabled": True,
                "auditCheckName": "vulnerableOpenPorts",
                "label": "Common Vulnerable Open Ports",
                "auditCheckAttributes": {
                    "ports": [21, 1433, 3306, 23, 3389]
                },
                "auditCheckId": 4
            },
            {
                "isEnabled": True,
                "auditCheckName": "unusedAccessKeysAge",
                "label": "Unused Access Keys",
                "auditCheckAttributes": {
                    "age": 100
                },
                "auditCheckId": 5
            },
            {
                "isEnabled": True,
                "auditCheckName": "accessKeyRotationAge",
                "label": "Access key max age, Rotation required",
                "auditCheckAttributes": {
                    "age": 180
                },
                "auditCheckId": 5
            },
            {
                "isEnabled": True,
                "auditCheckName": "unusedIAMUsers",
                "label": "Unused IAM Users",
                "auditCheckAttributes": {
                    "age": 30
                },
                "auditCheckId": 5
            }
        ]

    def max_unused_iam_users_age(self):
        for audit in self.policy:
            if audit['auditCheckName'] == 'unusedIAMUsers':
                return audit['auditCheckAttributes']['age']

    def max_unused_access_key_age(self):
        for audit in self.policy:
            if audit['auditCheckName'] == 'unusedAccessKeysAge':
                return audit['auditCheckAttributes']['age']

    def max_access_key_age(self):
        for audit in self.policy:
            if audit['auditCheckName'] == 'accessKeyRotationAge':
                return audit['auditCheckAttributes']['age']

    def max_ami_age(self):
        for audit in self.policy:
            if audit['auditCheckName'] == 'amiAge':
                return audit['auditCheckAttributes']['age']

    def max_stopped_instance_age(self):
        for audit in self.policy:
            if audit['auditCheckName'] == 'instanceStoppedAge':
                return audit['auditCheckAttributes']['age']

    def max_rds_snapshot_age(self):
        for audit in self.policy:
            if audit['auditCheckName'] == 'rdsSnapshotAge':
                return audit['auditCheckAttributes']['age']

    def common_vulnerable_open_ports(self):
        for audit in self.policy:
            if audit['auditCheckName'] == 'vulnerableOpenPorts':
                return audit['auditCheckAttributes']['ports']