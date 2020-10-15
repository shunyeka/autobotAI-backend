from autobot_helpers import context_helper, boto3_helper
from datetime import datetime, timedelta
import json


class CostExplorer:

    def __init__(self):
        self.client = boto3_helper.get_client('ce')
        self.last_week_start, self.last_week_end = boto3_helper.previous_week_range(datetime.now())

    def get_last_weekly_ri_details(self):
        ri_hours_last_week_by_date = self.client.get_reservation_utilization(
            TimePeriod={'Start': self.last_week_start.strftime('%Y-%m-%d'),
                        'End': self.last_week_end.strftime('%Y-%m-%d')}, Granularity='DAILY')
        total = {}
        for item in ri_hours_last_week_by_date['Total']:
            try:

                total[item] = int(float(ri_hours_last_week_by_date['Total'][item]))
            except BaseException as e:
                total[item] = ri_hours_last_week_by_date['Total'][item]
        return {'weekStart': self.last_week_start.isoformat(), 'weekEnd': self.last_week_end.isoformat(),
                'weekNumber': self.last_week_start.isocalendar()[1],
                'riUtilBySubscription': self.__get_ri_util_by_subscription(),
                'riUtilByDate': ri_hours_last_week_by_date['UtilizationsByTime'],
                'total': total}

    def __get_ri_util_by_subscription(self):
        results = []
        response = self.client.get_reservation_utilization(
            TimePeriod={
                'Start': self.last_week_start.strftime('%Y-%m-%d'),
                'End': self.last_week_end.strftime('%Y-%m-%d')
            },
            Granularity='DAILY'
        )
        results.extend(response['UtilizationsByTime'])
        while 'nextToken' in response:
            next_token = response['nextToken']
            response = self.client.get_reservation_utilization(
                TimePeriod={
                    'Start': self.last_week_start.strftime('%Y-%m-%d'),
                    'End': self.last_week_end.strftime('%Y-%m-%d')
                },
                Granularity='DAILY',
                NextPageToken=next_token
            )
            results.extend(response['UtilizationsByTime'])
            next_token = response['nextToken'] if response.get('nextToken') else False
        return results

    def get_ri_recommendation(self):
        return {
            'ec2Recommendations': self.__get_ri_recommendation_by_service("Amazon Elastic Compute Cloud - Compute"),
            'rdsRecommendations': self.__get_ri_recommendation_by_service("Amazon Relational Database Service"),
            'redshiftRecommendations': self.__get_ri_recommendation_by_service("Amazon Redshift"),
            'elasticSearchRecommendations': self.__get_ri_recommendation_by_service("Amazon Elasticsearch Service")
        }

    def __get_ri_recommendation_by_service(self, service_name, term='ONE_YEAR', payment_option='ALL_UPFRONT'):
        results = []
        response = self.client.\
            get_reservation_purchase_recommendation(Service=service_name, LookbackPeriodInDays='THIRTY_DAYS',
                                                    PaymentOption=payment_option, TermInYears=term)
        results.extend(response['Recommendations'])
        while 'nextToken' in response:
            next_token = response['nextToken']
            response = self.client.\
                get_reservation_purchase_recommendation(Service=service_name, LookbackPeriodInDays='THIRTY_DAYS',
                                                        PaymentOption=payment_option, TermInYears=term,
                                                        NextPageToken=next_token)
            results.extend(response['Recommendations'])
            next_token = response['nextToken'] if response.get('nextToken') else False
        return results

    def get_last_week_ri_coverage(self):
        results = []
        response = self.client.get_reservation_coverage(
            TimePeriod={
                'Start': self.last_week_start.strftime('%Y-%m-%d'),
                'End': self.last_week_end.strftime('%Y-%m-%d')
            },
            Granularity='DAILY'
        )
        results.extend(response['CoveragesByTime'])
        while 'nextToken' in response:
            next_token = response['nextToken']
            response = self.client.get_reservation_coverage(
                TimePeriod={
                    'Start': self.last_week_start.strftime('%Y-%m-%d'),
                    'End': self.last_week_end.strftime('%Y-%m-%d')
                },
                Granularity='DAILY',
                NextPageToken=next_token
            )
            results.extend(response['CoveragesByTime'])
            next_token = response['nextToken'] if response.get('nextToken') else False
        return {'weekStart': self.last_week_start.isoformat(), 'weekEnd': self.last_week_end.isoformat(),
                'weekNumber': self.last_week_start.isocalendar()[1],
                'riCoverageByDate': results, 'riCoverageDetailed': self.__get_last_week_ri_coverage_detailed(),
                'total': response['Total']}

    def __get_last_week_ri_coverage_detailed(self):
        results = []
        group_by = [{
                'Type': 'DIMENSION',
                'Key': 'PLATFORM'
            },
            {
                'Type': 'DIMENSION',
                'Key': 'LINKED_ACCOUNT'
            },
            {
                'Type': 'DIMENSION',
                'Key': 'REGION'
            },
            {
                'Type': 'DIMENSION',
                'Key': 'INSTANCE_TYPE'
            }]
        response = self.client.get_reservation_coverage(
            TimePeriod={
                'Start': self.last_week_start.strftime('%Y-%m-%d'),
                'End': self.last_week_end.strftime('%Y-%m-%d')
            },
            GroupBy=group_by
        )
        results.extend(response['CoveragesByTime'])
        while 'nextToken' in response:
            next_token = response['nextToken']
            response = self.client.get_reservation_coverage(
                TimePeriod={
                    'Start': self.last_week_start.strftime('%Y-%m-%d'),
                    'End': self.last_week_end.strftime('%Y-%m-%d')
                },
                GroupBy=group_by,
                NextPageToken=next_token
            )
        return results

    def get_savings_from_recommendations(self):
        recommendations = self.get_ri_recommendation()
        total_savings = 0
        highest_percent = 0
        for ec2 in recommendations['ec2Recommendations']:
            total_savings += int(float(ec2['RecommendationSummary']['TotalEstimatedMonthlySavingsAmount']))
            percent_saving = int(float(ec2['RecommendationSummary']['TotalEstimatedMonthlySavingsPercentage']))
            if highest_percent < percent_saving:
                highest_percent = percent_saving
        for rds in recommendations['rdsRecommendations']:
            total_savings += int(float(rds['RecommendationSummary']['TotalEstimatedMonthlySavingsAmount']))
            percent_saving = int(float(rds['RecommendationSummary']['TotalEstimatedMonthlySavingsPercentage']))
            if highest_percent < percent_saving:
                highest_percent = percent_saving
        for redshift in recommendations['redshiftRecommendations']:
            total_savings += int(float(redshift['RecommendationSummary']['TotalEstimatedMonthlySavingsAmount']))
            percent_saving = int(float(redshift['RecommendationSummary']['TotalEstimatedMonthlySavingsPercentage']))
            if highest_percent < percent_saving:
                highest_percent = percent_saving
        for elastic_search in recommendations['elasticSearchRecommendations']:
            total_savings += int(float(elastic_search['RecommendationSummary']['TotalEstimatedMonthlySavingsAmount']))
            percent_saving = int(float(elastic_search['RecommendationSummary']['TotalEstimatedMonthlySavingsPercentage']))
            if highest_percent < percent_saving:
                highest_percent = percent_saving
        return {'totalSaving': total_savings,'highestPercent': highest_percent}