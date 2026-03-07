"""CDK Stack: CloudFront distribution for global content delivery."""

from aws_cdk import (
    Duration,
    Stack,
    aws_cloudfront as cloudfront,
    aws_cloudfront_origins as origins,
    aws_s3 as s3,
    aws_certificatemanager as acm,
)
from constructs import Construct


class CdnStack(Stack):
    def __init__(
        self,
        scope: Construct,
        id: str,
        api_domain: str,
        certificate_arn: str = None,
        custom_domain: str = None,
        **kwargs
    ):
        super().__init__(scope, id, **kwargs)

        # --- CloudFront Distribution ---

        # Cache policy for API responses
        api_cache_policy = cloudfront.CachePolicy(
            self, "ApiCachePolicy",
            cache_policy_name="agri-mitra-api-cache",
            comment="Cache policy for Agri-Mitra API",
            default_ttl=Duration.seconds(0),  # No caching for dynamic API
            min_ttl=Duration.seconds(0),
            max_ttl=Duration.seconds(1),
            cookie_behavior=cloudfront.CacheCookieBehavior.all(),
            header_behavior=cloudfront.CacheHeaderBehavior.allow_list(
                "Authorization",
                "Content-Type",
                "Accept",
            ),
            query_string_behavior=cloudfront.CacheQueryStringBehavior.all(),
            enable_accept_encoding_gzip=True,
            enable_accept_encoding_brotli=True,
        )

        # Origin request policy
        origin_request_policy = cloudfront.OriginRequestPolicy(
            self, "ApiOriginRequestPolicy",
            origin_request_policy_name="agri-mitra-api-origin",
            comment="Origin request policy for Agri-Mitra API",
            cookie_behavior=cloudfront.OriginRequestCookieBehavior.all(),
            header_behavior=cloudfront.OriginRequestHeaderBehavior.all_viewer(),
            query_string_behavior=cloudfront.OriginRequestQueryStringBehavior.all(),
        )

        # Response headers policy for security
        response_headers_policy = cloudfront.ResponseHeadersPolicy(
            self, "SecurityHeadersPolicy",
            response_headers_policy_name="agri-mitra-security-headers",
            comment="Security headers for Agri-Mitra",
            security_headers_behavior=cloudfront.ResponseSecurityHeadersBehavior(
                strict_transport_security=cloudfront.ResponseHeadersStrictTransportSecurity(
                    access_control_max_age=Duration.days(365),
                    include_subdomains=True,
                    override=True,
                ),
                content_type_options=cloudfront.ResponseHeadersContentTypeOptions(
                    override=True,
                ),
                frame_options=cloudfront.ResponseHeadersFrameOptions(
                    frame_option=cloudfront.HeadersFrameOption.DENY,
                    override=True,
                ),
                xss_protection=cloudfront.ResponseHeadersXSSProtection(
                    protection=True,
                    mode_block=True,
                    override=True,
                ),
                referrer_policy=cloudfront.ResponseHeadersReferrerPolicy(
                    referrer_policy=cloudfront.HeadersReferrerPolicy.STRICT_ORIGIN_WHEN_CROSS_ORIGIN,
                    override=True,
                ),
            ),
            cors_behavior=cloudfront.ResponseHeadersCorsConfig(
                access_control_allow_origins=["*"],  # Update with your frontend domain
                access_control_allow_methods=["GET", "POST", "OPTIONS"],
                access_control_allow_headers=["*"],
                access_control_allow_credentials=False,
                origin_override=True,
            ),
        )

        # CloudFront distribution
        distribution_props = {
            "comment": "Agri-Mitra API CDN",
            "default_behavior": cloudfront.BehaviorOptions(
                origin=origins.HttpOrigin(
                    api_domain,
                    protocol_policy=cloudfront.OriginProtocolPolicy.HTTPS_ONLY,
                ),
                cache_policy=api_cache_policy,
                origin_request_policy=origin_request_policy,
                response_headers_policy=response_headers_policy,
                allowed_methods=cloudfront.AllowedMethods.ALLOW_ALL,
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                compress=True,
            ),
            "enable_logging": True,
            "log_includes_cookies": True,
            "price_class": cloudfront.PriceClass.PRICE_CLASS_200,  # US, Europe, Asia, Middle East, Africa
            "geo_restriction": cloudfront.GeoRestriction.allowlist("IN"),  # India only
        }

        # Add custom domain if provided
        if certificate_arn and custom_domain:
            certificate = acm.Certificate.from_certificate_arn(
                self, "Certificate",
                certificate_arn,
            )
            distribution_props["certificate"] = certificate
            distribution_props["domain_names"] = [custom_domain]

        self.distribution = cloudfront.Distribution(
            self, "AgriMitraDistribution",
            **distribution_props,
        )

        # --- Outputs ---
        self.distribution_domain = self.distribution.distribution_domain_name
