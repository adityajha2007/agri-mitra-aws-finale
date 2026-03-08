"""CDK Stack: AWS WAF, Secrets Manager, and security configurations."""

from aws_cdk import (
    Stack,
    aws_secretsmanager as secretsmanager,
    aws_wafv2 as wafv2,
)
from constructs import Construct


class SecurityStack(Stack):
    def __init__(self, scope: Construct, id: str, **kwargs):
        super().__init__(scope, id, **kwargs)

        # --- Secrets Manager for API Keys ---

        self.openweather_secret = secretsmanager.Secret(
            self, "OpenWeatherAPIKey",
            secret_name="agri-mitra/openweather-api-key",
            description="OpenWeatherMap API key for weather data",
            generate_secret_string=secretsmanager.SecretStringGenerator(
                secret_string_template='{"api_key": ""}',
                generate_string_key="placeholder",
            ),
        )

        self.news_api_secret = secretsmanager.Secret(
            self, "NewsAPIKey",
            secret_name="agri-mitra/news-api-key",
            description="News API key for agricultural news",
            generate_secret_string=secretsmanager.SecretStringGenerator(
                secret_string_template='{"api_key": ""}',
                generate_string_key="placeholder",
            ),
        )

        self.data_gov_secret = secretsmanager.Secret(
            self, "DataGovAPIKey",
            secret_name="agri-mitra/data-gov-api-key",
            description="data.gov.in API key for mandi prices",
            generate_secret_string=secretsmanager.SecretStringGenerator(
                secret_string_template='{"api_key": ""}',
                generate_string_key="placeholder",
            ),
        )

        self.twilio_secret = secretsmanager.Secret(
            self, "TwilioWebhookCredentials",
            secret_name="agri-mitra/twilio-credentials",
            description="Twilio SID and Auth Token for WhatsApp Webhook media fetching",
            generate_secret_string=secretsmanager.SecretStringGenerator(
                secret_string_template='{"TWILIO_ACCOUNT_SID": "", "TWILIO_AUTH_TOKEN": ""}',
                generate_string_key="placeholder",
            ),
        )

        # --- A W S WAF Web ACL ---

        self.web_acl = wafv2.CfnWebACL(
            self, "AgriMitraWebACL",
            scope="REGIONAL",
            default_action=wafv2.CfnWebACL.DefaultActionProperty(allow={}),
            visibility_config=wafv2.CfnWebACL.VisibilityConfigProperty(
                cloud_watch_metrics_enabled=True,
                metric_name="agri-mitra-waf",
                sampled_requests_enabled=True,
            ),
            name="agri-mitra-web-acl",
            rules=[
                # Rate limiting rule - max 2000 requests per 5 minutes per IP
                wafv2.CfnWebACL.RuleProperty(
                    name="RateLimitRule",
                    priority=1,
                    statement=wafv2.CfnWebACL.StatementProperty(
                        rate_based_statement=wafv2.CfnWebACL.RateBasedStatementProperty(
                            limit=2000,
                            aggregate_key_type="IP",
                        )
                    ),
                    action=wafv2.CfnWebACL.RuleActionProperty(
                        block=wafv2.CfnWebACL.BlockActionProperty(
                            custom_response=wafv2.CfnWebACL.CustomResponseProperty(
                                response_code=429,
                            )
                        )
                    ),
                    visibility_config=wafv2.CfnWebACL.VisibilityConfigProperty(
                        cloud_watch_metrics_enabled=True,
                        metric_name="RateLimitRule",
                        sampled_requests_enabled=True,
                    ),
                ),
                # AWS Managed Rules - Core Rule Set
                wafv2.CfnWebACL.RuleProperty(
                    name="AWSManagedRulesCommonRuleSet",
                    priority=2,
                    statement=wafv2.CfnWebACL.StatementProperty(
                        managed_rule_group_statement=wafv2.CfnWebACL.ManagedRuleGroupStatementProperty(
                            vendor_name="AWS",
                            name="AWSManagedRulesCommonRuleSet",
                        )
                    ),
                    override_action=wafv2.CfnWebACL.OverrideActionProperty(none={}),
                    visibility_config=wafv2.CfnWebACL.VisibilityConfigProperty(
                        cloud_watch_metrics_enabled=True,
                        metric_name="AWSManagedRulesCommonRuleSet",
                        sampled_requests_enabled=True,
                    ),
                ),
                # AWS Managed Rules - Known Bad Inputs
                wafv2.CfnWebACL.RuleProperty(
                    name="AWSManagedRulesKnownBadInputsRuleSet",
                    priority=3,
                    statement=wafv2.CfnWebACL.StatementProperty(
                        managed_rule_group_statement=wafv2.CfnWebACL.ManagedRuleGroupStatementProperty(
                            vendor_name="AWS",
                            name="AWSManagedRulesKnownBadInputsRuleSet",
                        )
                    ),
                    override_action=wafv2.CfnWebACL.OverrideActionProperty(none={}),
                    visibility_config=wafv2.CfnWebACL.VisibilityConfigProperty(
                        cloud_watch_metrics_enabled=True,
                        metric_name="AWSManagedRulesKnownBadInputsRuleSet",
                        sampled_requests_enabled=True,
                    ),
                ),
                # Block requests with no User-Agent header
                wafv2.CfnWebACL.RuleProperty(
                    name="BlockNoUserAgent",
                    priority=4,
                    statement=wafv2.CfnWebACL.StatementProperty(
                        not_statement=wafv2.CfnWebACL.NotStatementProperty(
                            statement=wafv2.CfnWebACL.StatementProperty(
                                byte_match_statement=wafv2.CfnWebACL.ByteMatchStatementProperty(
                                    field_to_match=wafv2.CfnWebACL.FieldToMatchProperty(
                                        single_header={"Name": "user-agent"}
                                    ),
                                    positional_constraint="CONTAINS",
                                    search_string="Mozilla",
                                    text_transformations=[
                                        wafv2.CfnWebACL.TextTransformationProperty(
                                            priority=0,
                                            type="NONE",
                                        )
                                    ],
                                )
                            )
                        )
                    ),
                    action=wafv2.CfnWebACL.RuleActionProperty(
                        block=wafv2.CfnWebACL.BlockActionProperty()
                    ),
                    visibility_config=wafv2.CfnWebACL.VisibilityConfigProperty(
                        cloud_watch_metrics_enabled=True,
                        metric_name="BlockNoUserAgent",
                        sampled_requests_enabled=True,
                    ),
                ),
            ],
        )
