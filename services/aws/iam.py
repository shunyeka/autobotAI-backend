from datetime import datetime

from autobot_helpers import boto3_helper, policy_helper, context_helper
from services.aws.utils import Helpers
from models.aws_access_policy_docs import  AwsAccessPolicyDoc
import json
import traceback


class IAM:

    def __init__(self):
        self.client = boto3_helper.get_client('iam')

    def get_user_details(self):
        context_helper.logger().debug("Started")
        results = []
        response = self.client.list_users()
        results.extend(response['Users'])
        while response['IsTruncated']:
            next_token = response['Marker']
            response = self.client.list_users(Marker=next_token)
            results.extend(response['Users'])
            next_token = response['Marker'] if response.get('Marker') else False

        user_virtual_mfa = self.__get_virtual_mfa_details()

        vmfa_enabled_users = []
        for virtual in user_virtual_mfa:
            if 'User' in virtual:
                vmfa_enabled_users.append(virtual['User']['Arn'])

        users_list = []
        for user in results:
            try:
                user_data = {'name': user['UserName'], 'accessKeys': [], 'hasMFAEnabled': True, 'hasAdminAccess': False,
                             'arn': user['Arn'], 'id': user['UserName'], 'policies': []}

                user_policies = self.__get_user_policies(user['UserName'])
                user_data['policies'] = user_policies
                # if user_policies:
                #     for user_policy in user_policies:
                #         if 'AdministratorAccess' in user_policy or 'PowerUserAccess' in user_policy:
                #             user_data['hasAdminAccess'] = True

                user_data['groups'] = self.__get_user_groups(user['UserName'])

                user_data['accessKeys'] = IAM.get_access_key_details(self.client, user['UserName'])

                # last time user logged in
                if 'PasswordLastUsed' in user:
                    user_data['lastLoggedIn'] = (datetime.now(
                    ) - user['PasswordLastUsed'].replace(tzinfo=None)).days

                # Check MFA device Virtual and physical
                user_mfa = self.client.list_mfa_devices(UserName=user['UserName'])
                if not user_mfa['MFADevices']:
                    if user_data['arn'] not in vmfa_enabled_users:
                        user_data['hasMFAEnabled'] = False
                users_list.append(user_data)
            except BaseException as e:
                context_helper.logger().exception("Some exception occurred while getting User=%s, message=%s",
                                                  user['UserId'], e)
            context_helper.logger().debug("Ended")
        return users_list

    def __get_user_groups(self, user_name):
        context_helper.logger().debug("Started for User=%s", user_name)
        results = []
        response = self.client.list_groups_for_user(UserName=user_name)
        results.extend(response['Groups'])
        while response['IsTruncated']:
            next_token = response['Marker']
            response = self.client.list_groups_for_user(UserName=user_name, Marker=next_token)
            results.extend(response['Groups'])
            next_token = response['Marker'] if response.get('Marker') else False
        groups = []
        for group in results:
            groups.append(group['GroupName'])
        context_helper.logger().debug("Ended for User=%s", user_name)
        return groups

    def __get_user_policies(self, user_name):
        context_helper.logger().debug("Started for User=%s", user_name)
        results = []
        response = self.client.list_user_policies(UserName=user_name)
        results.extend(response['PolicyNames'])
        while response['IsTruncated']:
            next_token = response['Marker']
            response = self.client.list_user_policies(UserName=user_name, Marker=next_token)
            results.extend(response['PolicyNames'])
            next_token = response['Marker'] if response.get('Marker') else False
        context_helper.logger().debug("Ended for User=%s", user_name)
        return results

    def get_group_details(self):
        context_helper.logger().debug("Started")
        results = []
        response = self.client.list_groups()
        results.extend(response['Groups'])
        while response['IsTruncated']:
            next_token = response['Marker']
            response = self.client.list_groups(Marker=next_token)
            results.extend(response['Groups'])
            next_token = response['Marker'] if response.get('Marker') else False

        groups = []
        for group in results:
            group_data = {'id': group['GroupId'], 'name': group['GroupName'], 'arn': group['Arn'],
                          'path': group['Path'], 'createdOn': group['CreateDate'].isoformat(),
                          'policies': self.__get_group_policies(group['GroupName'])}
            groups.append(group_data)
        context_helper.logger().debug("Ended")
        return groups

    def __get_group_policies(self, group_name):
        context_helper.logger().debug("Started for Group=%s", group_name)
        results = []
        response = self.client.list_group_policies(GroupName=group_name)
        results.extend(response['PolicyNames'])
        while response['IsTruncated']:
            next_token = response['Marker']
            response = self.client.list_group_policies(GroupName=group_name, Marker=next_token)
            results.extend(response['PolicyNames'])
            next_token = response['Marker'] if response.get('Marker') else False
        context_helper.logger().debug("Ended for Group=%s", group_name)
        return results

    def get_account_summary(self):
        context_helper.logger().debug("Started")
        response = self.client.get_account_summary()
        account_summary = {
            'accessKeysPerUserQuota': response['SummaryMap']['AccessKeysPerUserQuota'],
            "accountAccessKeysPresent": response['SummaryMap']['AccountAccessKeysPresent'],
            "accountMFAEnabled": response['SummaryMap']['AccountMFAEnabled'],
            "accountSigningCertificatesPresent": response['SummaryMap']['AccountSigningCertificatesPresent'],
            "assumeRolePolicySizeQuota": response['SummaryMap']['AssumeRolePolicySizeQuota'],
            "attachedPoliciesPerGroupQuota": response['SummaryMap']['AttachedPoliciesPerGroupQuota'],
            "attachedPoliciesPerRoleQuota": response['SummaryMap']['AttachedPoliciesPerRoleQuota'],
            "attachedPoliciesPerUserQuota": response['SummaryMap']['AttachedPoliciesPerUserQuota'],
            "groupPolicySizeQuota": response['SummaryMap']['GroupPolicySizeQuota'],
            "groups": response['SummaryMap']['Groups'],
            "groupsPerUserQuota": response['SummaryMap']['GroupsPerUserQuota'],
            "groupsQuota": response['SummaryMap']['GroupsQuota'],
            "instanceProfiles": response['SummaryMap']['InstanceProfiles'],
            "instanceProfilesQuota": response['SummaryMap']['InstanceProfilesQuota'],
            "mFADevices": response['SummaryMap']['MFADevices'],
            "mFADevicesInUse": response['SummaryMap']['MFADevicesInUse'],
            "policies": response['SummaryMap']['Policies'],
            "policiesQuota": response['SummaryMap']['PoliciesQuota'],
            "policySizeQuota": response['SummaryMap']['PolicySizeQuota'],
            "policyVersionsInUse": response['SummaryMap']['PolicyVersionsInUse'],
            "policyVersionsInUseQuota": response['SummaryMap']['PolicyVersionsInUseQuota'],
            "providers": response['SummaryMap']['Providers'],
            "rolePolicySizeQuota": response['SummaryMap']['RolePolicySizeQuota'],
            "roles": response['SummaryMap']['Roles'],
            "rolesQuota": response['SummaryMap']['RolesQuota'],
            "serverCertificates": response['SummaryMap']['ServerCertificates'],
            "serverCertificatesQuota": response['SummaryMap']['ServerCertificatesQuota'],
            "signingCertificatesPerUserQuota": response['SummaryMap']['SigningCertificatesPerUserQuota'],
            "userPolicySizeQuota": response['SummaryMap']['UserPolicySizeQuota'],
            "users": response['SummaryMap']['Users'],
            "usersQuota": response['SummaryMap']['UsersQuota'],
            "versionsPerPolicyQuota": response['SummaryMap']['VersionsPerPolicyQuota'],
            'passwordPolicy': self.get_password_policy_score()
        }
        context_helper.logger().debug("Ended")
        return account_summary

    def __get_virtual_mfa_details(self):
        context_helper.logger().debug("Started")
        vmfa_result = []
        response = self.client.list_virtual_mfa_devices()
        vmfa_result.extend(response['VirtualMFADevices'])
        while response['IsTruncated']:
            next_token = response['Marker']
            response = self.client.list_virtual_mfa_devices(Marker=next_token)
            vmfa_result.extend(response['VirtualMFADevices'])
            next_token = response['Marker'] if response.get('Marker') else False
        context_helper.logger().debug("Ended")
        return vmfa_result

    def get_password_policy_score(self):
        context_helper.logger().debug("Started")
        passowrd_policy_score = 0
        try:
            iam_policy = self.client.get_account_password_policy()

            if iam_policy['ExpirePasswords']:
                passowrd_policy_score = passowrd_policy_score + 1

            if iam_policy['MinimumPasswordLength'] >= 8:
                passowrd_policy_score = passowrd_policy_score + 1

            if iam_policy['RequireLowercaseCharacters']:
                passowrd_policy_score = passowrd_policy_score + 1

            if iam_policy['RequireNumbers']:
                passowrd_policy_score = passowrd_policy_score + 1

            if iam_policy['RequireSymbols']:
                passowrd_policy_score = passowrd_policy_score + 1

            if iam_policy['RequireUppercaseCharacters']:
                passowrd_policy_score = passowrd_policy_score + 1

        except Exception as e:
            pass
        context_helper.logger().debug("Ended with score=%s", str(passowrd_policy_score))
        return {'id': 'passwordPolicy', 'name': 'passwordPolicy', 'score': passowrd_policy_score}

    def delete_access_key(self, access_key_id, user_name):
        if not user_name or not access_key_id:
            return {'success': False, 'error_code': 'VALUE_ERROR', 'message': 'AccessKeyId or UserName not provided'}
        try:
            self.client.delete_access_key(
                UserName=user_name,
                AccessKeyId=access_key_id
            )
            return {'success': True}
        except BaseException as e:
            context_helper.logger().exception("Some exception occurred while deleting AccessKey=%s, %s",
                                              access_key_id, e)
            return {'success': False, 'error_code': 'EXCEPTION', 'message': repr(e)}

    def delete_user(self, user_name):
        if not user_name:
            return {'success': False, 'error_code': 'VALUE_ERROR', 'message': 'UserName not provided'}
        try:
            self.client.delete_user(
                UserName=user_name
            )
            return {'success': True}
        except BaseException as e:
            context_helper.logger().exception("Some exception occurred while deleting User=%s, %s",
                                              user_name, e)
            return {'success': False, 'error_code': 'EXCEPTION', 'message': repr(e)}

    def delete_role(self, role_name):
        if not role_name:
            return {'success': False, 'error_code': 'VALUE_ERROR', 'message': 'RoleName not provided'}
        try:
            self.client.delete_role(
                RoleName=role_name
            )
            return {'success': True}
        except BaseException as e:
            context_helper.logger().exception("Some exception occurred while deleting Role=%s, %s",
                                              role_name, e)
            return {'success': False, 'error_code': 'EXCEPTION', 'message': repr(e)}

    def delete_group(self, group_name):
        if not group_name:
            return {'success': False, 'error_code': 'VALUE_ERROR', 'message': 'GroupName not provided'}
        try:
            self.client.delete_group(
                GroupName=group_name
            )
            return {'success': True}
        except BaseException as e:
            context_helper.logger().exception("Some exception occurred while deleting Group=%s, %s",
                                              group_name, e)
            return {'success': False, 'error_code': 'EXCEPTION', 'message': repr(e)}

    def set_password_policy(self):
        try:
            self.client.update_account_password_policy(
                MinimumPasswordLength=8,
                RequireSymbols=True,
                RequireNumbers=True,
                RequireUppercaseCharacters=True,
                RequireLowercaseCharacters=True,
            )
            return {'success': True}
        except BaseException as e:
            context_helper.logger().exception("Some exception occurred while setting PasswordPolicy %s", e)
            return {'success': False, 'error_code': 'EXCEPTION', 'message': repr(e)}

    @staticmethod
    def get_access_key_details(iam_client, userName):
        access_keys = iam_client.list_access_keys(UserName=userName)
        access_key_data_list = []
        for access_key in access_keys['AccessKeyMetadata']:
            if access_key:
                try:
                    access_key_data = {'id': access_key['AccessKeyId'], "lastUsed": None}
                    last_used_data = iam_client.get_access_key_last_used(AccessKeyId=access_key['AccessKeyId'])
                    if 'LastUsedDate' in last_used_data['AccessKeyLastUsed']:
                        access_key_data['lastUsed'] = (
                                    datetime.now() - last_used_data['AccessKeyLastUsed']['LastUsedDate'].replace(
                                tzinfo=None)).days
                    access_key_data['age'] = (datetime.now() - access_key['CreateDate'].replace(tzinfo=None)).days
                    access_key_data['status'] = access_key['Status']
                    access_key_data_list.append(access_key_data)
                except BaseException as e:
                    context_helper.logger().exception("Some exception occurred while getting AccessKey=%s, message=%s",
                                                      access_key['AccessKeyId'], e)
        return access_key_data_list

    def get_role_details(self):
        context_helper.logger().debug("Started")
        results = []
        response = self.client.list_roles()
        results.extend(response['Roles'])
        while response['IsTruncated']:
            next_token = response['Marker']
            response = self.client.list_roles(Marker=next_token)
            results.extend(response['Roles'])
            next_token = response['Marker'] if response.get('Marker') else False

        roles_data = []
        for role in results:
            try:
                role_data = {'name': role['RoleName'], 'id': role['RoleId'], 'arn': role['Arn'],
                             'createdOn': role['CreateDate'].isoformat(),
                             'maxSessionDuration': role['MaxSessionDuration'], 'policies': []}

                if 'Description' in role:
                    role_data['description'] = role['Description']

                role_policies = self.__get_role_policies(role['RoleName'])
                role_data['policies'] = role_policies
                roles_data.append(role_data)
            except BaseException as e:
                context_helper.logger().exception("Some exception occurred while getting Role=%s, message=%s",
                                                  role['RoleId'], e)
        context_helper.logger().debug("Ended")
        return roles_data

    def __get_role_policies(self, role_name):
        context_helper.logger().debug("Started for Role=%s", role_name)
        results = []
        response = self.client.list_attached_role_policies(RoleName=role_name)
        results.extend(response['AttachedPolicies'])
        while response['IsTruncated']:
            next_token = response['Marker']
            response = self.client.list_role_policies(RoleName=role_name, Marker=next_token)
            results.extend(response['AttachedPolicies'])
            next_token = response['Marker'] if response.get('Marker') else False

        final_result = []
        response = self.client.list_role_policies(RoleName=role_name)
        final_result.extend(response['PolicyNames'])
        while response['IsTruncated']:
            next_token = response['Marker']
            response = self.client.list_role_policies(RoleName=role_name, Marker=next_token)
            final_result.extend(response['PolicyNames'])
            next_token = response['Marker'] if response.get('Marker') else False
        context_helper.logger().debug("Ended for Role=%s", role_name)

        for policy in results:
            final_result.append(policy['PolicyName'])

        return final_result

    def __list_all_policies(self):
        context_helper.logger().debug("Started for all")
        results = []
        response = self.client.list_policies(
            Scope='Local',
            OnlyAttached=True,
        )
        results.extend(response['Policies'])
        while response['IsTruncated']:
            next_token = response['Marker']
            response = self.client.list_policies(
                Scope='Local',
                OnlyAttached=True,
                Marker=next_token
            )
            results.extend(response['Policies'])
            next_token = response['Marker'] if response.get('Marker') else False
        context_helper.logger().debug("Ended for all")
        return results

    def attach_policy_to_role(self, role_name, policy_name=None, arn=None):
        if not policy_name and not arn:
            return {'success': False, 'error_code': 'VALUE_ERROR', 'message': 'PolicyName or Arn not provided'}
        try:
            if policy_name:
                self.client.attach_role_policy(RoleName=role_name, PolicyArn=IAM.get_policy_arn(policy_name))
            else:
                self.client.attach_role_policy(RoleName=role_name, PolicyArn=arn)
        except BaseException as e:
            error_stack = traceback.format_exc()
            context_helper.logger().exception("Some exception occurred while attaching policy=%s to Role=%s, message=%s",
                                              policy_name, role_name, error_stack)
            return {'success': False, 'error_code': 'EXCEPTION', 'message': error_stack}

    def create_role(self, name, description, policy_json):
        self.client.create_role(
            RoleName=name,
            Description=description,
            AssumeRolePolicyDocument=policy_json
        )

    def get_pending_autobot_policies(self, full_doc=False):
        active_docs = AwsAccessPolicyDoc.get_active_docs()
        policies = self.__get_role_policies(context_helper.get_current_session()['attributes']['role_name'])
        pending_policies = []

        def check_policy_applied(policy_name):
            for policy in policies:
                if policy_name in policy:
                    return True
            return False

        for active_doc in active_docs:
            active_doc_dict = active_doc
            if not check_policy_applied(active_doc_dict['name']):
                if full_doc:
                    pending_policies.append(active_doc_dict)
                else:
                    pending_policies.append(active_doc_dict['name'])
        return pending_policies

    def create_policy(self, name, json):
        try:
            self.client.create_policy(
                PolicyName=name,
                PolicyDocument=json
            )
            return {'success': True}
        except BaseException as e:
            error_stack = traceback.format_exc()
            context_helper.logger().exception("Some exception occurred while creating policy=%s, message=%s",
                                              name,  error_stack)
            if 'EntityAlreadyExists' in error_stack:
                return {'success': True, 'error_code': 'POLICY_ALREADY_EXIST', 'message': 'Policy Already Exists'}
            return {'success': False, 'error_code': 'EXCEPTION', 'message': error_stack}

    def get_instance_profile_role(self, name):
        instance_profile = self.client.get_instance_profile(
            InstanceProfileName=name
        )
        return instance_profile['InstanceProfile']['Roles'][0]['RoleName'] if instance_profile else None

    def apply_pending_autobot_policies(self):
        pending_policies = self.get_pending_autobot_policies(full_doc=True)
        for policy in pending_policies:
            policy_json = json.loads(policy['json'])
            policy_name = policy['name']+Helpers.env_name()
            response = self.create_policy(policy_name, json.dumps(policy_json["Properties"]["PolicyDocument"]))
            if response['success']:
                self.attach_policy_to_role(context_helper.get_current_session()['attributes']['role_name'], policy_name)

    @staticmethod
    def get_policy_arn(policy_name):
        account_number = context_helper.get_current_session()['attributes']['accountNumber']
        return "arn:aws:iam::"+account_number+":policy/"+policy_name


    @staticmethod
    def get_users_without_mfa(users):
        count = 0
        item_list = []
        for user in users:
            if not user['hasMFAEnabled']:
                count += 1
                item_list.append(user['id'])
        return count, item_list

    @staticmethod
    def get_admin_users(users, groups):
        count = 0
        item_list = []
        for user in users:
            is_user_admin = IAM.__is_policy_admin(user['policies'])
            is_group_admin = False

            def check_group_admin(group_name):
                for group in groups:
                    if group['name'] == group_name:
                        return IAM.__is_policy_admin(group['policies'])

            for group in user['groups']:
                is_group_admin = check_group_admin(group)
                if is_group_admin:
                    break
            if is_group_admin or is_user_admin:
                count += 1
                item_list.append(user['id'])
        return count, item_list

    @staticmethod
    def get_expired_access_keys(users):
        count = 0
        item_list = []
        for user in users:
            for access_key in user['accessKeys']:
                if access_key['age'] > policy_helper.get_policy().max_access_key_age():
                    count += 1
                    item_list.append(access_key['id'])
        return count, item_list

    @staticmethod
    def get_unused_access_keys(users):
        count = 0
        item_list = []
        for user in users:
            for access_key in user['accessKeys']:
                if access_key['lastUsed'] is None or access_key[
                    'lastUsed'] > policy_helper.get_policy().max_unused_access_key_age():
                    count += 1
                    item_list.append(access_key['id'])
        return count, item_list

    @staticmethod
    def get_unused_iam_users(users):
        count = 0
        item_list = []
        for user in users:
            if 'lastLoggedIn' in user and user['lastLoggedIn'] > policy_helper.get_policy().max_unused_iam_users_age():
                count += 1
                item_list.append(user['id'])
        return count, item_list

    @staticmethod
    def get_admin_roles(roles):
        count = 0
        item_list = []
        for role in roles:
            if IAM.__is_policy_admin(role['policies']):
                count += 1
                item_list.append(role['id'])
        return count, item_list


    @staticmethod
    def __is_policy_admin(policies):
        for policy in policies:
            if 'AdministratorAccess' in policy or 'PowerUserAccess' in policy:
                return True
        return False
