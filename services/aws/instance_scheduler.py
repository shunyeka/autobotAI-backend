import uuid
import botocore
from flask import current_app as app

from autobot_helpers import boto3_helper, context_helper
from lib.scheduler_cli.configuration.config_admin import ConfigAdmin
from services.aws.ec2 import EC2
from models.instance_schedule import InstanceSchedule

ENV_CONFIG = "CONFIG_TABLE"


class InstanceScheduler:
    def __init__(self):
        self.cf_client = boto3_helper.get_client("cloudformation")
        self.aws_scheduler_admin = ConfigAdmin(logger=context_helper.logger(),
                                               context=context_helper.get_current_context(),
                                               config_table=app.config["INSTANCE_SCHEDULER_CONFIG"][
                                                   "config_dynamo_table"])

    def _build_period_name(self, params):
        return f"period_{params.get('begintime', '')}_{params.get('endtime', '')}_{''.join(params.get('weekdays', []))}"

    def _create_period(self, params):
        period_name = self._build_period_name(params)
        try:
            self.aws_scheduler_admin.create_period(**{
                "name": self._build_period_name(params),
                "description": params["description"],
                "weekdays": params["weekdays"],
                "begintime": params.get("begintime"),
                "endtime": params.get("endtime")
            })
            return period_name
        except ValueError as e:
            import re
            match = re.search(r"^error: period.*already exists$", str(e))
            if match:
                return period_name
            raise e

    def _create_schedule(self, schedule_name, params, period_name):
        self.aws_scheduler_admin.create_schedule(**{
            "name": schedule_name,
            "description": params["description"],
            "periods": {period_name},
            "timezone": params["timezone"]
        })

    def _remote_role_name(self):
        response = self.cf_client.describe_stacks(
            StackName=app.config["INSTANCE_SCHEDULER_CONFIG"]["remote_cf_name"],
        )
        for stack in response['Stacks']:
            for output in stack["Outputs"]:
                if output["OutputKey"] == "CrossAccountRole":
                    return output["OutputValue"]

    def _add_role_to_config(self, role_arn):
        config_row_param = {
            "type": "config",
            "name": "scheduler"
        }
        config_table = boto3_helper.get_dynamo_db_table(app.config["INSTANCE_SCHEDULER_CONFIG"]["config_dynamo_table"],
                                                        autobot_resources=True, live=True)
        result = config_table.get_item(Key=config_row_param)
        if result and result.get('Item'):
            config = result['Item']
            config_roles = config.get('cross_account_roles', [])
            if role_arn not in config_roles:
                config_roles.append(role_arn)
                response = config_table.update_item(
                    Key=config_row_param,
                    UpdateExpression="set #roles = :r",
                    ExpressionAttributeNames={"#roles": 'cross_account_roles'},
                    ExpressionAttributeValues={
                        ':r': config_roles,
                    },
                    ReturnValues="UPDATED_NEW"
                )

    def _stack_exists(self):
        stacks = self.cf_client.list_stacks()['StackSummaries']
        for stack in stacks:
            if stack['StackStatus'] == 'DELETE_COMPLETE':
                continue
            if app.config["INSTANCE_SCHEDULER_CONFIG"]["remote_cf_name"] == stack['StackName']:
                print("AutobotScheduler stack exists")
                return True
        print("AutobotScheduler does not exist")
        return False

    def _create_stack(self):
        return self.cf_client.create_stack(
            StackName=app.config["INSTANCE_SCHEDULER_CONFIG"]["remote_cf_name"],
            TemplateURL=app.config["INSTANCE_SCHEDULER_CONFIG"]["remote_cf_template_url"],
            Parameters=[
                {
                    'ParameterKey': 'InstanceSchedulerAccount',
                    'ParameterValue': app.config["INSTANCE_SCHEDULER_CONFIG"]["master_account_no"],
                    'UsePreviousValue': False,
                },
            ],
            Capabilities=[
                'CAPABILITY_IAM'
            ],
        )

    def _remote_setup(self):
        try:
            if not self._stack_exists():
                print("Calling create cf stack")
                response = self._create_stack()
                print("Create stack response" + str(response))
                waiter = self.cf_client.get_waiter('stack_create_complete')
                print("Waiting for the stack to completed")
                waiter.wait(StackName=app.config["INSTANCE_SCHEDULER_CONFIG"]["remote_cf_name"])
                print("Stack creation completed")
                role_name = self._remote_role_name()
                self._add_role_to_config(role_name)
        except botocore.exceptions.ClientError as ex:
            error_message = ex.response['Error']['Message']
            if error_message == 'No updates are to be performed.':
                print("No changes")
            else:
                raise

    def _tag_ec2_resources(self, instances, scheduler_id):
        for region in instances:
            if not instances[region]:
                continue
            ec2 = EC2(region)
            ec2.set_instance_tags(instances[region],
                                  [{'Key': app.config["INSTANCE_SCHEDULER_CONFIG"]['resource_tag_name'],
                                    'Value': scheduler_id}])

    def _detag_ec2_resources(self, instances, scheduler_id):
        for region in instances:
            if not instances[region]:
                continue
            ec2 = EC2(region)
            ec2.delete_instance_tags(instances[region],
                                  [{'Key': app.config["INSTANCE_SCHEDULER_CONFIG"]['resource_tag_name'],
                                    'Value': scheduler_id}])

    def _validate_create_schedule(self, body):

        raise BaseException()

    def create_schedule(self, account_id, params):
        try:
            user_id = context_helper.get_current_session()['attributes']['rootUserId']
            schedule_id = str(uuid.uuid4())
            self._remote_setup()
            period_name = self._create_period(params)
            self._create_schedule(schedule_id, params, period_name)
            self._tag_ec2_resources(params["instances"], schedule_id)
            instance_schedule = InstanceSchedule({**params,
                                                  **{"schedule_id": schedule_id, "period_name":
                                                      period_name, "user_id": user_id, "csp_id": account_id
                                                     , "is_active": True}}).save()
            return {'success': True}
        except ValueError as e:
            print("Some error as Value Error")
            print(e)
            return {'success': False, 'error': str(e), 'error_code': 'VALIDATION_ERROR'}

    def delete_schedule(self, account_id, schedule_id):
        try:
            user_id = context_helper.get_current_session()['attributes']['rootUserId']
            schedule = InstanceSchedule.find_one(schedule_id, user_id)
            if not schedule:
                return {'success': False, 'error': "NOT_FOUND", 'error_code': 'Schedule not found'}
            self.aws_scheduler_admin.delete_schedule(schedule['schedule_id'])
            self._detag_ec2_resources(schedule['instances'], schedule['schedule_id'])
            schedule['is_active'] = False
            schedule.save()
            return {'success': True }
        except ValueError as e:
            print("Some error as Value Error")
            print(e)
            return {'success': False, 'error': str(e), 'error_code': 'VALIDATION_ERROR'}
        except BaseException as be:
            import traceback
            print(traceback.format_exc())
            return {'success': False, 'error': str(be), 'error_code': 'UNKNOWN_ERROR'}

    def list_schedules(self, account_id):
        user_id = context_helper.get_current_session()['attributes']['rootUserId']
        schedules = InstanceSchedule.find({"csp_id": account_id, "user_id": user_id, "is_active": True})
        return schedules
