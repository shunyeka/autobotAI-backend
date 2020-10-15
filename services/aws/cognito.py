from autobot_helpers import boto3_helper
from flask import current_app as app
from services.aws.utils import Constants

class Cognito:

    def __init__(self):
        self.client = boto3_helper.get_client('cognito-idp', region_name=Constants.AWSRegions.VIRGINIA.value, autobot_resources=True)

    def create_sub_user(self, sub_user_data, root_user):
        response = self.client.sign_up(
            ClientId=app.config["COGNITO_CLIENT_ID"],
            Username=sub_user_data["email"],
            Password=sub_user_data['password'],
            UserAttributes=[
                {
                    'Name': 'email',
                    'Value': sub_user_data["email"]
                },
                {
                    'Name': 'given_name',
                    'Value': sub_user_data["name"]
                },
                {
                    'Name': 'phone_number',
                    'Value': sub_user_data["phone"]
                },
                {
                    'Name': 'custom:type',
                    'Value': 'SUBUSER'
                },
                {
                    'Name': 'custom:root_user',
                    'Value': root_user
                }
            ]
        )
        return response

