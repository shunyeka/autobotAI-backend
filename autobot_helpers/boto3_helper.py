from datetime import datetime, timedelta
import boto3
from autobot_helpers import context_helper
from services.aws.utils import Constants, Helpers

autobot_region = 'Virginia'


def get_session(autobot_resources=False):
    context_helper.logger().debug("get_session called for %s", str(autobot_resources))
    session = None
    if session is None:
        if not autobot_resources or context_helper.app().config["ENVIRONMENT"] == "local":
            session = boto3.Session(
                aws_access_key_id=get_access_key(autobot_resources),
                aws_secret_access_key=get_secret_key(autobot_resources),
                region_name=get_region_id(get_region(autobot_resources)),
                aws_session_token=get_session_token(autobot_resources)
            )
        else:
            session = boto3.Session(region_name=get_region_id(get_region(autobot_resources)))
    return session


def get_autobot_access_role():
    if context_helper.app().config["ENVIRONMENT"] != "live":
        return "AutobotAIRoleStaging"
    else:
        return "AutobotAIRoleLive"


def get_client(resource, region_name=Constants.AWSRegions.VIRGINIA.value, autobot_resources=False):
    context_helper.logger().debug("get_client called for resource=%s, region=%s, autobot_resource=%s", resource,
                                  region_name, str(autobot_resources))
    client = None
    if client is None:
        if not autobot_resources or context_helper.app().config["ENVIRONMENT"] == "local":
            client = boto3.client(resource,
                                  aws_access_key_id=get_access_key(autobot_resources),
                                  aws_secret_access_key=get_secret_key(autobot_resources),
                                  region_name=region_name if region_name else get_region_id(
                                      get_region(autobot_resources)),
                                  aws_session_token=get_session_token(autobot_resources)
                                  )
        else:
            client = boto3.client(resource, region_name=region_name if region_name
            else get_region_id(get_region(autobot_resources)))
    return client


def get_dynamo_db_table(table_name, autobot_resources=False, live=False):
    context_helper.logger().debug("Called with table=%s, autbot_resources=%s", table_name, str(autobot_resources))
    if context_helper.app().config["ENVIRONMENT"] != "live" and not live:
        context_helper.logger().debug("Not production, using staging table=%s", table_name)
        table_name = "staging_" + table_name
    session = get_session(autobot_resources)
    dynamodb = session.resource('dynamodb', region_name=get_region_id(get_region(autobot_resources)))
    table = dynamodb.Table(table_name)
    context_helper.logger().debug("Returning dynamo table")
    return table


def get_access_key(autobot_resources=False):
    context_helper.logger().debug("Called with autobot_resources=%s", str(autobot_resources))
    if autobot_resources:
        return context_helper.app().config["ACCESS_KEY"]
    else:
        if (datetime.now() - Helpers.fromisoformat(
                context_helper.get_current_session()['attributes']['stsCredsGeneratedOn'])).total_seconds() > 3600:
            context_helper.refresh_sts_creds(context_helper.get_current_session())
        return context_helper.get_current_session()['attributes']['AccessKeyId']


def get_secret_key(autobot_resources=False):
    context_helper.logger().debug("Called with autobot_resources=%s", str(autobot_resources))
    if autobot_resources:
        return context_helper.app().config["SECRET_KEY"]
    else:
        return context_helper.get_current_session()['attributes']['SecretAccessKey']


def get_session_token(autobot_resources=False):
    context_helper.logger().debug("Called with autobot_resources=%s", str(autobot_resources))
    if autobot_resources:
        return None
    else:
        return context_helper.get_current_session()['attributes']['SessionToken']


def get_region(autobot_resources=False):
    context_helper.logger().debug("Called with autobot_resources=%s", str(autobot_resources))
    session = context_helper.get_current_session()
    try:
        if autobot_resources:
            return 'Virginia'
        else:
            context_helper.logger().debug("Getting user's default region")
            return session['attributes']['defaultRegion']
    except Exception as e:
        context_helper.logger().exception("Some exception while getting user's region, returning Virginia", e)
        return 'Virginia'


def get_all_regions():
    client = boto3.client('ec2')
    regions = [region['RegionName'] for region in client.describe_regions()['Regions']]
    return regions


regions = [
    {'id': 'us-east-1', 'name': 'Virginia'},
    {'id': 'ap-south-1', 'name': 'Mumbai'},
    {'id': 'ap-southeast-1', 'name': 'Singapore'},
    {'id': 'us-east-2', 'name': 'Ohio'},
    {'id': 'us-west-1', 'name': 'California'},
    {'id': 'us-west-2', 'name': 'Oregon'},
    {'id': 'ca-central-1', 'name': 'Canada'},
    {'id': 'eu-west-1', 'name': 'Ireland'},
    {'id': 'eu-central-1', 'name': 'Frankfurt'},
    {'id': 'eu-west-2', 'name': 'London'},
    {'id': 'ap-northeast-1', 'name': 'Tokyo'},
    {'id': 'ap-northeast-2', 'name': 'Seoul'},
    {'id': 'ap-northeast-3', 'name': 'Osaka-Local'},
    {'id': 'ap-southeast-2', 'name': 'Sydney'},
    {'id': 'eu-west-3', 'name': 'Paris'},
    {'id': 'sa-east-1', 'name': 'Sao Paulo(South America)'},
    {'id': 'cn-north-1', 'name': 'Beijing(China)'},
]


def get_region_id(set_region):
    if not set_region: return
    context_helper.logger().debug("Called with region_name=%s", set_region)
    for region in regions:
        if set_region in region['name']:
            return region['id']
    return "us-east-1"


def get_region_details_by_name(set_region):
    if not set_region: return
    context_helper.logger().debug("Called with region_name=%s", set_region)
    for region in regions:
        if set_region in region['name']:
            return region
    return regions[0]


def get_regions_details_by_names(region_names):
    if not region_names: return
    context_helper.logger().debug("Called with region_name=%s", region_names)
    region_detail_list = []
    for region in regions:
        for region_name in region_names:
            if region_name in region['name']:
                region_detail_list.append(region)
    return region_detail_list


def get_region_details_by_id(region_id):
    if not region_id: return
    context_helper.logger().debug("Called with region_name=%s", region_id)
    for region in regions:
        if region_id in region['id']:
            return region
    return regions[0]


def get_region_name(region_id):
    if not region_id: return
    context_helper.logger().debug("Called with region_name=%s", region_id)
    for region in regions:
        if region_id in region['id']:
            return region['name']
    return "Virginia"


def previous_week_range(date):
    start_date = date + timedelta(-date.weekday(), weeks=-1)
    end_date = date + timedelta(-date.weekday() - 1)
    return start_date, end_date
