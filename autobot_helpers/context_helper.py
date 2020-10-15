import traceback
from datetime import datetime
from random import randint

from botocore.exceptions import ClientError
from flask import current_app
from flask import session as flask_session
from flask_ask import context as ask_context
from flask_ask import session as ask_session

from autobot_helpers import boto3_helper
from models import autobot_context
from models import cloud_service_provider, users
from services.aws.utils import Constants, Helpers


def get_current_session():
    return ask_session or flask_session or autobot_context.session


def get_current_context():
    return ask_context or autobot_context.context


def app():
    try:
        current_app.logger
        return current_app
    except Exception as e:
        return autobot_context.app


def logger():
    try:
        return current_app.logger
    except:
        return autobot_context.app.logger


def initialize(email=None, account_id=None):
    try:
        session = get_current_session()
        allregions = []

        user = users.get_by_email(email)
        isRoot = True
        if user['userType'] is not 'ROOT':
            root_user = users.get_by_email(user['rootUserId'])
            isRoot = False
        if not account_id:
            try:
                account_id = user['preferences']['defaultAccount']
            except BaseException as e:
                logger().info("Preferences are not set for %s, %s", user['id'], e)

        # DynamoDB connection and get all user data to store in session
        if account_id and email:
            csp = cloud_service_provider.get_by_account_id(email, account_id)
        elif email and not account_id:
            csp = cloud_service_provider.get_by_email(user['id'] if isRoot else root_user['id'])

        if csp is None: return {"success": False, "error_code": "AAI_ACCOUNT_NOT_FOUND",
                                "error_message": "autobotAI account not found"}
        if csp['roleArn'] is None: return {"success": False, "error_code": "AAI_ACCOUNT_LINKING_NOT_DONE",
                                           "error_message": "AWS account is not linked with autobotAI."}
        arn = csp['roleArn']
        csp_attributes = {
            "arn": csp['roleArn'],
            "accountnumber": arn[13:25],
            "rolename": arn[31:],
            "rolesession": arn[13:25] + arn[31:],
            "external_id": csp['externalId'],
            "email_id": csp['userId'],
            "default_region": csp.get('defaultRegion', Constants.AWSRegions.VIRGINIA.name.capitalize())
        }
        # Assume another account role before staring execution
        sts_client = boto3_helper.get_client('sts', autobot_resources=True)
        assumerole = sts_client.assume_role(
            RoleArn=csp['roleArn'],
            RoleSessionName=csp_attributes["rolesession"],
            ExternalId=csp_attributes["external_id"],
            DurationSeconds=3600
        )
        range_start = 10 ** (4 - 1)
        range_end = (10 ** 4) - 1
        otp = randint(range_start, range_end)

        credentials = assumerole['Credentials']
        session_attributes = {"AccessKeyId": credentials['AccessKeyId'],
                              "SecretAccessKey": credentials['SecretAccessKey'],
                              "SessionToken": credentials['SessionToken'],
                              "SessionOtp": str(otp), "email": csp_attributes['email_id'],
                              'accountNumber': csp['accountId'],
                              "default_region": csp_attributes['default_region'],
                              "defaultRegion": csp_attributes['default_region'], "setAction": "", "setEnvironment": "",
                              'roleSession': csp_attributes['rolesession'], 'externalId': csp_attributes["external_id"],
                              'roleArn': csp['roleArn'], 'stsCredsGeneratedOn': datetime.now().isoformat(),
                              'userId': user['id'], 'isRoot': isRoot, 'rootUserId': root_user['id'],
                              'permissions': user.get('permissions'), 'role_name': Helpers.role_from_arn(csp['roleArn'])
                              }
        ec2 = boto3_helper.get_client('ec2', autobot_resources=True)
        regions = ec2.describe_regions()
        for region in regions['Regions']:
            allregions.append(region['RegionName'])
        aws_global_regions = sorted(set(allregions))
        session_attributes['all_regions'] = aws_global_regions
        session_attributes['activeRegions'] = __get_active_regions(csp)
        session['attributes'] = session_attributes
        return {'success': True}
    except ClientError as e:
        print(traceback.format_exc())
        if 'AccessDenied' in str(e):
            return {'success': False, 'error_code': 'UNAUTHORIZED', 'message': repr(e)}
    except Exception as e:
        print(traceback.format_exc())
        return {'success': False, 'error_code': 'EXCEPTION', 'message': repr(e)}


def __get_active_regions(csp):
    regions = []
    if 'defaultRegion' in csp:
        regions.append(csp['defaultRegion'])
    if 'activeRegions' in csp:
        for region in csp['activeRegions']:
            regions.append(region)
    if not regions:
        regions.append('Virginia')
    return regions


def refresh_sts_creds(session):
    sts_client = boto3_helper.get_client('sts', autobot_resources=True)

    assumerole = sts_client.assume_role(
        RoleArn=session['attributes']['roleArn'],
        RoleSessionName=session['attributes']["roleSession"],
        ExternalId=session['attributes']["externalId"],
        DurationSeconds=3600
    )

    credentials = assumerole['Credentials']
    session['attributes']['AccessKeyId'] = credentials['AccessKeyId']
    session['attributes']['SecretAccessKey'] = credentials['SecretAccessKey']
    session['attributes']['SessionToken'] = credentials['SessionToken']
    session['attributes']['stsCredsGeneratedOn'] = datetime.now().isoformat()

