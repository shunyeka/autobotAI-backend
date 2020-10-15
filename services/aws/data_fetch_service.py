import copy
from datetime import datetime

from autobot_helpers import context_helper, boto3_helper
from models import aws_intent_history, aws_datapoint_history
from services.aws.autoscaling import AutoScaling
from services.aws.budget import Budget
from services.aws.cloud_trail import CloudTrail
from services.aws.cost_explorer import CostExplorer
from services.aws.ec2 import EC2
from services.aws.elb import ELB
from services.aws.iam import IAM
from services.aws.maintenance_analyser import MaintenanceAnalyser
from services.aws.rds import RDS
from services.aws.s3 import S3
from services.aws.security_analyser import SecurityAnalyser
from services.aws.utils import Helpers, Constants
from autobot_helpers.context_helper import app
from multiprocessing import Process, Pipe
from models import cloud_service_provider
import traceback


def fetch_ec2_data(region, conn):
    ec2 = EC2(region_name=region)
    datapoints = {}
    datapoints['volumes'] = ec2.get_volume_details()
    datapoints['eips'] = ec2.get_eip_details()
    datapoints['snapshots'] = ec2.get_snapshot_details()
    datapoints['securityGroups'] = ec2.get_security_groups_details()
    datapoints['amis'] = ec2.get_ami_details()
    datapoints['ec2s'] = ec2.get_instances_details()
    conn.send([datapoints, region])
    conn.close()


def fetch_vpc_data(region, conn):
    ec2 = EC2(region_name=region)
    datapoints = {}
    datapoints['vpcs'] = ec2.get_vpc_details()
    datapoints['vpcEndpoints'] = ec2.get_vpc_endpoint_details()
    datapoints['enis'] = ec2.get_eni_details()
    datapoints['routeTables'] = ec2.get_route_table_details()
    datapoints['internetGateways'] = ec2.get_internet_gateway_details()
    datapoints['vpnGateways'] = ec2.get_vpn_gateways()
    # regional_data['datapoints']['subnets'] = ec2.get_subnet_details()
    conn.send([datapoints, region])
    conn.close()


def fetch_elb_data(region, conn):
    elb = ELB(region_name=region)
    datapoints = {}
    datapoints['elbs'] = elb.get_elb_details()
    datapoints['albs'] = elb.get_alb_details()
    datapoints['targetGroups'] = elb.get_target_groups_details()
    conn.send([datapoints, region])
    conn.close()


def fetch_rds_data(region, conn):
    rds_client = RDS(region_name=region)
    datapoints = {}
    datapoints['rdses'] = rds_client.get_rds_details()
    datapoints['rdsManualSnapshots'] = rds_client.get_rds_manual_snapshot_details()
    conn.send([datapoints, region])
    conn.close()


def fetch_autoscaling_data(region, conn):
    autoscaling_client = AutoScaling(region_name=region)
    datapoints = {}
    datapoints['launchConfigs'] = autoscaling_client.get_launchconfig_details()
    datapoints['autoScalingGroups'] = autoscaling_client.get_autoscaling_group_details()
    conn.send([datapoints, region])
    conn.close()


def fetch_cloudtrail_data(region, conn):
    cloudtrail_client = CloudTrail(region_name=region)
    datapoints = {}
    datapoints['cloudTrails'] = cloudtrail_client.get_cloud_trail_details()
    conn.send([datapoints, region])
    conn.close()

# Global Data


def fetch_iam_users(conn):
    iam_client = IAM()
    datapoints = {}
    datapoints['users'] = iam_client.get_user_details()
    conn.send([datapoints])
    conn.close()


def fetch_iam_roles(conn):
    iam_client = IAM()
    datapoints = {}
    datapoints['roles'] = iam_client.get_role_details()
    conn.send([datapoints])
    conn.close()


def fetch_iam_groups(conn):
    iam_client = IAM()
    datapoints = {}
    datapoints['groups'] = iam_client.get_group_details()
    conn.send([datapoints])
    conn.close()


def fetch_iam_others(conn):
    iam_client = IAM()
    datapoints = {}
    datapoints['accountSummary'] = iam_client.get_account_summary()
    datapoints['passwordPolicy'] = iam_client.get_password_policy_score()
    conn.send([datapoints])
    conn.close()


def fetch_s3_data(conn):
    s3_client = S3()
    datapoints = {}
    datapoints['s3Buckets'] = s3_client.get_s3_bucket_details()
    conn.send([datapoints])
    conn.close()


