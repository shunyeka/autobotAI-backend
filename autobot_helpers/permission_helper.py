from models import cloud_service_provider, users
from services.aws.utils import Constants


def has_account_permission(user_id, account_id):
    user = users.get_by_email(user_id)
    csp = cloud_service_provider.get_by_account_id(user['rootUserId'], account_id)
    if csp:
        if user['userType'] == Constants.UserTypes.ROOT.value:
            return True
        elif user['permissions'].get('accounts'):
            return True if account_id in user['permissions'].get('accounts') else False
        else:
            return True
    return False
