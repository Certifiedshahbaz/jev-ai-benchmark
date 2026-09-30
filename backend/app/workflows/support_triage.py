from typing import Dict, Any
from typesafe_sdk import Choice, Noul, Score

# =============================================================================
# MODE A — 5 Questions (Core Triage)
# =============================================================================
QUESTIONS_MODE_A: Dict[str, Any] = {
    "department": Choice(
        instructions="Which team should handle this customer request?",
        criteria={
            "billing": "Payments, charges, refunds, invoicing, subscription billing",
            "orders": "Order status, shipping, package tracking, delivery delays",
            "technical": "Bugs, site errors, technical glitches, broken features",
            "account": "Login, password reset, profile, account access, permissions",
            "general": "General inquiries, feedback, other non-urgent questions",
        },
    ),
    "refund_requested": Noul(
        instructions="Does the customer explicitly request a refund, money back, or account credit?",
    ),
    "urgency": Score(
        instructions="How time-sensitive is this customer request?",
        criteria=["No deadline / relaxed", "Within a few days", "Today or immediate attention required"],
    ),
    "frustration": Score(
        instructions="How frustrated or angry does the customer appear in their message?",
        criteria=["Calm, polite, matter-of-fact", "Frustrated but civil", "Very angry, threat of escalation, aggressive tone"],
    ),
    "escalation_required": Noul(
        instructions="Is this request complex, high-risk, or sensitive enough that a human agent should handle it instead of automated self-service?",
    ),
}

# =============================================================================
# MODE B — 15 Questions (Standard Triage)
# =============================================================================
QUESTIONS_MODE_B: Dict[str, Any] = {
    **QUESTIONS_MODE_A,
    "intent": Choice(
        instructions="What is the primary action or goal of the customer?",
        criteria={
            "billing_inquiry": "Asking about charges, invoices, or payment methods",
            "order_tracking": "Checking order delivery or package tracking",
            "technical_support": "Reporting an app, web, or service defect",
            "account_management": "Updating profile, credentials, or security",
            "refund_claim": "Requesting money back or transaction cancellation",
            "complaint": "Expressing dissatisfaction with service or policy",
        },
    ),
    "issue_type": Choice(
        instructions="Which specific category best describes the issue?",
        criteria={
            "duplicate_charge": "Customer charged more than once for same order",
            "late_package": "Shipment delayed beyond promised delivery date",
            "site_error": "UI error, HTTP 500, crash, or broken button",
            "login_failure": "Unable to sign in or 2FA issue",
            "general_question": "Informational or feedback inquiry",
            "damaged_item": "Product arrived broken, defective, or physically damaged",
            "wrong_item": "Delivered product variant, size, or color differs from order",
            "bug": "Software malfunction, crash, or unintended technical glitch",
            "subscription_issue": "Recurring plan renewal, auto-charge, or tier dispute",
        },
    ),
    "duplicate_payment_suspected": Noul(
        instructions="Is there indication or suspicion of a duplicate payment/transaction?",
    ),
    "sensitive_info_requested": Noul(
        instructions="Does the customer mention sensitive account details (SSN, full card number, security pin)?",
    ),
    "order_mentioned": Noul(
        instructions="Does the message reference an order ID, purchase, or product package?",
    ),
    "policy_allows_refund": Noul(
        instructions="Based on context and typical policy, is this type of request eligible for a refund?",
    ),
    "evidence_supports_duplicate": Noul(
        instructions="Do the provided transaction records or details support a duplicate charge?",
    ),
    "churn_risk": Score(
        instructions="What is the likelihood this customer will cancel their service or stop buying?",
        criteria=["Low risk / loyal customer", "Moderate risk / evaluating alternatives", "High risk / threatening to leave"],
    ),
    "customer_priority": Score(
        instructions="What priority tier should be assigned to this ticket?",
        criteria=["Low priority", "Medium priority", "High priority"],
    ),
    "human_review_required": Noul(
        instructions="Does policy mandate human review before resolution?",
    ),
}