class DataFetchService:

    regional_function = [fetch_ec2_data, fetch_vpc_data, fetch_elb_data, fetch_rds_data,
                         fetch_autoscaling_data, fetch_cloudtrail_data]
    global_function = [fetch_iam_users, fetch_iam_roles, fetch_iam_groups, fetch_iam_others, fetch_s3_data]
    # regional_function = [fetch_ec2_data]
    # global_function = []

    @staticmethod
    def fetch_data():
        try:
            print("Data fetch service started")
            session = context_helper.get_current_session()
            response = {'success': False, 'regionalData': {}, 'globalData': { 'datapoints': {} }}
            if session.get('attributes', None):
                processes = []
                regional_p_con = []
                global_p_con = []

                for region_name in session['attributes']['activeRegions']:
                    region = boto3_helper.get_region_id(region_name)
                    for rfunct in DataFetchService.regional_function:
                        parent_conn, child_conn = Pipe()
                        process = Process(target=rfunct, args=(region, child_conn,))
                        processes.append(process)
                        regional_p_con.append(parent_conn)
                    app().logger.debug("Fetch completed for region=%s", region)
                    response['regionalData'][region] = { 'datapoints': {} }

                app().logger.debug("Fetch started for global data")
                for rfunct in DataFetchService.global_function:
                    parent_conn, child_conn = Pipe()
                    process = Process(target=rfunct, args=(child_conn,))
                    processes.append(process)
                    global_p_con.append(parent_conn)
                for process in processes:
                    process.start()

                for regional_con in regional_p_con:
                    con_response = regional_con.recv()
                    datapoints = con_response[0]
                    region = con_response[1]
                    for datapoint in datapoints:
                        response['regionalData'][region]['datapoints'][datapoint] = datapoints[datapoint]
                for global_con in global_p_con:
                    datapoints = global_con.recv()[0]
                    for datapoint in datapoints:
                        response['globalData']['datapoints'][datapoint] = datapoints[datapoint]
                for process in processes:
                    process.join()
                metadata = {}
                print("Data Analysis Stated")
                metadata['unusedResources'] = DataFetchService.analyze_data_for_unused_resources(response)
                metadata['securityIssues'] = SecurityAnalyser.analyse_data_for_security(response)
                metadata['maintenance'] = MaintenanceAnalyser.analyse_data(response)
                response['metadata'] = metadata
                print("Data Analysis Ended")
                print("Datapoint Save started")
                DataFetchService.save_datapoints(response, metadata)
                print("Datapoint Save ended")
                response['success'] = True
            app().logger.debug("Data fetch service ended")
            return {'success': True}
        except BaseException as e:
            context_helper.logger().exception("Some exception occurred while fetching data", e)
            return {'success': False, 'error_code': 'EXCEPTION', 'message': traceback.format_exc()}


    @staticmethod
    def analyze_data_for_unused_resources(dataset):
        unused_resources = copy.deepcopy(Constants.default_unused_dict)
        for region in dataset['regionalData']:
            for datapoint in dataset['regionalData'][region]['datapoints']:
                if dataset['regionalData'][region]['datapoints'][datapoint] is not None and len(
                        dataset['regionalData'][region]['datapoints'][datapoint]) > 0 and unused_resources.get(datapoint):
                    # Set the total
                    unused_resources[datapoint]['total'] += len(dataset['regionalData'][region]['datapoints'][datapoint]) if \
                        dataset['regionalData'][region]['datapoints'].get(datapoint, None) else 0

                    if datapoint == 'volumes':
                        count, unused_list, cost = EC2.get_unused_volume_count(
                            dataset['regionalData'][region]['datapoints'][datapoint])
                        unused_resources[datapoint]['unused'] += count
                        unused_resources[datapoint]['itemList'].extend(unused_list)
                        unused_resources[datapoint]['costSaving'] += cost
                    elif datapoint == 'snapshots':
                        unused_count, unused_list = EC2.get_unused_snapshots_count(
                            dataset['regionalData'][region]['datapoints'][datapoint],
                            dataset['regionalData'][region]['datapoints']['volumes'],
                            dataset['regionalData'][region]['datapoints']['amis'])
                        unused_resources[datapoint]['unused'] += unused_count
                        unused_resources[datapoint]['itemList'].extend(unused_list)
                    elif datapoint == 'enis':
                        unused_count, unused_sec_groups = EC2.get_unused_enis_count(
                            dataset['regionalData'][region]['datapoints'][datapoint])
                        unused_resources[datapoint]['unused'] += unused_count
                        unused_resources[datapoint]['itemList'].extend(unused_sec_groups)
                    elif datapoint == 'securityGroups':
                        unused_count, unused_sec_groups = EC2.get_unused_security_group_count(
                            dataset['regionalData'][region]['datapoints'][datapoint], dataset['regionalData'][region]['datapoints']['ec2s'])
                        unused_resources[datapoint]['unused'] += unused_count
                        unused_resources[datapoint]['itemList'].extend(unused_sec_groups)
                    elif datapoint == 'eips':
                        unused_count, unused_sec_groups, cost = EC2.get_unused_eips_count(
                            dataset['regionalData'][region]['datapoints'][datapoint])
                        unused_resources[datapoint]['unused'] += unused_count
                        unused_resources[datapoint]['itemList'].extend(unused_sec_groups)
                        unused_resources[datapoint]['costSaving'] += cost
                    elif datapoint == 'amis':
                        unused_count, unused_list = EC2.get_unused_amis_count(dataset['regionalData'][region]['datapoints'][datapoint])
                        unused_resources[datapoint]['unused'] += unused_count
                        unused_resources[datapoint]['itemList'].extend(unused_list)
                    elif datapoint == 'ec2s':
                        unused_count, unused_list = EC2.get_stopped_instance_count(
                            dataset['regionalData'][region]['datapoints'][datapoint])
                        unused_resources[datapoint]['unused'] += unused_count
                        unused_resources[datapoint]['itemList'].extend(unused_list)
                    elif datapoint == 'elbs':
                        unused_count, unused_list, cost = ELB.get_unused_elb_count(dataset['regionalData'][region]['datapoints'][datapoint])
                        unused_resources[datapoint]['unused'] += unused_count
                        unused_resources[datapoint]['itemList'].extend(unused_list)
                        unused_resources[datapoint]['costSaving'] += cost
                    elif datapoint == 'albs':
                        unused_count, unused_list, cost = ELB.get_unused_alb_count(dataset['regionalData'][region]['datapoints'][datapoint],
                                                                             dataset['regionalData'][region]['datapoints'][
                                                                                 'targetGroups'])
                        unused_resources[datapoint]['unused'] += unused_count
                        unused_resources[datapoint]['itemList'].extend(unused_list)
                        unused_resources[datapoint]['costSaving'] += cost
                    elif datapoint == 'autoScalingGroups':
                        unused_count, unused_list = AutoScaling.get_unused_autoscaling_groups(
                            dataset['regionalData'][region]['datapoints'][datapoint])
                        unused_resources[datapoint]['unused'] += unused_count
                        unused_resources[datapoint]['itemList'].extend(unused_list)
                    elif datapoint == 'launchConfigs':
                        unused_count, unused_list = AutoScaling.get_unused_lanuchconfigs(
                            dataset['regionalData'][region]['datapoints'][datapoint], dataset['regionalData'][region]['datapoints']['autoScalingGroups'])
                        unused_resources[datapoint]['unused'] += unused_count
                        unused_resources[datapoint]['itemList'].extend(unused_list)
                    elif datapoint == 'routeTables':
                        unused_count, unused_list = EC2.get_unused_route_tables(dataset['regionalData'][region]['datapoints'][datapoint])
                        unused_resources[datapoint]['unused'] += unused_count
                        unused_resources[datapoint]['itemList'].extend(unused_list)
                    elif datapoint == 'internetGateways':
                        unused_count, unused_list = EC2.get_unused_internet_gateways(
                            dataset['regionalData'][region]['datapoints'][datapoint])
                        unused_resources[datapoint]['unused'] += unused_count
                        unused_resources[datapoint]['itemList'].extend(unused_list)
                    elif datapoint == 'vpnGateways':
                        unused_count, unused_list, cost = EC2.get_unused_vpn_gateways(dataset['regionalData'][region]['datapoints'][datapoint])
                        unused_resources[datapoint]['unused'] += unused_count
                        unused_resources[datapoint]['itemList'].extend(unused_list)
                        unused_resources[datapoint]['costSaving'] += cost
                    elif datapoint == 'rdses':
                        unused_count, unused_list, cost = RDS.get_unused_rds_snapshots(dataset['regionalData'][region]['datapoints'][datapoint])
                        unused_resources[datapoint]['unused'] += unused_count
                        unused_resources[datapoint]['itemList'].extend(unused_list)
                        unused_resources[datapoint]['costSaving'] += cost
        for datapoint in unused_resources:
            if unused_resources[datapoint].get('costSaving'):
                unused_resources[datapoint]['costSaving'] = int(round(unused_resources[datapoint].get('costSaving')))
        return unused_resources

    @staticmethod
    def save_datapoints(dataset, metadata):
        timestamp = datetime.utcnow().isoformat()
        account_number = context_helper.get_current_session()['attributes']['accountNumber']
        Helpers.clean_dict_for_dynamo(dataset)
        Helpers.clean_dict_for_dynamo(metadata)
        aws_datapoint_history.save_all_resources(account_number=account_number, timestamp=timestamp,
                                                        dataset=dataset)
        aws_intent_history.save(account_number, Constants.Intents.ALL_RESOURCES.value, timestamp, metadata)

    @staticmethod
    def get_ri_details():
        response = {'success': False, 'data': {}}
        cost_explorer = CostExplorer()
        response['data']['riUtil'] = cost_explorer.get_last_weekly_ri_details()
        response['data']['riCoverage'] = cost_explorer.get_last_week_ri_coverage()
        response['data']['riRecommendation'] = cost_explorer.get_ri_recommendation()
        response['success'] = True
        return response

    @staticmethod
    def get_dashboard_data():
        response = {'success': False, 'data': {}}
        cost_explorer = CostExplorer()
        response['data']['riSavings'] = cost_explorer.get_savings_from_recommendations()
        response['data']['riCoverage'] = cost_explorer.get_last_week_ri_coverage()['total']
        response['data']['riUtil'] = cost_explorer.get_last_weekly_ri_details()['total']
        budget = Budget()
        budgets = budget.get_all_budgets()
        budgets['monthElapsed'] = round(Helpers.month_elapsed())
        budgets['yearElapsed'] = round(Helpers.year_elapsed())
        budgets['quarterElapsed'] = round(Helpers.quarter_elapsed())
        response['data']['budgets'] = budgets
        response['success'] = True
        return response

    @staticmethod
    def index_success_handler(email, account_id):
        try:
            cloud_service_provider.mark_indexed(email, account_id)
        except BaseException as e:
            print("Some exception occurred while enabling the user"+repr(e))

    @staticmethod
    def disable_account(email, account_id,  error, unauthorized=False):
        try:
            cloud_service_provider.disable_account(email, account_id, unauthorized)
            ses_client = boto3_helper.get_client('ses', autobot_resources=True)
            response = ses_client.send_email(
                Source='contact@autobot.live',
                Destination={
                    'ToAddresses': [
                        'contact@autobot.live',
                        'amit@autobot.live',
                        'amit.m.chotaliya@gmail.com',
                    ]
                },
                Message={
                    'Subject': {
                        'Data': 'Disabling indexing for account '+email,
                        'Charset': 'UTF-8',
                    },
                    'Body': {
                        'Text': {
                            'Data': 'Disabling data indexing for account with email '+email+' because of error '+error,
                            'Charset': 'UTF-8',
                        },
                    }
                }
            )
            print(response)
        except BaseException as e:
            context_helper.logger().exception("Some error occured while disabling user")
            print("Some exception occurred while disabling the user"+repr(e))

    @staticmethod
    def index_failure_handler(email, account_id, result):
        try:
            csp = cloud_service_provider.get_by_account_id(email, account_id)
            if result['error_code'] == 'UNAUTHORIZED' or csp.get('indexFailures', 0) > 4:
                DataFetchService.disable_account(email, account_id, result['error_code']+':'+result['message'],
                                                 (result['error_code'] == 'UNAUTHORIZED'))
                return
            else:
                cloud_service_provider.update_failure_count(email, account_id, csp.get('indexFailures', 0)+1)

            ses_client = boto3_helper.get_client('ses', autobot_resources=True)
            response = ses_client.send_email(
                Source='contact@autobot.live',
                Destination={
                    'ToAddresses': [
                        'contact@autobot.live',
                        'amit@shunyeka.com'
                    ]
                },
                Message={
                    'Subject': {
                        'Data': 'Indexing failure for account '+email,
                        'Charset': 'UTF-8',
                    },
                    'Body': {
                        'Text': {
                            'Data': 'Indexing failure for account with '
                                    'email '+email+' because of error '+result['error_code']+':'+result['message'],
                            'Charset': 'UTF-8',
                        },
                    }
                }
            )
        except BaseException as e:
            context_helper.logger().exception("Some error occured while disabling user")
            print("Some exception occurred while disabling the user"+repr(e))

    @staticmethod
    def schedule_data_fetch_for_account(email, account_id):
        try:
            sns_client = boto3_helper.get_client('sns', autobot_resources=True)
            context_helper.logger().info("Indexing account with email id = " + account_id)
            response = sns_client.publish(
                TopicArn='arn:aws:sns:us-east-1:480805696776:DataFetch-' + context_helper.app().config["ENVIRONMENT"],
                Message=account_id,
                Subject=email,
            )
            context_helper.logger().info("Indexing queued for account = " + str(response))
            print('indexing started for user ' + account_id)
            return {'success': True}
        except BaseException as e:
            context_helper.logger().exception("Some error occured while scheduling fetch for email="+account_id)
            print("Some exception occurred while scheduling fetch for email"+repr(e))
            return {'success': False, 'error_message': repr(e)}

    @staticmethod
    def test():
        iam = IAM()
        user_details = iam.get_account_summary()
        return user_details
