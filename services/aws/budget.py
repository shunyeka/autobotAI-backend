from services.aws.utils import Constants, Helpers
from autobot_helpers import boto3_helper, context_helper

class Budget:

    def __init__(self):
        self.client = boto3_helper.get_client('budgets')

    def get_all_budgets(self):
        response = self.client.describe_budgets(
            AccountId=context_helper.get_current_session()['attributes']['accountNumber'])
        if 'Budgets' in response:
            budgets = {}
            for budget in response['Budgets']:
                if Constants.Budgets.has_value(budget['BudgetName']):
                    budget_forecast = int(float(budget['CalculatedSpend']['ForecastedSpend']['Amount']))
                    actual_spend = int(float(budget['CalculatedSpend']['ActualSpend']['Amount']))
                    budget_limit = int(float(budget['BudgetLimit']['Amount']))
                    budgets[budget['BudgetName']] = {
                        'budgetName': budget['BudgetName'],
                        'budgetForecast': round(budget_forecast),
                        'actualSpend': round(actual_spend),
                        'budgetLimit': round(budget_limit),
                        'budgetUtilization': round((actual_spend * 100) / budget_limit),
                        'forecastUtilization': round((actual_spend * 100) / budget_forecast),
                        'budgetVsForecast': round((budget_forecast * 100) / budget_limit)
                    }
            return budgets
        return None