# =============================================================================
# MODE C — 25 Questions (Extended Triage)
# =============================================================================
QUESTIONS_MODE_C: Dict[str, Any] = {
    **QUESTIONS_MODE_B,
    "account_security_concern": Noul(
        instructions="Is there an indication of account takeover, unauthorized login, or credential leak?",
    ),
    "subscription_issue": Noul(
        instructions="Is the inquiry about plan upgrades, downgrades, auto-renewal, or subscription cancellation?",
    ),
    "complaint_severity": Score(
        instructions="How severe is the customer's complaint regarding service quality?",
        criteria=["Minor inconvenience", "Significant operational disruption", "Severe breach of trust / business critical"],
    ),
    "response_tone_recommendation": Choice(
        instructions="What tone should the support response adopt?",
        criteria={
            "empathetic": "Warm, understanding, acknowledging distress",
            "technical": "Direct, step-by-step, instruction-focused",
            "formal": "Professional, policy-aligned, official",
            "apologetic": "Sincere apology for service failure",
            "direct": "Concise, factual answer without filler",
        },
    ),
    "cross_sell_opportunity": Noul(
        instructions="Is there an appropriate opportunity to recommend an upgraded plan or product add-on?",
    ),
    "language_complexity": Score(
        instructions="How complex is the language or technical jargon used by the customer?",
        criteria=["Simple, clear prose", "Moderate domain terminology", "Highly complex or technical language"],
    ),
    "resolution_timeframe": Choice(
        instructions="What target resolution window is appropriate?",
        criteria={
            "immediate": "Needs resolution within 1 hour",
            "same_day": "Needs resolution within 24 hours",
            "within_48h": "Standard 48-hour response window",
            "normal_queue": "Low-priority backlog queue",
        },
    ),
    "previous_contact_referenced": Noul(
        instructions="Does the customer mention contacting support previously about this issue?",
    ),
    "emotional_state": Choice(
        instructions="Which primary emotional state is expressed?",
        criteria={
            "calm": "Neutrally stating facts",
            "anxious": "Worried about money, data, or time",
            "frustrated": "Annoyed by delay or poor service",
            "angry": "Hostile, demanding immediate action",
            "satisfied": "Praising service or confirming fix",
        },
    ),
    "data_privacy_concern": Noul(
        instructions="Does the request involve GDPR, CCPA, data deletion, or privacy settings?",
    ),
}

# Helper to generate Mode D (50 questions)
def _build_mode_d() -> Dict[str, Any]:
    base = dict(QUESTIONS_MODE_C)
    mode_d_additions = {
        "sla_breach_risk": Noul(instructions="Is this ticket at risk of breaching customer SLA deadlines?"),
        "technical_severity": Score(instructions="Rate technical severity", criteria=["Low / non-blocking", "Medium / partial workaround", "High / service outage"]),
        "payment_method_issue": Noul(instructions="Is the card expired, declined, or unsupported?"),
        "escalation_tier": Choice(instructions="Select target escalation level", criteria={
            "tier1": "General support agent",
            "tier2": "Senior specialist",
            "management": "Team lead or manager",
            "legal": "Legal / compliance department",
            "vip_concierge": "Dedicated account manager",
        }),
        "knowledge_base_relevant": Noul(instructions="Can this issue be answered with a standard FAQ or KB article?"),
        "customer_loyalty_tier": Choice(instructions="Estimate customer loyalty tier from context", criteria={
            "bronze": "Standard user",
            "silver": "Repeat buyer",
            "gold": "High LTV customer",
            "platinum": "Key enterprise stakeholder",
        }),
        "seasonal_holiday_context": Noul(instructions="Does the request mention holiday deadlines, Black Friday, or time-sensitive events?"),
        "bug_reproducibility": Choice(instructions="Can the reported technical bug be reproduced easily?", criteria={
            "always": "Consistently reproducible",
            "intermittent": "Happens occasionally",
            "single_user": "Isolated to single user environment",
            "unknown": "Not enough detail",
        }),
        "browser_device_mentioned": Noul(instructions="Does the message specify operating system, browser, or mobile device details?"),
        "shipping_carrier_delay": Noul(instructions="Is the delay caused by third-party delivery carriers (FedEx, UPS, DHL)?"),
        "address_change_requested": Noul(instructions="Is the customer requesting to change the shipping or billing address?"),
        "promo_code_issue": Noul(instructions="Is there a problem applying a discount code or coupon?"),
        "cancellation_request": Noul(instructions="Is the customer asking to cancel an active order or subscription?"),
        "legal_threat_mentioned": Noul(instructions="Does the customer mention lawyers, lawsuits, or regulatory reports?"),
        "social_media_escalation_risk": Noul(instructions="Is the customer threatening to post complaints publicly on social media?"),
        "partial_refund_acceptable": Noul(instructions="Would a partial credit or discount resolve the customer complaint?"),
        "replacement_item_requested": Noul(instructions="Is the customer asking for a replacement product instead of a cash refund?"),
        "third_party_vendor_involved": Noul(instructions="Does resolving this require contacting an external vendor or partner?"),
        "billing_currency_mismatch": Noul(instructions="Is there an error related to currency conversion or foreign exchange fee?"),
        "authorization_failed": Noul(instructions="Did bank credit card authorization fail during checkout?"),
        "password_reset_blocked": Noul(instructions="Is the user unable to receive password reset emails?"),
        "two_factor_lost": Noul(instructions="Has the customer lost access to 2FA authenticator device?"),
        "api_key_compromised": Noul(instructions="Is there a report of leaked API credentials or security keys?"),
        "feature_deprecation_complaint": Noul(instructions="Is the user complaining about a retired product feature?"),
        "contract_renewal_impacted": Noul(instructions="Does this issue threaten an upcoming enterprise contract renewal?"),
    }
    base.update(mode_d_additions)
    return base

