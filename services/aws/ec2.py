from datetime import datetime

import dateutil.parser
from botocore.exceptions import ClientError
from autobot_helpers import context_helper, boto3_helper, policy_helper
from services.aws.utils import Constants, Helpers



class EC2:

    def __init__(self, region_name=Constants.AWSRegions.VIRGINIA.value):
        self.client = boto3_helper.get_client('ec2', region_name=region_name)
        self.autoscaling_client = boto3_helper.get_client('autoscaling', region_name=region_name)
        self.region_name = region_name

    def get_instances_details(self, instance_ids=None):
        results = []
        filters = []
        if instance_ids:
            if not isinstance(instance_ids, list):
                instance_ids = [instance_ids]
            filters = [{'Name': 'instance-id', 'Values': instance_ids}]
        response = self.client.describe_instances(Filters=filters)
        results.extend(response['Reservations'])
        while 'NextToken' in response:
            next_token = response['NextToken']
            response = self.client.describe_instances(NextToken=next_token)
            results.extend(response['Reservations'])
            next_token = response['NextToken'] if response.get('NextToken') else False

        autoscaling_instances = self.autoscaling_client.describe_auto_scaling_instances()
        instance_data_list = []

        for reservation in results:
            for instance in reservation['Instances']:
                try:
                    instance_data = {'id': instance['InstanceId'], 'isTerminationProtected': False,
                                     'launchedOn': instance['LaunchTime'].isoformat(),
                                     'state': instance['State']['Name'],
                                     'isEbsOptimized': instance['EbsOptimized'],
                                     'securityGroups': [], 'region': self.region_name}
                    if 'StateTransitionReason' in instance and instance['StateTransitionReason']:
                        state_trans_reason = instance['StateTransitionReason']
                        instance_data['isLastStateChangeUserInitiated'] = \
                            True if "User initiated" in state_trans_reason else False
                        if "(" in state_trans_reason:
                            date_string = state_trans_reason[
                                          state_trans_reason.find("(") + 1:state_trans_reason.find(")")]
                            instance_data['lastStateChangedOn'] = \
                                datetime.strptime(date_string, "%Y-%m-%d %H:%M:%S %Z").isoformat()
                    if 'PrivateIpAddress' in instance:
                        instance_data['privateIp'] = instance['PrivateIpAddress']
                    if 'VpcId' in instance:
                        instance_data['vpcId'] = instance['VpcId']
                        instance_data['subnetId'] = instance['SubnetId']
                    if 'Tags' in instance:
                        instance_data['tags'] = instance['Tags']
                        for tag in instance_data['tags']:
                            if tag['Key'].lower() == 'name':
                                instance_data['name'] = tag['Value']
                    for security_group in instance['SecurityGroups']:
                        instance_data['securityGroups'].append({'id': security_group['GroupId'],
                                                                'name': security_group['GroupName']})
                    if "StateReason" in instance:
                        if instance['StateReason'].get('Code') and instance['StateReason'].get('Message'):
                            instance_data['reasonForLastStateChange'] = {'code': instance['StateReason'].get('Code'),
                                                                         'message': instance['StateReason'].get(
                                                                             'Message')}
                    if 'IamInstanceProfile' in instance:
                        instance_data['iamProfileId'] = instance['IamInstanceProfile']
                    ec2_protection = self.client.describe_instance_attribute(Attribute='disableApiTermination',
                                                                             InstanceId=instance['InstanceId'])
                    if ec2_protection['DisableApiTermination']['Value']:
                        instance_autoscaling = next((asg_instance for asg_instance in
                                                     autoscaling_instances['AutoScalingInstances']
                                                     if asg_instance["InstanceId"] == instance['InstanceId']), None)

                        if not instance_autoscaling:
                            instance_data['isTerminationProtected'] = ec2_protection['DisableApiTermination']['Value']
                        else:
                            instance_data['autoScaled'] = True
                            instance_data['autoScalingGroupName'] = instance_autoscaling['AutoScalingGroupName']
                            instance_data['autoScalingHealthStatus'] = instance_autoscaling['HealthStatus']
                    instance_data_list.append(instance_data)
                except BaseException as e:
                    context_helper.logger().exception("Some exception occurred while getting Ec2Instance=%s, %s",
                                                      instance['InstanceId'], e)
        return instance_data_list if instance_data_list else None

    def get_security_groups_details(self):
        results = []
        response = self.client.describe_security_groups()
        results.extend(response['SecurityGroups'])
        while 'NextToken' in response:
            next_token = response['NextToken']
            response = self.client.describe_security_groups(NextToken=next_token)
            results.extend(response['SecurityGroups'])
            next_token = response['NextToken'] if response.get('NextToken') else False
        security_groups = []
        for sec_group in results:
            try:
                security_group = {'id': sec_group['GroupId'], 'name': sec_group['GroupName'],
                                  'tags': None, 'vpcId': None, 'region': self.region_name, 'ingressRules': [],
                                  'egressRules': []}
                if 'Tags' in sec_group:
                    security_group['tags'] = sec_group['Tags']
                if 'VpcId' in sec_group:
                    security_group['vpcId'] = sec_group['VpcId']
                for ingress in sec_group['IpPermissions']:
                    security_group['ingressRules'].append(
                        {'fromPort': ingress.get('FromPort') if ingress.get('FromPort') else None,
                         'toPort': ingress.get('ToPort') if ingress.get('ToPort') else None,
                         'ipRange': ingress['IpRanges']})
                for egress in sec_group['IpPermissionsEgress']:
                    security_group['egressRules'].append(
                        {'fromPort': egress.get('FromPort') if egress.get('FromPort') else None,
                         'toPort': egress.get('ToPort') if egress.get('ToPort') else None,
                         'ipRange': egress['IpRanges'] if egress['IpRanges'] else None})
                security_groups.append(security_group)
            except BaseException as e:
                context_helper.logger().exception("Some exception occurred while getting SecurityGroup=%s, %s",
                                                  sec_group['GroupId'], e)
        return security_groups if security_groups else None

    def get_stale_security_groups(self, vpc_id):
        results = []
        response = self.client.describe_stale_security_groups(VpcId=vpc_id)
        results.extend(response['StaleSecurityGroupSet'])
        while 'NextToken' in response:
            next_token = response['NextToken']
            response = self.client.describe_stale_security_groups(VpcId=vpc_id, NextToken=next_token)
            results.extend(response['StaleSecurityGroupSet'])
            next_token = response['NextToken'] if response.get('NextToken') else False
        stale_sg_list = []
        for stale_sg in results:
            stale_sg_list.append({'id': stale_sg['GroupId'], 'name': stale_sg['GroupName'], 'region': self.region_name})
        return stale_sg_list

    def get_volume_details(self):
        results = []
        response = self.client.describe_volumes()
        results.extend(response['Volumes'])
        while 'NextToken' in response:
            next_token = response['NextToken']
            response = self.client.describe_volumes(NextToken=next_token)
            results.extend(response['Volumes'])
            next_token = response['NextToken'] if response.get('NextToken') else False
        volumes_data = []
        for volume in results:
            try:
                volume_data = {'id': volume['VolumeId'], 'type': volume['VolumeType'], 'size': volume['Size'],
                               'availabilityZone': volume['AvailabilityZone'],
                               'createdOn': volume['CreateTime'].isoformat(),
                               'attachments': [], 'region': self.region_name, 'isEncrypted': volume['Encrypted']}
                if 'Iops' in volume:
                    volume_data['iops'] = volume['Iops']
                if 'Tags' in volume:
                    volume_data['tags'] = volume['Tags']
                    for tag in volume_data['tags']:
                        if tag['Key'].lower() == 'name':
                            volume_data['name'] = tag['Value']
                for attachment in volume['Attachments']:
                    volume_data['attachments'].append({'attachedOn': attachment['AttachTime'].isoformat(),
                                                       'instanceId': attachment['InstanceId']})
                volumes_data.append(volume_data)
            except BaseException as e:
                context_helper.logger().exception("Some exception occurred while getting Volume=%s, %s",
                                                  volume['VolumeId'], e)
        return volumes_data if volumes_data else None

    def get_snapshot_details(self):
        results = []
        response = self.client.describe_snapshots(
            OwnerIds=[context_helper.get_current_session()['attributes']['accountNumber']])
        results.extend(response['Snapshots'])
        while 'NextToken' in response:
            next_token = response['NextToken']
            response = self.client.describe_snapshots(
                OwnerIds=[context_helper.get_current_session()['attributes']['accountNumber']], NextToken=next_token)
            results.extend(response['Snapshots'])
            next_token = response['NextToken'] if response.get('NextToken') else False
        snapshots = []
        for snapshot in results:
            try:
                snapshot_data = {'id': snapshot['SnapshotId'], 'volumeId': snapshot['VolumeId'],
                                 'isEncrypted': snapshot['Encrypted'], 'volumeSize': snapshot['VolumeSize'],
                                 'createdOn': snapshot['StartTime'].isoformat(),
                                 'description': snapshot['Description'], 'region': self.region_name}
                if 'Tags' in snapshot:
                    snapshot_data['tags'] = snapshot['Tags']
                    for tag in snapshot_data['tags']:
                        if tag['Key'].lower() == 'name':
                            snapshot_data['name'] = tag['Value']
                snapshots.append(snapshot_data)
            except BaseException as e:
                context_helper.logger().exception("Some exception occurred while getting Snapshot=%s, %s",
                                                  snapshot['SnapshotId'], e)
        return snapshots if snapshots else None

    def get_eip_details(self):
        addresses = self.client.describe_addresses()
        eips = []
        for address in addresses['Addresses']:
            try:
                eip = {'ip': address['PublicIp'], 'domain': address['Domain'], 'allocationId': None,
                       'region': self.region_name, 'id': address['PublicIp']}
                if address['Domain'] == 'vpc':
                    eip['allocationId'] = address['AllocationId']
                    if 'AssociationId' in address:
                        eip['networkInterfaceId'] = address['NetworkInterfaceId']
                if 'InstanceId' in address and address['InstanceId']:
                    eip['instanceId'] = address['InstanceId']
                if 'Tags' in address:
                    eip['tags'] = address['Tags']
                    for tag in eip['tags']:
                        if tag['Key'].lower() == 'name':
                            eip['name'] = tag['Value']
                eips.append(eip)
            except BaseException as e:
                context_helper.logger().exception("Some exception occurred while getting ElasticIP=%s, %s",
                                                  address['PublicIp'], e)
        return eips if eips else None

    def get_eni_details(self):
        response = self.client.describe_network_interfaces()
        enis = []

        for interface in response['NetworkInterfaces']:
            try:
                eni = {'id': interface['NetworkInterfaceId'], 'status': interface['Status'],
                       'subnetId': interface['SubnetId'], 'availabilityZone': interface['AvailabilityZone'],
                       'association': None, 'attachment': None,
                       'type': interface['InterfaceType'], 'region': self.region_name}
                if interface['Description']:
                    eni['description'] = interface['Description']
                if 'TagSet' in interface:
                    eni['tags'] = interface['TagSet']
                    for tag in eni['tags']:
                        if tag['Key'].lower() == 'name':
                            eni['name'] = tag['Value']
                if 'Association' in interface and 'AssociationId' in interface['Association']:
                    eni['association'] = {'id': interface['Association']['AssociationId'],
                                          'publicIp': interface['Association']['PublicIp'],
                                          'allocationId': interface['Association']['AllocationId']}
                if 'Attachment' in interface:
                    eni['attachment'] = {'id': interface['Attachment']['AttachmentId'],
                                         'instanceId': interface['Attachment'].get('InstanceId'),
                                         'status': interface['Attachment']['Status'],
                                         'attachedOn': interface['Attachment'].get(
                                             'AttachTime').isoformat() if 'AttachTime' in interface[
                                             'Attachment'] else None
                                         }
                enis.append(eni)
            except BaseException as e:
                context_helper.logger().exception("Some exception occurred while getting ENI=%s, %s",
                                                  interface['NetworkInterfaceId'], e)
        return enis if enis else None

    def __get_vpc_nat_gateways(self):
        results = []
        response = self.client.describe_nat_gateways()
        results.extend(response['NatGateways'])
        while 'NextToken' in response:
            next_token = response['NextToken']
            response = self.client.describe_nat_gateways(NextToken=next_token)
            results.extend(response['NatGateways'])
            next_token = response['NextToken'] if response.get('NextToken') else False
        return results

    def get_vpc_endpoint_details(self):
        '''
        Sampel Output:
        "vpcEndpoints": [
          {
            "id": "vpce-02d61e5816f638f9b",
            "serviceName": "com.amazonaws.us-east-1.s3",
            "status": "available",
            "type": "Gateway",
            "vpcId": "vpc-78ef0b02"
          }
        ]
        '''
        results = []
        response = self.client.describe_vpc_endpoints(Filters=[{'Name': 'vpc-endpoint-state', 'Values': ['available']}])
        results.extend(response['VpcEndpoints'])
        while 'NextToken' in response:
            next_token = response['NextToken']
            response = self.client.describe_vpc_endpoints(Filters=[{'Name': 'vpc-endpoint-state',
                                                                    'Values': ['available']}], NextToken=next_token)
            results.extend(response['VpcEndpoints'])
            next_token = response['NextToken'] if response.get('NextToken') else False
        vpc_end_points = []
        for endpoint in results:
            try:
                endpoint_detail = {'id': endpoint['VpcEndpointId'], 'vpcId': endpoint['VpcId'],
                                   'serviceName': endpoint['ServiceName'], 'status': endpoint['State'],
                                   'type': endpoint['VpcEndpointType']}
                vpc_end_points.append(endpoint_detail)
            except BaseException as e:
                context_helper.logger().exception("Some exception occurred while getting VPCEndpoint=%s, %s",
                                                  endpoint['VpcEndpointId'], e)
        return vpc_end_points

    def __get_egress_only_gateways(self):
        results = []
        response = self.client.describe_egress_only_internet_gateways()
        results.extend(response['EgressOnlyInternetGateways'])
        while 'NextToken' in response:
            next_token = response['NextToken']
            response = self.client.describe_egress_only_internet_gateways(NextToken=next_token)
            results.extend(response['EgressOnlyInternetGateways'])
            next_token = response['NextToken'] if response.get('NextToken') else False
        return results

    def __describe_flow_logs(self):
        results = []
        response = self.client.describe_flow_logs()
        results.extend(response['FlowLogs'])
        while 'NextToken' in response:
            next_token = response['NextToken']
            response = self.client.describe_flow_logs(NextToken=next_token)
            results.extend(response['FlowLogs'])
            next_token = response['NextToken'] if response.get('NextToken') else False
        return results

    def get_vpc_details(self):
        vpcs = self.client.describe_vpcs()
        vpc_gateways = self.__get_vpc_nat_gateways()
        egress_only_gateways = self.__get_egress_only_gateways()
        flow_logs = self.__describe_flow_logs()

        vpc_data_list = []
        for vpc in vpcs['Vpcs']:
            try:
                vpc_data = {'id': vpc['VpcId'], 'hasIPv6Association': False, 'isDefault': vpc['IsDefault'],
                            'hasEgressOnlyInternetGateways': False, 'region': self.region_name, 'natGateways': [],
                            'flowLogs': []}
                try:
                    if vpc['Ipv6CidrBlockAssociationSet']:
                        vpc_data['hasIPv6Association'] = True
                except KeyError as e:
                    pass
                if 'Tags' in vpc:
                    vpc_data['tags'] = vpc['Tags']
                    for tag in vpc_data['tags']:
                        if tag['Key'].lower() == 'name':
                            vpc_data['name'] = tag['Value']
                vpc_data['staleSecurityGroups'] = self.get_stale_security_groups(vpc['VpcId'])
                for vpc_gateway in vpc_gateways:
                    if vpc_gateway["VpcId"] == vpc['VpcId']:
                        nat_gateway = {'id': vpc_gateway['NatGatewayId'],
                                       'createdOn': vpc_gateway['CreateTime'].isoformat()}
                        if 'State' in vpc_gateway:
                            nat_gateway['state'] = vpc_gateway['State']
                        vpc_data['natGateways'].append(nat_gateway)

                for egress_only_gateway in egress_only_gateways:
                    if egress_only_gateway['Attachments'][0]['VpcId'] == vpc['VpcId']:
                        vpc_data['hasEgressOnlyInternetGateways'] = True

                for flow_log in flow_logs:
                    if flow_log["ResourceId"] == vpc['VpcId']:
                        vpc_data['flowLogs'].append({'id': flow_log['FlowLogId'], 'name': flow_log['LogGroupName'],
                                                     'status': flow_log['FlowLogStatus'],
                                                     'hasError': True if (
                                                             'DeliverLogsErrorMessage' in flow_log) else False})
                vpc_data_list.append(vpc_data)
            except BaseException as e:
                context_helper.logger().exception("Some exception occurred while getting VPC=%s, %s", vpc['VpcId'], e)
        return vpc_data_list if vpc_data_list else None

    def get_subnet_details(self):
        response = self.client.describe_subnets()
        subnets = []
        for subnet in response['Subnets']:
            subnet_data = {'id': subnet['SubnetId'], 'vpcId': subnet['VpcId'],
                           'availabilityZone': subnet['AvailabilityZone'], 'state': subnet['State']}
            subnets.append(subnet_data)
        return subnets

    def get_route_table_details(self):
        response = self.client.describe_route_tables(Filters=[
            {
                'Name': 'association.main',
                'Values': ['false']
            }
        ])
        route_table_list = []
        for route in response['RouteTables']:
            try:
                route_table_detail = {'id': route['RouteTableId'], 'associations': [], 'region': self.region_name}
                if 'VpcId' in route:
                    route_table_detail['vpcId'] = route['VpcId']
                if 'Tags' in route:
                    route_table_detail['tags'] = route['Tags']
                    for tag in route_table_detail['tags']:
                        if tag['Key'].lower() == 'name':
                            route_table_detail['name'] = tag['Value']
                if 'Associations' in route:
                    route_table_detail['associations'] = route['Associations']
                route_table_list.append(route_table_detail)
            except BaseException as e:
                context_helper.logger().exception("Some exception occurred while getting RouteTable=%s, %s",
                                                  route['RouteTableId'], e)
        return route_table_list if route_table_list else None

    def get_internet_gateway_details(self):
        response = self.client.describe_internet_gateways()
        internet_gateways = []
        for igw in response['InternetGateways']:
            try:
                internet_gateway = {'id': igw['InternetGatewayId'], 'region': self.region_name}
                if 'Tags' in igw:
                    internet_gateway['tags'] = igw['Tags']
                    for tag in internet_gateway['tags']:
                        if tag['Key'].lower() == 'name':
                            internet_gateway['name'] = tag['Value']
                if 'Attachments' in igw:
                    internet_gateway['attachments'] = igw['Attachments']
                internet_gateways.append(internet_gateway)
            except BaseException as e:
                context_helper.logger().exception("Some exception occurred while getting InternetGateway=%s, %s",
                                                  igw['InternetGatewayId'], e)
        return internet_gateways if internet_gateways else None

    def get_vpn_gateways(self):
        response = self.client.describe_vpn_gateways()
        vpn_gateways = []
        for vpngw in response['VpnGateways']:
            try:
                vpn_gateway = {'id': vpngw['VpnGatewayId'], 'state': vpngw['State'], 'type': vpngw['Type'],
                               'region': self.region_name}
                if 'AvailabilityZone' in vpngw:
                    vpn_gateway['availabilityZone'] = vpngw['AvailabilityZone']
                if 'VpcAttachments' in vpngw:
                    vpn_gateway['vpcAttachments'] = vpngw['VpcAttachments']
                if 'Tags' in vpngw:
                    vpn_gateway['tags'] = vpngw['Tags']
                    for tag in vpn_gateway['tags']:
                        if tag['Key'].lower() == 'name':
                            vpn_gateway['name'] = tag['Value']
                vpn_gateways.append(vpn_gateway)
            except BaseException as e:
                context_helper.logger().exception("Some exception occurred while getting VPNGateway=%s, %s",
                                                  vpngw['VpnGatewayId'], e)
        return vpn_gateways if vpn_gateways else None

    def get_ami_details(self):
        response = self.client.describe_images(Filters=[
            {
                'Name': 'owner-id',
                'Values': [context_helper.get_current_session()['attributes']['accountNumber']]
            }
        ])
        amis = []
        for image in response['Images']:
            try:
                ami = {'id': image['ImageId'], 'state': image['State'], 'region': self.region_name, 'snapshots': []}
                if 'Tags' in image:
                    ami['tags'] = image['Tags']
                    for tag in ami['tags']:
                        if tag['Key'].lower() == 'name':
                            ami['name'] = tag['Value']
                if image['Name']:
                    ami['name'] = image['Name']
                try:
                    created_on = datetime.strptime(image['CreationDate'], '%Y-%m-%dT%H:%M:%S.000Z')
                    ami['createdOn'] = created_on.isoformat()
                    date_diff = datetime.now() - created_on
                    ami['age'] = date_diff.days
                    for block_device_mapping in image['BlockDeviceMappings']:
                        ami['snapshots'].append(block_device_mapping['Ebs']['SnapshotId'])
                except BaseException as e:
                    pass
                amis.append(ami)
            except BaseException as e:
                context_helper.logger().exception("Some exception occurred while getting AMI=%s, %s", image['ImageId'],
                                                  e)
        return amis if amis else None

    def delete_volume(self, volume_id):
        if not volume_id:
            return {'success': False, 'error_code': 'EC2_NO_VOLUME_ID', 'message': 'Volume ID not provided'}
        try:
            self.client.delete_volume(
                VolumeId=volume_id,
                DryRun=True
            )
        except ClientError as e:
            if 'DryRunOperation' not in str(e):
                return {'success': False, 'error_code': 'EC2_UNAUTHORIZED', 'message': repr(e)}
        try:
            self.client.delete_volume(
                VolumeId=volume_id,
                DryRun=False
            )
            return {'success': True}
        except BaseException as e:
            context_helper.logger().exception("Some exception occurred while deleting Volume=%s, %s",
                                              volume_id, e)
            return {'success': False, 'error_code': 'EXCEPTION', 'message': repr(e)}

    def delete_eip(self, public_ip, allocation_id):
        if not allocation_id and not public_ip:
            return {'success': False, 'error_code': 'EC2_INVALID_ARGS', 'message': 'AllocationId or '
                                                                                   'PublicIP not provided'}
        try:
            if allocation_id:
                self.client.release_address(
                    AllocationId=allocation_id,
                    DryRun=True
                )
            else:
                self.client.release_address(
                    PublicIp=public_ip,
                    DryRun=True
                )
        except ClientError as e:
            if 'DryRunOperation' not in str(e):
                return {'success': False, 'error_code': 'EC2_UNAUTHORIZED', 'message': repr(e)}
        try:
            if allocation_id:
                self.client.release_address(
                    AllocationId=allocation_id,
                    DryRun=False
                )
            else:
                self.client.release_address(
                    PublicIp=public_ip,
                    DryRun=False
                )
            return {'success': True}
        except BaseException as e:
            context_helper.logger().exception("Some exception occurred while deleting EIP=%s, %s",
                                              allocation_id, e)
            return {'success': False, 'error_code': 'EXCEPTION', 'message': repr(e)}

    def delete_ami(self, image_id):
        if not image_id:
            return {'success': False, 'error_code': 'EC2_NO_IMAGE_ID', 'message': 'Image ID not provided'}
        try:
            self.client.deregister_image(
                ImageId=image_id,
                DryRun=True
            )
        except ClientError as e:
            if 'DryRunOperation' not in str(e):
                return {'success': False, 'error_code': 'EC2_UNAUTHORIZED', 'message': repr(e)}
        try:
            self.client.deregister_image(
                ImageId=image_id,
                DryRun=False
            )
            return {'success': True}
        except BaseException as e:
            context_helper.logger().exception("Some exception occurred while deleting Image=%s, %s",
                                              image_id, e)
            return {'success': False, 'error_code': 'EXCEPTION', 'message': repr(e)}

    def terminate_instances(self, instance_ids):
        if not instance_ids:
            return {'success': False, 'error_code': 'EC2_NO_INSTANCE_ID', 'message': 'InstanceID(s) not provided'}
        if not isinstance(instance_ids, list):
            instance_ids = [instance_ids]
        try:
            self.client.terminate_instances(
                InstanceIds=instance_ids,
                DryRun=True
            )
        except ClientError as e:
            if 'DryRunOperation' not in str(e):
                return {'success': False, 'error_code': 'EC2_UNAUTHORIZED',
                        'message': repr(e)}
        try:
            self.client.terminate_instances(
                InstanceIds=instance_ids,
                DryRun=False
            )
            return {'success': True}
        except BaseException as e:
            context_helper.logger().exception("Some exception occurred while terminating Instances=%s, %s",
                                              ''.join(instance_ids), e)
            return {'success': False, 'error_code': 'EXCEPTION', 'message': repr(e)}

    def stop_waiter(self, instance_ids):
        waiter = self.client.get_waiter('instance_stopped')
        if not isinstance(instance_ids, list):
            instance_ids = [instance_ids]
        waiter.wait(InstanceIds=instance_ids)

    def start_waiter(self, instance_ids):
        waiter = self.client.get_waiter('instance_running')
        if not isinstance(instance_ids, list):
            instance_ids = [instance_ids]
        waiter.wait(InstanceIds=instance_ids)

    def stop_instances(self, instance_ids):
        if not instance_ids:
            return {'success': False, 'error_code': 'EC2_NO_INSTANCE_ID', 'message': 'InstanceID(s) not provided'}
        if not isinstance(instance_ids, list):
            instance_ids = [instance_ids]
        try:
            self.client.stop_instances(
                InstanceIds=instance_ids,
                DryRun=True
            )
        except ClientError as e:
            if 'DryRunOperation' not in str(e):
                return {'success': False, 'error_code': 'EC2_UNAUTHORIZED',
                        'message': repr(e)}
        try:
            self.client.stop_instances(
                InstanceIds=instance_ids,
                DryRun=False
            )
            return {'success': True}
        except BaseException as e:
            context_helper.logger().exception("Some exception occurred while stopping Instances=%s, %s",
                                              ''.join(instance_ids), e)
            return {'success': False, 'error_code': 'EXCEPTION', 'message': repr(e)}

    def start_instances(self, instance_ids):
        if not instance_ids:
            return {'success': False, 'error_code': 'EC2_NO_INSTANCE_ID', 'message': 'InstanceID(s) not provided'}
        if not isinstance(instance_ids, list):
            instance_ids = [instance_ids]
        try:
            self.client.start_instances(
                InstanceIds=instance_ids,
                DryRun=True
            )
        except ClientError as e:
            if 'DryRunOperation' not in str(e):
                return {'success': False, 'error_code': 'EC2_UNAUTHORIZED',
                        'message': repr(e)}
        try:
            self.client.start_instances(
                InstanceIds=instance_ids,
                DryRun=False
            )
            return {'success': True}
        except BaseException as e:
            context_helper.logger().exception("Some exception occurred while starting Instances=%s, %s",
                                              ''.join(instance_ids), e)
            return {'success': False, 'error_code': 'EXCEPTION', 'message': repr(e)}

    def delete_security_group(self, security_group_id):
        if not security_group_id:
            return {'success': False, 'error_code': 'VALUE_ERROR', 'message': 'Security Group ID not provided'}
        try:
            self.client.delete_security_group(
                GroupId=security_group_id,
                DryRun=True
            )
        except ClientError as e:
            print(e)
            if 'DryRunOperation' not in str(e):
                return {'success': False, 'error_code': 'UNAUTHORIZED',
                        'message': repr(e)}
        try:
            self.client.delete_security_group(
                GroupId=security_group_id,
                DryRun=False
            )
            return {'success': True}
        except BaseException as e:
            context_helper.logger().exception("Some exception occurred while deleting SecurityGroup=%s, %s",
                                              security_group_id, e)
            return {'success': False, 'error_code': 'EXCEPTION', 'message': repr(e)}

    def delete_eni(self, eni_id):
        if not eni_id:
            return {'success': False, 'error_code': 'VALUE_ERROR', 'message': 'NetworkInterfaceID not provided'}
        try:
            self.client.delete_network_interface(
                DryRun=True,
                NetworkInterfaceId=eni_id
            )
        except ClientError as e:
            if 'DryRunOperation' not in str(e):
                return {'success': False, 'error_code': 'UNAUTHORIZED', 'message': repr(e)}
        try:
            self.client.delete_network_interface(
                DryRun=False,
                NetworkInterfaceId=eni_id
            )
            return {'success': True}
        except BaseException as e:
            context_helper.logger().exception("Some exception occurred while deleting ENI=%s, %s",
                                              eni_id, e)
            return {'success': False, 'error_code': 'EXCEPTION', 'message': repr(e)}

    def delete_route_table(self, route_table_id):
        if not route_table_id:
            return {'success': False, 'error_code': 'VALUE_ERROR', 'message': 'RouteTableID not provided'}
        try:
            self.client.delete_route_table(
                DryRun=True,
                RouteTableId=route_table_id
            )
        except ClientError as e:
            if 'DryRunOperation' not in str(e):
                return {'success': False, 'error_code': 'UNAUTHORIZED', 'message': repr(e)}
        try:
            self.client.delete_route_table(
                DryRun=False,
                RouteTableId=route_table_id
            )
            return {'success': True}
        except BaseException as e:
            context_helper.logger().exception("Some exception occurred while deleting RouteTable=%s, %s",
                                              route_table_id, e)
            return {'success': False, 'error_code': 'EXCEPTION', 'message': repr(e)}

    def delete_snapshot(self, snapshot_id):
        if not snapshot_id:
            return {'success': False, 'error_code': 'VALUE_ERROR', 'message': 'SnapshotID not provided'}
        try:
            self.client.delete_snapshot(
                SnapshotId=snapshot_id,
                DryRun=True
            )
        except ClientError as e:
            if 'DryRunOperation' not in str(e):
                return {'success': False, 'error_code': 'UNAUTHORIZED', 'message': repr(e)}
        try:
            self.client.delete_snapshot(
                SnapshotId=snapshot_id,
                DryRun=False
            )
            return {'success': True}
        except BaseException as e:
            context_helper.logger().exception("Some exception occurred while deleting Snapshot=%s, %s",
                                              snapshot_id, e)
            return {'success': False, 'error_code': 'EXCEPTION', 'message': repr(e)}

    def delete_internet_gateway(self, internet_gateway_id):
        if not internet_gateway_id:
            return {'success': False, 'error_code': 'VALUE_ERROR', 'message': 'InternetGatewayID not provided'}
        try:
            self.client.delete_internet_gateway(
                DryRun=True,
                InternetGatewayId=internet_gateway_id
            )
        except ClientError as e:
            if 'DryRunOperation' not in str(e):
                return {'success': False, 'error_code': 'UNAUTHORIZED',
                        'message': repr(e)}
        try:
            self.client.delete_internet_gateway(
                DryRun=False,
                InternetGatewayId=internet_gateway_id
            )
            return {'success': True}
        except BaseException as e:
            context_helper.logger().exception("Some exception occurred while deleting InternetGateway=%s, %s",
                                              internet_gateway_id, e)
            return {'success': False, 'error_code': 'EXCEPTION', 'message': repr(e)}

    def delete_vpn_gateway(self, vpn_gateway_id):
        if not vpn_gateway_id:
            return {'success': False, 'error_code': 'VALUE_ERROR', 'message': 'VPNGatewayID not provided'}
        try:
            self.client.delete_vpn_gateway(
                VpnGatewayId=vpn_gateway_id,
                DryRun=True
            )
        except ClientError as e:
            if 'DryRunOperation' not in str(e):
                return {'success': False, 'error_code': 'UNAUTHORIZED', 'message': repr(e)}
        try:
            self.client.delete_vpn_gateway(
                VpnGatewayId=vpn_gateway_id,
                DryRun=False
            )
            return {'success': True}
        except BaseException as e:
            context_helper.logger().exception("Some exception occurred while deleting VPNGateway=%s, %s",
                                              vpn_gateway_id, e)
            return {'success': False, 'error_code': 'EXCEPTION', 'message': repr(e)}

    def get_vpc_endpoint_s3_service_name(self, region_id):
        # service_names = self.client.describe_vpc_endpoint_services()
        return 'com.amazonaws.' + region_id + '.s3'

    def create_s3_endpoint(self, vpc_id, region_id):
        if not vpc_id or not region_id:
            return {'success': False, 'error_code': 'VALUE_ERROR', 'message': 'VpcId or RegionId not provided'}
        try:
            self.client.create_vpc_endpoint(
                VpcId=vpc_id,
                ServiceName=self.get_vpc_endpoint_s3_service_name(region_id)
            )
            return {'success': True}
        except BaseException as e:
            context_helper.logger().exception("Some exception occurred while creating s3 endpoint "
                                              "for VPC=%s, %s",
                                              vpc_id, e)
            return {'success': False, 'error_code': 'EXCEPTION', 'message': repr(e)}

    def enable_termination_protection(self, instance_id):
        if not instance_id:
            return {'success': False, 'error_code': 'VALUE_ERROR', 'message': 'InstanceID not provided'}
        try:
            self.client.modify_instance_attribute(
                DisableApiTermination={
                    'Value': True
                },
                InstanceId=instance_id,
                DryRun=True,
            )
        except ClientError as e:
            if 'DryRunOperation' not in str(e):
                return {'success': False, 'error_code': 'UNAUTHORIZED',
                        'message': repr(e)}
        try:
            self.client.modify_instance_attribute(
                DisableApiTermination={
                    'Value': True
                },
                InstanceId=instance_id,
                DryRun=False,
            )
            return {'success': True}
        except BaseException as e:
            context_helper.logger().exception("Some exception occurred while enabling "
                                              "TerminationProtection for Instnace=%s, %s",
                                              instance_id, e)
            return {'success': False, 'error_code': 'EXCEPTION', 'message': repr(e)}

    def enable_ebs_optimise(self, instance_id):
        if not instance_id:
            return {'success': False, 'error_code': 'VALUE_ERROR', 'message': 'InstanceID not provided'}
        result = self.stop_instances(instance_id)
        if not result['success']:
            return result
        self.stop_waiter(instance_id)
        try:
            self.client.modify_instance_attribute(
                EbsOptimized={
                    'Value': True
                },
                InstanceId=instance_id,
                DryRun=True,
            )
        except ClientError as e:
            if 'DryRunOperation' not in str(e):
                return {'success': False, 'error_code': 'UNAUTHORIZED',
                        'message': repr(e)}
        try:
            self.client.modify_instance_attribute(
                EbsOptimized={
                    'Value': True
                },
                InstanceId=instance_id,
                DryRun=False,
            )
            result = self.start_instances(instance_id)
            self.start_waiter(instance_id)
            if not result['success']:
                result['message'] = 'Unable to start the instance. Please manually start the InstanceID=' + instance_id
                return result
            return {'success': True}
        except BaseException as e:
            context_helper.logger().exception("Some exception occurred while enabling "
                                              "EBSOptimize for InstanceID=%s, %s",
                                              instance_id, e)
            return {'success': False, 'error_code': 'EXCEPTION', 'message': repr(e)}

    def delete_instance_tags(self, instance_ids, tags):
        if not instance_ids:
            return {'success': False, 'error_code': 'VALUE_ERROR', 'message': 'InstanceID not provided'}
        if not isinstance(instance_ids, list):
            instance_ids = [instance_ids]
        try:
            self.client.delete_tags(
                DryRun=False,
                Resources=instance_ids,
                Tags=tags
            )
            return {'success': True}
        except BaseException as e:
            context_helper.logger().exception("Some exception occurred while deleting tags "
                                              "for InstanceID=%s, %s",
                                              instance_ids, e)
            return {'success': False, 'error_code': 'EXCEPTION', 'message': repr(e)}

    def set_instance_tags(self, instance_ids, tags):
        if not instance_ids:
            return {'success': False, 'error_code': 'VALUE_ERROR', 'message': 'InstanceID not provided'}
        if not isinstance(instance_ids, list):
            instance_ids = [instance_ids]
        try:
            self.client.create_tags(
                DryRun=False,
                Resources=instance_ids,
                Tags=tags
            )
            return {'success': True}
        except BaseException as e:
            context_helper.logger().exception("Some exception occurred while creating tags "
                                              "for InstanceID=%s, %s",
                                              instance_ids, e)
            return {'success': False, 'error_code': 'EXCEPTION', 'message': repr(e)}

    @staticmethod
    def get_unused_volume_count(volumes):
        unused_volume_count = 0
        unused_list = []
        cost = 0
        for volume in volumes:
            if not volume['attachments']:
                unused_volume_count += 1
                unused_list.append(volume['id'])
                cost += EC2.__calculate_volume_cost(volume)
        return unused_volume_count, unused_list, cost

    @staticmethod
    def __calculate_volume_cost(volume):
        costItems = Constants.cost_matrix['volumes'][volume['type']]
        cost = 0
        for costItem in costItems:
            cost += volume[costItem] * costItems[costItem]
        return cost

    @staticmethod
    def get_unused_eips_count(eips):
        unused_count = 0
        unused_list = []
        cost = 0
        for eip in eips:
            if 'instanceId' not in eip and not eip.get('networkInterfaceId'):
                unused_count += 1
                unused_list.append(eip['ip'])
                cost += Constants.cost_matrix['eips']
        return unused_count, unused_list, cost

    @staticmethod
    def get_unused_amis_count(amis):
        unused_count = 0
        unused_list = []
        for ami in amis:
            if 'age' in ami and ami['age'] > policy_helper.get_policy().max_ami_age():
                unused_count += 1
                unused_list.append(ami['id'])
        return unused_count, unused_list

    @staticmethod
    def get_stopped_instance_count(instances):
        unused_count = 0
        unused_list = []
        for instance in instances:
            if instance['state'] == 'stopped' and 'lastStateChangedOn' in instance:
                diff = datetime.now() - dateutil.parser.parse(instance['lastStateChangedOn']).replace(tzinfo=None)
                if diff.days > policy_helper.get_policy().max_stopped_instance_age():
                    unused_count += 1
                    unused_list.append(instance['id'])
        return unused_count, unused_list

    @staticmethod
    def get_unused_security_group_count(security_groups, instances):
        unused_count = 0
        unused_security_groups = []

        def is_security_group_used(instances, sec_group_id):
            if instances:
                for instance in instances:
                    for security_group in instance['securityGroups']:
                        if security_group['id'] == sec_grp['id']:
                            return True
            return False

        for sec_grp in security_groups:
            if sec_grp['name'] != 'default' and not is_security_group_used(instances, sec_grp['id']) and \
                    'ElasticMapReduce' not in sec_grp['name']:
                unused_security_groups.append(sec_grp['id'])
                unused_count += 1

        return unused_count, unused_security_groups

    @staticmethod
    def get_unused_enis_count(enis):
        unused_count = 0
        unused_list = []
        if enis:
            for eni in enis:
                if eni['status'] == 'available' and (eni.get('description') != 'RDSNetworkInterface'):
                    unused_count += 1
                    unused_list.append(eni['id'])
        return unused_count, unused_list

    @staticmethod
    def get_unused_snapshots_count(snapshots, volumes, amis):
        unused_count = 0
        unused_list = []

        def find_volume(volume_id):
            if volumes:
                for vlm in volumes:
                    if vlm['id'] == volume_id:
                        return vlm
            return False

        def find_image(ami_id):
            if amis:
                for ami in amis:
                    if ami['id'] == ami_id:
                        return ami
            return False

        for snapshot in snapshots:
            instance_id, image_id = Helpers.parse_snapshot_description(snapshot['description'])
            image = None
            if image_id:
                image = find_image(image_id)
            volume = find_volume(snapshot['volumeId'])
            if (image_id and not image) and not volume:
                unused_count += 1
                unused_list.append(snapshot['id'])
        return unused_count, unused_list;

    @staticmethod
    def get_unused_route_tables(route_tables):
        unused_count = 0
        unused_list = []
        for route_table in route_tables:
            if len(route_table['associations']) == 0:
                unused_count += 1
                unused_list.append(route_table['id'])
        return unused_count, unused_list

    @staticmethod
    def get_unused_internet_gateways(internet_gateways):
        unused_count = 0
        unused_list = []
        for internet_gateway in internet_gateways:
            if 'attachments' not in internet_gateway or not internet_gateway['attachments']:
                unused_count += 1
                unused_list.append(internet_gateway['id'])
        return unused_count, unused_list

    @staticmethod
    def get_unused_vpn_gateways(vpn_gateways):
        unused_count = 0
        unused_list = []
        cost = 0
        for vpn_gateway in vpn_gateways:
            if vpn_gateway['state'] == 'available' or not vpn_gateway.get('vpcAttachments'):
                unused_count += 1
                unused_list.append(vpn_gateway['id'])
                cost += Constants.cost_matrix['vpnGateways']
        return unused_count, unused_list, cost

    @staticmethod
    def get_ec2_without_iams(ec2s):
        count = 0
        item_list = []
        for ec2 in ec2s:
            if not 'iamProfileId' in ec2 or not ec2['iamProfileId']:
                count += 1
                item_list.append(ec2['id'])
        return count, item_list

    @staticmethod
    def get_security_groups_with_insecure_open_ports(security_groups):
        count = 0
        item_list = []
        for security_group in security_groups:
            if EC2.__check_sg_has_vulnerable_open_port(security_group,
                                                       policy_helper.get_policy().common_vulnerable_open_ports()):
                count += 1
                item_list.append(security_group['id'])
        return count, item_list

    @staticmethod
    def get_security_groups_with_open_ssh_port(security_groups):
        count = 0
        item_list = []
        for security_group in security_groups:
            if EC2.__check_sg_has_vulnerable_open_port(security_group,
                                                       [22]):
                count += 1
                item_list.append(security_group['id'])
        return count, item_list

    @staticmethod
    def __check_sg_has_vulnerable_open_port(security_group, ports):
        if 'ingressRules' in security_group:
            for ingress_rule in security_group['ingressRules']:
                if 'ipRange' in ingress_rule and ingress_rule['ipRange']:
                    for ip_range in ingress_rule['ipRange']:
                        if 'CidrIp' in ip_range and ip_range['CidrIp'] == '0.0.0.0/0':
                            if (ingress_rule['fromPort'] or ingress_rule['toPort']) and \
                                    (ingress_rule['fromPort'] == '-1' or ingress_rule['toPort'] == "-1" or
                                     ingress_rule['fromPort'] in ports or ingress_rule['toPort'] in ports):
                                return True
        return False

    @staticmethod
    def get_ec2s_without_TP(ec2s):
        count = 0
        item_list = []
        for ec2 in ec2s:
            if not ec2['isTerminationProtected']:
                count += 1
                item_list.append(ec2['id'])
        return count, item_list

    @staticmethod
    def get_stale_sec_groups(vpcs):
        count = 0
        item_list = []
        for vpc in vpcs:
            for stale_sg in vpc['staleSecurityGroups']:
                count += 1
                item_list.append(stale_sg['id'])
        return count, item_list

    @staticmethod
    def get_failing_nat_gateways(vpcs):
        count = 0
        item_list = []
        for vpc in vpcs:
            for nat_gateway in vpc['natGateways']:
                if not nat_gateway['state'] or nat_gateway['state'] == 'failed':
                    count += 1
                    item_list.append(nat_gateway['id'])
        return count, item_list

    @staticmethod
    def get_ipv6_vpc_wo_egress_igw(vpcs):
        count = 0
        item_list = []
        for vpc in vpcs:
            if vpc['hasEgressOnlyInternetGateways']:
                count += 1
                item_list.append(vpc['id'])
        return count, item_list

    @staticmethod
    def get_vpc_wo_private_subnet(vpcs):
        count = 0
        item_list = []
        for vpc in vpcs:
            if not vpc.get('natGateways'):
                count += 1
                item_list.append(vpc['id'])
        return count, item_list

    @staticmethod
    def get_classic_ec2s(ec2s):
        count = 0
        item_list = []
        for ec2 in ec2s:
            if not ec2.get('vpcId'):
                count += 1
                item_list.append(ec2['id'])
        return count, item_list

    @staticmethod
    def filter_ec2s_wo_ebs_optimised(ec2s):
        count = 0
        item_list = []
        for ec2 in ec2s:
            if not ec2.get('isEbsOptimized'):
                count += 1
                item_list.append(ec2['id'])
        return count, item_list

    @staticmethod
    def filter_volumes_unencrypted(volumes):
        count = 0
        item_list = []
        for volume in volumes:
            if not volume.get('isEncrypted'):
                count += 1
                item_list.append(volume['id'])
        return count, item_list

    @staticmethod
    def get_vpcs_without_s3_endpoints(vpcs, vpc_endpoints):
        count = 0
        item_list = []

        def vpc_has_endpoint(vpc_id, vpc_endpoints):
            for endpoint in vpc_endpoints:
                if endpoint['vpcId'] == vpc_id:
                    return True
            return False

        for vpc in vpcs:
            if not vpc_has_endpoint(vpc['id'], vpc_endpoints):
                count += 1
                item_list.append(vpc['id'])
        return count, item_list
