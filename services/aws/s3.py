from autobot_helpers import context_helper, boto3_helper


class S3:
    public_acl_indicator = 'http://acs.amazonaws.com/groups/global/AllUsers'
    permissions_to_check = ['READ', 'WRITE']

    def __init__(self):
        self.client = boto3_helper.get_client('s3')

    def get_s3_bucket_details(self):
        context_helper.logger().debug("Started")
        response = self.client.list_buckets()
        s3_buckets = []
        for bucket in response['Buckets']:
            try:
                bucket_data = {'id': bucket['Name'], 'name': bucket['Name'],
                               'createdOn': bucket['CreationDate'].isoformat()}
                is_public_read, is_public_write = self.__bucket_permission_details(bucket['Name'])
                bucket_data['isPublicRead'] = is_public_read
                bucket_data['isPublicWrite'] = is_public_write
                bucket_data['isVersioningEnabled'] = self.__bucket_versioning_details(bucket['Name'])
                bucket_data['tags'] = self.__bucket_tags(bucket['Name'])
                s3_buckets.append(bucket_data)
            except BaseException as e:
                context_helper.logger().exception("Some exception occurred while getting S3=%s, %s", bucket['Name'], e)
        context_helper.logger().debug("Ended")
        return s3_buckets

    def __bucket_tags(self, bucket_name):
        try:
            response = self.client.get_bucket_tagging(Bucket=bucket_name)
            return response['TagSet']
        except BaseException as e:
            return None

    def __bucket_versioning_details(self, bucket_name):
        context_helper.logger().debug("Started for Bucket=%s", bucket_name)
        response = self.client.get_bucket_versioning(
            Bucket=bucket_name
        )
        context_helper.logger().debug("Ended for Bucket=%s", bucket_name)
        if 'Status' in response and response['Status'] == 'Enabled':
            return True
        else:
            return False

    def __bucket_permission_details(self, bucket_name):
        context_helper.logger().debug("Started for Bucket=%s", bucket_name)
        bucket_acl_response = self.client.get_bucket_acl(Bucket=bucket_name)
        is_public_read = False
        is_public_write = False
        for grant in bucket_acl_response['Grants']:
            for (k, v) in grant.items():
                if k == 'Permission' and any(permission in v for permission in self.permissions_to_check):
                    for (grantee_attrib_k, grantee_attrib_v) in grant['Grantee'].items():
                        if 'URI' in grantee_attrib_k and grant['Grantee']['URI'] == self.public_acl_indicator:
                            if v == "READ":
                                is_public_read = True
                            else:
                                is_public_write = True
        context_helper.logger().debug("Ended for Bucket=%s", bucket_name)
        return is_public_read, is_public_write

    def enable_versioning(self, bucket_name):
        if not bucket_name:
            return {'success': False, 'error_code': 'EC2_INVALID_ARGS', 'message': 'BucketName not provided'}
        try:
            self.client.put_bucket_versioning(
                Bucket=bucket_name,
                VersioningConfiguration={
                    'Status': 'Enabled'
                }
            )
            return {'success': True}
        except BaseException as e:
            context_helper.logger().exception("Some exception occurred while enabling versioning for BUCKET=%s, %s",
                                              bucket_name, e)
            return {'success': False, 'error_code': 'EXCEPTION', 'message': repr(e)}

    def create_bucket(self, bucket_name):
        if not bucket_name:
            return {'success': False, 'error_code': 'VALUE_ERROR', 'message': 'Bucket Name not provided'}
        try:
            self.client.create_bucket(
                Bucket=bucket_name,
            )
            return {'success': True}
        except BaseException as e:
            context_helper.logger().exception("Some exception occurred while creating S3 Bucket=%s, %s",
                                              bucket_name, e)
            return {'success': False, 'error_code': 'EXCEPTION', 'message': repr(e)}


    @staticmethod
    def get_public_rw_buckets(buckets):
        count = 0
        item_list = []
        for bucket in buckets:
            if bucket['isPublicRead'] or bucket['isPublicWrite']:
                count += 1
                item_list.append(bucket['id'])
        return count, item_list

    @staticmethod
    def filter_buckets_wo_versioning(buckets):
        count = 0
        item_list = []
        for bucket in buckets:
            if not bucket['isVersioningEnabled']:
                count += 1
                item_list.append(bucket['id'])
        return count, item_list