QUESTIONS_MODE_D: Dict[str, Any] = _build_mode_d()

# Helper to generate Mode E (100 questions)
def _build_mode_e() -> Dict[str, Any]:
    base = dict(QUESTIONS_MODE_D)
    mode_e_additions = {
        f"sub_category_{i}": Noul(instructions=f"Is domain facet #{i} applicable to this support ticket?")
        for i in range(1, 26)
    }
    # Add 25 specific domain questions to reach exactly 100
    specific_facet_additions = {
        "invoice_pdf_requested": Noul(instructions="Does the customer request an official tax invoice or PDF receipt?"),
        "tax_exemption_claimed": Noul(instructions="Is the customer claiming non-profit or B2B tax exemption status?"),
        "chargeback_threatened": Noul(instructions="Is the customer threatening a credit card chargeback with their bank?"),
        "gift_card_redemption_error": Noul(instructions="Is there an error redeeming a gift card balance?"),
        "damaged_goods_reported": Noul(instructions="Did the item arrive physically damaged or broken?"),
        "wrong_item_shipped": Noul(instructions="Did the warehouse send the wrong product variant or size?"),
        "stolen_package_claimed": Noul(instructions="Does tracking show delivered but customer claims package was stolen?"),
        "customs_duty_dispute": Noul(instructions="Is there an international customs duty or import tariff dispute?"),
        "express_shipping_refund_asked": Noul(instructions="Is the user requesting a refund specifically for priority shipping fee?"),
        "pre_order_delay_inquiry": Noul(instructions="Is the inquiry about a back-ordered or pre-order item launch date?"),
        "api_rate_limit_exceeded": Noul(instructions="Is developer complaining about HTTP 429 API rate limiting?"),
        "data_export_requested": Noul(instructions="Is user asking to export account data in CSV or JSON format?"),
        "account_merge_requested": Noul(instructions="Is customer asking to merge two separate user accounts?"),
        "email_change_requested": Noul(instructions="Is user requesting to transfer account ownership to a new email address?"),
        "mobile_app_crash": Noul(instructions="Is the crash occurring on iOS or Android native mobile application?"),
        "web_browser_extension_conflict": Noul(instructions="Is an ad-blocker or extension causing page rendering failures?"),
        "sso_saml_integration_error": Noul(instructions="Is enterprise Single Sign-On (SAML/Okta) authentication failing?"),
        "webhook_delivery_failure": Noul(instructions="Are event notification webhooks failing to reach customer endpoint?"),
        "domain_verification_pending": Noul(instructions="Is custom domain DNS verification failing or pending?"),
        "ssl_certificate_expired": Noul(instructions="Is user reporting an invalid SSL/TLS security certificate warning?"),
        "multi_tenant_isolation_inquiry": Noul(instructions="Is enterprise client asking about data isolation security guarantees?"),
        "audit_log_requested": Noul(instructions="Is admin requesting access security audit trail logs?"),
        "maintenance_window_disruption": Noul(instructions="Was customer impacted by scheduled maintenance downtime?"),
        "beta_feature_opt_in": Noul(instructions="Is user requesting early access to experimental beta features?"),
        "affiliate_commission_payout": Noul(instructions="Is inquiry about affiliate partner commission payment status?"),
    }
    base.update(mode_e_additions)
    base.update(specific_facet_additions)
    return base

QUESTIONS_MODE_E: Dict[str, Any] = _build_mode_e()


def get_questions_for_mode(mode: str = "A") -> Dict[str, Any]:
    """
    Return question dictionary for the given mode:
    - Mode A: 5 questions
    - Mode B: 15 questions
    - Mode C: 25 questions
    - Mode D: 50 questions
    - Mode E: 100 questions
    """
    m = mode.upper().strip()
    if m == "A":
        return QUESTIONS_MODE_A
    elif m == "B":
        return QUESTIONS_MODE_B
    elif m == "C":
        return QUESTIONS_MODE_C
    elif m == "D":
        return QUESTIONS_MODE_D
    elif m == "E":
        return QUESTIONS_MODE_E
    else:
        # Default to Mode A if unknown mode passed
        return QUESTIONS_MODE_A
