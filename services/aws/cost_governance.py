from services.aws.budget import Budget
from services.aws.cost_explorer import CostExplorer
from models import aws_intent_history
from services.aws.utils import Helpers
from autobot_helpers import context_helper


class CostGovernance:

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
    def get_ri_and_budget_details(account_id):
        response = {'data': {}}
        cost_explorer = CostExplorer()
        response['data']['riSavings'] = cost_explorer.get_savings_from_recommendations()
        response['data']['riCoverage'] = cost_explorer.get_last_week_ri_coverage()['total']
        response['data']['riUtil'] = cost_explorer.get_last_weekly_ri_details()['total']
        budget = Budget()
        budgets = budget.get_all_budgets()
        if budgets:
            budgets['monthElapsed'] = round(Helpers.month_elapsed())
            budgets['yearElapsed'] = round(Helpers.year_elapsed())
            budgets['quarterElapsed'] = round(Helpers.quarter_elapsed())
            response['data']['budgets'] = budgets
        response['success'] = True
        return response
