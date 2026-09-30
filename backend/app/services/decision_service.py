from typing import Dict, Any, List
from pydantic import BaseModel

class RoutingDecision(BaseModel):
    team: str
    priority: str
    action: str
    reason: str
    confidence_factors: Dict[str, Any]
    relevant_answers: Dict[str, Any]
    ignored_answers: List[str]

class DecisionService:
    """
    Deterministic Python Routing Engine.
    JEV produces speculative independent answers.
    Python code alone decides the final workflow route and action.
    """

    def route_ticket(self, answers: Dict[str, Any], customer_context: Dict[str, Any]) -> RoutingDecision:
        relevant: Dict[str, Any] = {}
        ignored: List[str] = []

        # Helper getters
        def get_val(key: str, default=None):
            ans = answers.get(key)
            if not ans:
                return default
            if isinstance(ans, dict):
                return ans.get("choice") or ans.get("noul") or ans.get("score") or default
            return getattr(ans, "choice", getattr(ans, "noul", getattr(ans, "score", default)))

        department = get_val("department", "general")
        escalation_prob = float(get_val("escalation_required", 0.0) or 0.0)
        refund_prob = float(get_val("refund_requested", 0.0) or 0.0)
        dup_payment_prob = float(get_val("duplicate_payment_suspected", 0.0) or 0.0)
        policy_allows_prob = float(get_val("policy_allows_refund", 0.0) or 0.0)
        evidence_dup_prob = float(get_val("evidence_supports_duplicate", 0.0) or 0.0)
        frustration = float(get_val("frustration", 0.0) or 0.0)
        urgency = float(get_val("urgency", 0.0) or 0.0)
        sensitive_info = float(get_val("sensitive_info_requested", 0.0) or 0.0)

        # Context policy rules
        policy_cfg = customer_context.get("policy", {}) if isinstance(customer_context, dict) else {}
        auto_refund_allowed_by_policy = policy_cfg.get("duplicate_payment_refund", False)
        human_review_threshold = policy_cfg.get("human_review_threshold", 0.75)

        # 1. High-risk / sensitive security escalation
        if sensitive_info > 0.5:
            relevant["sensitive_info_requested"] = sensitive_info
            return RoutingDecision(
                team="security_compliance",
                priority="critical",
                action="quarantine_and_mask_pii",
                reason="Sensitive personal/financial information detected in request.",
                confidence_factors={"sensitive_info_confidence": sensitive_info},
                relevant_answers=relevant,
                ignored_answers=[k for k in answers.keys() if k not in relevant]
            )

        # 2. Urgent human escalation rule
        if escalation_prob > human_review_threshold:
            relevant["escalation_required"] = escalation_prob
            relevant["frustration"] = frustration
            return RoutingDecision(
                team="human_escalation",
                priority="urgent",
                action="assign_senior_tier2_agent",
                reason=f"Escalation probability ({escalation_prob:.2f}) exceeds policy threshold ({human_review_threshold}).",
                confidence_factors={"escalation_probability": escalation_prob},
                relevant_answers=relevant,
                ignored_answers=[k for k in answers.keys() if k not in relevant]
            )

        # 3. Billing Duplicate Payment Auto-Refund workflow
        if (department == "billing" or dup_payment_prob > 0.7) and refund_prob > 0.7:
            relevant["department"] = department
            relevant["refund_requested"] = refund_prob
            relevant["duplicate_payment_suspected"] = dup_payment_prob
            relevant["evidence_supports_duplicate"] = evidence_dup_prob
            relevant["policy_allows_refund"] = policy_allows_prob

            if (dup_payment_prob > 0.8 and evidence_dup_prob > 0.7) and (auto_refund_allowed_by_policy or policy_allows_prob > 0.8):
                return RoutingDecision(
                    team="billing_auto_refund",
                    priority="high" if urgency > 1.2 else "standard",
                    action="execute_automated_stripe_refund",
                    reason="Verified duplicate charge with corroborating transaction context and policy compliance.",
                    confidence_factors={
                        "duplicate_certainty": dup_payment_prob,
                        "evidence_certainty": evidence_dup_prob
                    },
                    relevant_answers=relevant,
                    ignored_answers=[k for k in answers.keys() if k not in relevant]
                )
            else:
                return RoutingDecision(
                    team="billing_specialists",
                    priority="high",
                    action="manual_billing_investigation",
                    reason="Refund claimed but duplicate evidence or policy requirements require agent sign-off.",
                    confidence_factors={"refund_probability": refund_prob},
                    relevant_answers=relevant,
                    ignored_answers=[k for k in answers.keys() if k not in relevant]
                )

        # 4. Standard Departmental Routing
        relevant["department"] = department
        relevant["urgency"] = urgency
        relevant["frustration"] = frustration

        priority = "urgent" if urgency > 1.5 or frustration > 1.6 else "standard"

        if department == "orders":
            action = "dispatch_warehouse_tracking_trace" if "order_tracking" == get_val("intent") else "orders_support_queue"
            team = "order_fulfillment"
        elif department == "technical":
            action = "collect_client_telemetry"
            team = "technical_support"
        elif department == "account":
            action = "trigger_identity_verification"
            team = "account_services"
        else:
            action = "triage_general_inquiry"
            team = "general_support"

        return RoutingDecision(
            team=team,
            priority=priority,
            action=action,
            reason=f"Standard routing based on classified department '{department}' with urgency {urgency:.1f}.",
            confidence_factors={"department": department},
            relevant_answers=relevant,
            ignored_answers=[k for k in answers.keys() if k not in relevant]
        )

decision_service = DecisionService()
