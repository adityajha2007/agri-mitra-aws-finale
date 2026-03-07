"""CDK Stack: CloudWatch monitoring, dashboards, and alarms."""

from aws_cdk import (
    Duration,
    Stack,
    aws_cloudwatch as cloudwatch,
    aws_cloudwatch_actions as cw_actions,
    aws_sns as sns,
    aws_sns_subscriptions as subscriptions,
)
from constructs import Construct


class MonitoringStack(Stack):
    def __init__(
        self,
        scope: Construct,
        id: str,
        fargate_service,
        lambda_functions: dict,
        dynamodb_tables: dict,
        alarm_email: str = None,
        **kwargs
    ):
        super().__init__(scope, id, **kwargs)

        # --- SNS Topic for Alarms ---
        self.alarm_topic = sns.Topic(
            self, "AlarmTopic",
            topic_name="agri-mitra-alarms",
            display_name="Agri-Mitra System Alarms",
        )

        if alarm_email:
            self.alarm_topic.add_subscription(
                subscriptions.EmailSubscription(alarm_email)
            )

        # --- CloudWatch Dashboard ---
        dashboard = cloudwatch.Dashboard(
            self, "AgriMitraDashboard",
            dashboard_name="agri-mitra-monitoring",
        )

        # ECS Service Metrics
        ecs_cpu = cloudwatch.Metric(
            namespace="AWS/ECS",
            metric_name="CPUUtilization",
            dimensions_map={
                "ServiceName": fargate_service.service.service_name,
                "ClusterName": fargate_service.cluster.cluster_name,
            },
            statistic="Average",
            period=Duration.minutes(5),
        )

        ecs_memory = cloudwatch.Metric(
            namespace="AWS/ECS",
            metric_name="MemoryUtilization",
            dimensions_map={
                "ServiceName": fargate_service.service.service_name,
                "ClusterName": fargate_service.cluster.cluster_name,
            },
            statistic="Average",
            period=Duration.minutes(5),
        )

        # ALB Metrics
        alb_requests = cloudwatch.Metric(
            namespace="AWS/ApplicationELB",
            metric_name="RequestCount",
            dimensions_map={
                "LoadBalancer": fargate_service.load_balancer.load_balancer_full_name,
            },
            statistic="Sum",
            period=Duration.minutes(5),
        )

        alb_target_response_time = cloudwatch.Metric(
            namespace="AWS/ApplicationELB",
            metric_name="TargetResponseTime",
            dimensions_map={
                "LoadBalancer": fargate_service.load_balancer.load_balancer_full_name,
            },
            statistic="Average",
            period=Duration.minutes(5),
        )

        alb_5xx = cloudwatch.Metric(
            namespace="AWS/ApplicationELB",
            metric_name="HTTPCode_Target_5XX_Count",
            dimensions_map={
                "LoadBalancer": fargate_service.load_balancer.load_balancer_full_name,
            },
            statistic="Sum",
            period=Duration.minutes(5),
        )

        # Add widgets to dashboard
        dashboard.add_widgets(
            cloudwatch.GraphWidget(
                title="ECS Service - CPU & Memory",
                left=[ecs_cpu],
                right=[ecs_memory],
                width=12,
            ),
            cloudwatch.GraphWidget(
                title="ALB - Request Count",
                left=[alb_requests],
                width=12,
            ),
        )

        dashboard.add_widgets(
            cloudwatch.GraphWidget(
                title="ALB - Response Time",
                left=[alb_target_response_time],
                width=12,
            ),
            cloudwatch.GraphWidget(
                title="ALB - 5XX Errors",
                left=[alb_5xx],
                width=12,
            ),
        )

        # Lambda metrics
        lambda_widgets = []
        for name, func in lambda_functions.items():
            lambda_errors = func.metric_errors(
                statistic="Sum",
                period=Duration.minutes(5),
            )
            lambda_duration = func.metric_duration(
                statistic="Average",
                period=Duration.minutes(5),
            )
            lambda_widgets.append(
                cloudwatch.GraphWidget(
                    title=f"Lambda - {name}",
                    left=[lambda_errors],
                    right=[lambda_duration],
                    width=8,
                )
            )

        if lambda_widgets:
            dashboard.add_widgets(*lambda_widgets)

        # DynamoDB metrics
        dynamodb_widgets = []
        for name, table in dynamodb_tables.items():
            read_capacity = table.metric_consumed_read_capacity_units(
                statistic="Sum",
                period=Duration.minutes(5),
            )
            write_capacity = table.metric_consumed_write_capacity_units(
                statistic="Sum",
                period=Duration.minutes(5),
            )
            dynamodb_widgets.append(
                cloudwatch.GraphWidget(
                    title=f"DynamoDB - {name}",
                    left=[read_capacity],
                    right=[write_capacity],
                    width=8,
                )
            )

        if dynamodb_widgets:
            dashboard.add_widgets(*dynamodb_widgets)

        # --- Alarms ---

        # High CPU alarm
        cpu_alarm = cloudwatch.Alarm(
            self, "HighCPUAlarm",
            alarm_name="agri-mitra-high-cpu",
            metric=ecs_cpu,
            threshold=80,
            evaluation_periods=2,
            datapoints_to_alarm=2,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING,
        )
        cpu_alarm.add_alarm_action(cw_actions.SnsAction(self.alarm_topic))

        # High memory alarm
        memory_alarm = cloudwatch.Alarm(
            self, "HighMemoryAlarm",
            alarm_name="agri-mitra-high-memory",
            metric=ecs_memory,
            threshold=80,
            evaluation_periods=2,
            datapoints_to_alarm=2,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING,
        )
        memory_alarm.add_alarm_action(cw_actions.SnsAction(self.alarm_topic))

        # High response time alarm
        response_time_alarm = cloudwatch.Alarm(
            self, "HighResponseTimeAlarm",
            alarm_name="agri-mitra-high-response-time",
            metric=alb_target_response_time,
            threshold=5,  # 5 seconds
            evaluation_periods=2,
            datapoints_to_alarm=2,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING,
        )
        response_time_alarm.add_alarm_action(cw_actions.SnsAction(self.alarm_topic))

        # 5XX errors alarm
        error_alarm = cloudwatch.Alarm(
            self, "High5XXErrorsAlarm",
            alarm_name="agri-mitra-high-5xx-errors",
            metric=alb_5xx,
            threshold=10,
            evaluation_periods=1,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING,
        )
        error_alarm.add_alarm_action(cw_actions.SnsAction(self.alarm_topic))

        # Lambda error alarms
        for name, func in lambda_functions.items():
            lambda_error_alarm = cloudwatch.Alarm(
                self, f"{name}ErrorAlarm",
                alarm_name=f"agri-mitra-lambda-{name}-errors",
                metric=func.metric_errors(
                    statistic="Sum",
                    period=Duration.minutes(5),
                ),
                threshold=5,
                evaluation_periods=1,
                comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
                treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING,
            )
            lambda_error_alarm.add_alarm_action(cw_actions.SnsAction(self.alarm_topic))
