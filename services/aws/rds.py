from datetime import datetime
from autobot_helpers import boto3_helper, policy_helper, context_helper
from services.aws.utils import Constants
from flask import current_app as app


class RDS:

    def __init__(self, region_name=Constants.AWSRegions.VIRGINIA.value):
        self.client = boto3_helper.get_client('rds', region_name)

    def get_rds_details(self):
        '''
        {
            "id": "autobottest",
            "isEncrypted": false,
            "isPublic": true,
            "name": "autobottest"
          }
        :return:
        '''

        results = []
        response = self.client.describe_db_instances()
        results.extend(response['DBInstances'])
        while 'Marker' in response:
            next_token = response['Marker']
            response = self.client.describe_db_instances(Marker=next_token)
            results.extend(response['DBInstances'])
            next_token = response['Marker'] if response.get('Marker') else False
        rds_list = []
        for db_instance in results:
            try:
                rds_data = {'id': db_instance['DBInstanceIdentifier'],
                            'name': db_instance['DBInstanceIdentifier'], 'isPublic': db_instance['PubliclyAccessible']}
                try:
                    rds_data['name'] = db_instance['DBName']
                except KeyError as e:
                    pass
                rds_list.append(rds_data)
                if 'StorageEncrypted' in db_instance:
                    rds_data["isEncrypted"] = db_instance['StorageEncrypted']
            except BaseException as e:
                context_helper.logger().exception("Some exception occurred while getting RDS=%s, %s", db_instance['DBInstanceIdentifier'], e)
        return rds_list

    def get_rds_manual_snapshot_details(self):
        '''
        {
            "arn": "arn:aws:rds:us-east-1:643293017610:snapshot:autobottest",
            "id": "autobottest",
            "rdsId": "autobottest"
          }
        :return:
        '''
        results = []
        response = self.client.describe_db_snapshots(SnapshotType='manual')
        results.extend(response['DBSnapshots'])
        while 'Marker' in response:
            next_token = response['Marker']
            response = self.client.describe_db_snapshots(SnapshotType='manual', Marker=next_token)
            results.extend(response['DBSnapshots'])
            next_token = response['Marker'] if response.get('Marker') else False
        rds_snapshots = []
        for rds_ss in results:
            try:
                rds_snapshot = {'id': rds_ss['DBSnapshotIdentifier'], 'rdsId': rds_ss['DBInstanceIdentifier'],
                                'arn': rds_ss['DBSnapshotArn']}
                if 'SnapshotCreateTime' in rds_ss:
                    rds_snapshot['age'] = (datetime.now() - rds_ss['SnapshotCreateTime'].replace(tzinfo=None)).days
                if 'AllocatedStorage' in rds_ss:
                    rds_snapshot['allocatedStorage'] = rds_ss['AllocatedStorage']
                rds_snapshots.append(rds_snapshot)
            except BaseException as e:
                context_helper.logger().exception("Some exception occurred while getting RDSSnapshot=%s, %s", rds_ss['DBSnapshotIdentifier'], e)
        return rds_snapshots

    def delete_rds_snapshot(self, snapshot_id):
        if not snapshot_id:
            return {'success': False, 'error_code': 'VALUE_ERROR', 'message': 'SnapShotID not provided'}
        try:
            self.client.delete_db_snapshot(
                DBSnapshotIdentifier=snapshot_id
            )
            return {'success': True}
        except BaseException as e:
            context_helper.logger().exception("Some exception occurred while deleting RDSSnapshot=%s, %s",
                                              snapshot_id, e)
            return {'success': False, 'error_code': 'EXCEPTION', 'message': repr(e)}

    @staticmethod
    def __calculate_rds_ss_cost(rds_ss):
        cost = 0
        for costItem in Constants.cost_matrix['rdses']:
            cost = rds_ss[costItem] * Constants.cost_matrix['rdses'][costItem]
        return cost

    @staticmethod
    def get_unused_rds_snapshots(rds_snapshots):
        unused_count = 0
        unused_list = []
        cost = 0
        for rds_snapshot in rds_snapshots:
            if 'age' in rds_snapshot and rds_snapshot['age'] > policy_helper.get_policy().max_rds_snapshot_age():
                unused_count += 1
                unused_list.append(rds_snapshot['id'])
                cost += RDS.__calculate_rds_ss_cost(rds_snapshot)
        return unused_count, unused_list, cost

    @staticmethod
    def get_public_rds(rdses):
        count = 0
        item_list = []
        for rds in rdses:
            if rds['isPublic']:
                count += 1
                item_list.append(rds['id'])
        return count, item_list

    @staticmethod
    def get_rds_without_encryption(rdses):
        count = 0
        item_list = []
        for rds in rdses:
            if not 'isEncrypted' in rds or not rds['isEncrypted']:
                count += 1
                item_list.append(rds['id'])
        return count, item_list
