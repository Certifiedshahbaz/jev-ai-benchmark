"""
Curated benchmark dataset for JEV / LLM decision-quality evaluation.
Ground truth labels are manually written — NOT model-generated.
"""

BENCHMARK_DATASET = [
    # ---------------- BILLING ----------------
    {
        "id": "billing_001",
        "category": "billing",
        "message": "Why was I charged $49.99 this month? My plan is supposed to be $29.99.",
        "customer_context": {"customer": {"plan": "premium"}, "order": {}, "transactions": []},
        "expected": {"department": "billing", "refund_requested": False, "urgency": 1, "frustration": 0},
    },
    {
        "id": "billing_002",
        "category": "billing",
        "message": "I was charged twice for my order and I need the duplicate payment refunded today.",
        "customer_context": {
            "customer": {"plan": "premium", "lifetime_value": 1240},
            "order": {"id": "ORD-8821", "amount": 149.99},
            "transactions": [
                {"id": "TX-1001", "amount": 149.99, "status": "captured"},
                {"id": "TX-1002", "amount": 149.99, "status": "captured"},
            ],
            "policy": {"duplicate_payment_refund": True},
        },
        "expected": {"department": "billing", "refund_requested": True, "issue_type": "duplicate_charge", "urgency": 2},
    },
    {
        "id": "billing_003",
        "category": "billing",
        "message": "Can you send me an invoice for last month's payment? I need it for taxes.",
        "customer_context": {},
        "expected": {"department": "billing", "refund_requested": False, "urgency": 0, "frustration": 0},
    },
    {
        "id": "billing_004",
        "category": "billing",
        "message": "This is the THIRD time I've been overcharged. I want a manager to call me NOW.",
        "customer_context": {},
        "expected": {"department": "billing", "refund_requested": False, "urgency": 2, "frustration": 2, "escalation_required": True},
    },

    # ---------------- REFUND ----------------
    {
        "id": "refund_001",
        "category": "refund",
        "message": "I'd like to cancel my subscription and get a refund for this month since I barely used it.",
        "customer_context": {},
        "expected": {"department": "billing", "refund_requested": True, "urgency": 1},
    },
    {
        "id": "refund_002",
        "category": "refund",
        "message": "The product arrived damaged. I want my money back, not a replacement.",
        "customer_context": {},
        "expected": {"department": "orders", "refund_requested": True, "issue_type": "damaged_item", "urgency": 1},
        "ambiguous_multi_valid": {"department": ["orders", "billing"]},
    },
    {
        "id": "refund_003",
        "category": "refund",
        "message": "Is it possible to get a partial refund if I only use half the service credits?",
        "customer_context": {},
        "expected": {"department": "billing", "refund_requested": True, "urgency": 0, "frustration": 0},
    },

    # ---------------- DUPLICATE PAYMENT ----------------
    {
        "id": "duplicate_001",
        "category": "duplicate_payment",
        "message": "My bank statement shows two identical charges from you on the same day. Please fix this.",
        "customer_context": {
            "transactions": [
                {"id": "TX-01", "amount": 89.00, "status": "captured"},
                {"id": "TX-02", "amount": 89.00, "status": "captured"},
            ],
            "policy": {"duplicate_payment_refund": True},
        },
        "expected": {"department": "billing", "refund_requested": False, "duplicate_payment_suspected": True, "policy_allows_refund": True},
    },
    {
        "id": "duplicate_002",
        "category": "duplicate_payment",
        "message": "I think I might have accidentally clicked pay twice. Can you check if I was double charged?",
        "customer_context": {"transactions": [{"id": "TX-01", "amount": 40.00, "status": "captured"}]},
        "expected": {"department": "billing", "duplicate_payment_suspected": False, "evidence_supports_duplicate": False},
    },

    # ---------------- SHIPPING ----------------
    {
        "id": "shipping_001",
        "category": "shipping",
        "message": "Can you tell me when my order will arrive? It's been 3 days since I ordered.",
        "customer_context": {"order": {"id": "ORD-100", "status": "in_transit"}},
        "expected": {"department": "orders", "refund_requested": False, "urgency": 0, "frustration": 0},
    },
    {
        "id": "shipping_002",
        "category": "shipping",
        "message": "The tracking hasn't updated in 5 days and I need this for an event tomorrow. Please help urgently.",
        "customer_context": {},
        "expected": {"department": "orders", "urgency": 2, "frustration": 1},
    },
    {
        "id": "shipping_003",
        "category": "shipping",
        "message": "Wrong item was delivered to me. I ordered a blue jacket and got a red scarf.",
        "customer_context": {},
        "expected": {"department": "orders", "issue_type": "wrong_item", "refund_requested": False, "urgency": 1},
    },

    # ---------------- LATE DELIVERY ----------------
    {
        "id": "late_delivery_001",
        "category": "late_delivery",
        "message": "This is now 10 days late. This is completely unacceptable and I want a refund or the item shipped for free overnight.",
        "customer_context": {},
        "expected": {"department": "orders", "refund_requested": True, "urgency": 2, "frustration": 2},
    },
    {
        "id": "late_delivery_002",
        "category": "late_delivery",
        "message": "Just checking in — my package seems a little delayed, no rush though.",
        "customer_context": {},
        "expected": {"department": "orders", "urgency": 0, "frustration": 0},
    },

    # ---------------- ORDER CANCELLATION ----------------
    {
        "id": "cancellation_001",
        "category": "cancellation",
        "message": "I need to cancel order #4521 before it ships. Please confirm as soon as possible.",
        "customer_context": {"order": {"id": "ORD-4521", "status": "processing"}},
        "expected": {"department": "orders", "urgency": 1, "refund_requested": False},
    },
    {
        "id": "cancellation_002",
        "category": "cancellation",
        "message": "Please cancel my subscription effective immediately. I no longer wish to use this service.",
        "customer_context": {},
        "expected": {"department": "billing", "urgency": 1, "churn_risk": 2},
    },

    # ---------------- ACCOUNT ACCESS ----------------
    {
        "id": "account_001",
        "category": "account_access",
        "message": "I can't log into my account. It says my password is incorrect but I'm sure it's right.",
        "customer_context": {},
        "expected": {"department": "account", "urgency": 1, "sensitive_info_requested": False},
    },
    {
        "id": "account_002",
        "category": "account_access",
        "message": "My account got locked after I tried logging in from a new phone. I need this fixed today, I have work to do.",
        "customer_context": {},
        "expected": {"department": "account", "urgency": 2, "frustration": 1},
    },
    {
        "id": "account_003",
        "category": "account_access",
        "message": "Can you tell me what email address is registered on my account? I forgot.",
        "customer_context": {},
        "expected": {"department": "account", "sensitive_info_requested": True, "urgency": 0},
    },

    # ---------------- TECHNICAL BUG ----------------
    {
        "id": "technical_001",
        "category": "technical_bug",
        "message": "The app crashes every time I try to upload a photo. This happens on both my phone and laptop.",
        "customer_context": {},
        "expected": {"department": "technical", "urgency": 1, "issue_type": "bug"},
    },
    {
        "id": "technical_002",
        "category": "technical_bug",
        "message": "The checkout page just shows a blank screen. I can't complete my purchase and I've tried three times.",
        "customer_context": {},
        "expected": {"department": "technical", "urgency": 2, "frustration": 1},
    },
    {
        "id": "technical_003",
        "category": "technical_bug",
        "message": "Minor issue — the dark mode toggle sometimes doesn't save my preference. Not urgent.",
        "customer_context": {},
        "expected": {"department": "technical", "urgency": 0, "frustration": 0},
    },

    # ---------------- FEATURE REQUEST ----------------
    {
        "id": "feature_001",
        "category": "feature_request",
        "message": "It would be great if you added dark mode to the mobile app. Any plans for that?",
        "customer_context": {},
        "expected": {"department": "general", "urgency": 0, "refund_requested": False},
    },
    {
        "id": "feature_002",
        "category": "feature_request",
        "message": "Could you add an export-to-CSV button on the reports page? Would save me a lot of time.",
        "customer_context": {},
        "expected": {"department": "general", "urgency": 0},
    },

    # ---------------- SUBSCRIPTION ----------------
    {
        "id": "subscription_001",
        "category": "subscription",
        "message": "My subscription renewed automatically but I meant to cancel it last week. Can I get a refund for this cycle?",
        "customer_context": {},
        "expected": {"department": "billing", "refund_requested": True, "issue_type": "subscription_issue", "urgency": 1},
    },
    {
        "id": "subscription_002",
        "category": "subscription",
        "message": "How do I upgrade from the basic plan to premium?",
        "customer_context": {},
        "expected": {"department": "billing", "refund_requested": False, "urgency": 0, "frustration": 0},
    },

    # ---------------- FRAUD / SECURITY ----------------
    {
        "id": "fraud_001",
        "category": "fraud_security",
        "message": "I see a charge on my card I don't recognize at all. I think my account has been compromised.",
        "customer_context": {},
        "expected": {"department": "account", "escalation_required": True, "urgency": 2, "sensitive_info_requested": False},
        "ambiguous_multi_valid": {"department": ["account", "billing"]},
    },
    {
        "id": "fraud_002",
        "category": "fraud_security",
        "message": "Someone logged into my account from a country I've never visited. Please secure my account immediately.",
        "customer_context": {},
        "expected": {"department": "account", "escalation_required": True, "urgency": 2},
    },

    # ---------------- COMPLAINT ----------------
    {
        "id": "complaint_001",
        "category": "complaint",
        "message": "Your customer service has been absolutely terrible. I've called three times and no one has helped me.",
        "customer_context": {},
        "expected": {"department": "general", "frustration": 2, "escalation_required": True},
    },
    {
        "id": "complaint_002",
        "category": "complaint",
        "message": "I'm disappointed with the quality of the product compared to what was advertised.",
        "customer_context": {},
        "expected": {"department": "orders", "frustration": 1, "refund_requested": False},
        "ambiguous_multi_valid": {"department": ["orders", "general"]},
    },

    # ---------------- CHURN RISK ----------------
    {
        "id": "churn_001",
        "category": "churn_risk",
        "message": "I've been a customer for 3 years but honestly I'm considering switching to a competitor after this experience.",
        "customer_context": {"customer": {"lifetime_value": 3200}},
        "expected": {"churn_risk": 2, "escalation_required": True, "frustration": 1},
    },
    {
        "id": "churn_002",
        "category": "churn_risk",
        "message": "Just wanted to say I've really enjoyed using your service this year, quick question about billing dates.",
        "customer_context": {},
        "expected": {"churn_risk": 0, "frustration": 0, "department": "billing"},
    },

    # ---------------- GENERAL INFORMATION ----------------
    {
        "id": "general_001",
        "category": "general",
        "message": "What are your customer support hours?",
        "customer_context": {},
        "expected": {"department": "general", "urgency": 0, "refund_requested": False},
    },
    {
        "id": "general_002",
        "category": "general",
        "message": "Do you ship internationally to Canada?",
        "customer_context": {},
        "expected": {"department": "orders", "urgency": 0},
    },

    # ---------------- AMBIGUOUS / MULTI-INTENT ----------------
    {
        "id": "ambiguous_001",
        "category": "multi_intent",
        "message": "My order is late AND I was overcharged. Also can you tell me if you have a loyalty program?",
        "customer_context": {},
        "expected": {"department": "orders", "refund_requested": False, "urgency": 1},
        "ambiguous_multi_valid": {"department": ["orders", "billing"]},
    },
    {
        "id": "ambiguous_002",
        "category": "multi_intent",
        "message": "I'm not sure if this is a billing issue or a technical one, but my payment failed even though the app said it succeeded.",
        "customer_context": {},
        "expected": {"department": "billing", "issue_type": "bug", "urgency": 1},
        "ambiguous_multi_valid": {"department": ["billing", "technical"]},
    },

    # ---------------- NOISY / TYPOS ----------------
    {
        "id": "noisy_001",
        "category": "noisy",
        "message": "hey i got chrged twise for teh same order pls refund asap thnx",
        "customer_context": {},
        "expected": {"department": "billing", "refund_requested": True, "urgency": 2},
    },
    {
        "id": "noisy_002",
        "category": "noisy",
        "message": "wat is my acount balance i cant chek it on teh app",
        "customer_context": {},
        "expected": {"department": "billing", "urgency": 0},
        "ambiguous_multi_valid": {"department": ["billing", "technical"]},
    },

    # ---------------- CONTRADICTORY CONTEXT ----------------
    {
        "id": "contradictory_001",
        "category": "contradictory",
        "message": "I was charged twice, please refund one of them.",
        "customer_context": {
            "transactions": [{"id": "TX-01", "amount": 20.00, "status": "captured"}],
            "policy": {"duplicate_payment_refund": True},
        },
        "expected": {"department": "billing", "refund_requested": True, "evidence_supports_duplicate": False},
    },
    {
        "id": "contradictory_002",
        "category": "contradictory",
        "message": "I need an urgent refund today.",
        "customer_context": {"policy": {"duplicate_payment_refund": False}},
        "expected": {"department": "billing", "refund_requested": True, "urgency": 2, "policy_allows_refund": False},
    },

    # ---------------- LONG MESSAGES ----------------
    {
        "id": "long_001",
        "category": "long",
        "message": (
            "Hi, I hope you're doing well. I've been a customer for a while now and generally "
            "I've had a good experience, but this time something went wrong. I placed an order "
            "last Tuesday, and according to the tracking it should have arrived by Friday, but "
            "it is now Wednesday and I still haven't received anything. I checked the tracking "
            "page multiple times and it hasn't updated since Tuesday evening. I have already "
            "reached out once through chat but didn't get a clear answer about when it will "
            "arrive. Could you please look into this and either get it moving quickly or "
            "process a refund? I need this resolved soon since I was planning to use the item "
            "this weekend."
        ),
        "customer_context": {},
        "expected": {"department": "orders", "refund_requested": True, "urgency": 1, "frustration": 1},
    },

    # ---------------- SHORT MESSAGES ----------------
    {
        "id": "short_001",
        "category": "short",
        "message": "refund now",
        "customer_context": {},
        "expected": {"department": "billing", "refund_requested": True, "urgency": 1},
    },
    {
        "id": "short_002",
        "category": "short",
        "message": "where's my order",
        "customer_context": {},
        "expected": {"department": "orders", "urgency": 0},
    },

    # ---------------- EMOTIONALLY CHARGED ----------------
    {
        "id": "emotional_001",
        "category": "emotional",
        "message": "I am absolutely furious. This is the worst experience I've ever had with any company. Fix this NOW or I'm never buying from you again.",
        "customer_context": {},
        "expected": {"frustration": 2, "escalation_required": True, "churn_risk": 2},
    },
    {
        "id": "emotional_002",
        "category": "emotional",
        "message": "I'm really sorry to bother you, I know you're probably busy, but I had a small question about my order whenever you get a chance, no rush at all!",
        "customer_context": {},
        "expected": {"frustration": 0, "urgency": 0},
    },

    # ---------------- IRRELEVANT INFO PADDING ----------------
    {
        "id": "padding_001",
        "category": "irrelevant_padding",
        "message": (
            "So I was at the grocery store earlier and then I remembered I needed to message you. "
            "Anyway, my package hasn't arrived and it was supposed to be here two days ago."
        ),
        "customer_context": {},
        "expected": {"department": "orders", "urgency": 1},
    },
    {
        "id": "padding_002",
        "category": "irrelevant_padding",
        "message": "Quick one — by the way I love your new logo, but also I was charged $15 twice this week, can you check?",
        "customer_context": {},
        "expected": {"department": "billing", "refund_requested": False},
    },

    # ---------------- OBVIOUS CASES ----------------
    {
        "id": "obvious_001",
        "category": "obvious",
        "message": "I want a full refund for order #7789, it was the wrong size.",
        "customer_context": {},
        "expected": {"department": "orders", "refund_requested": True, "issue_type": "wrong_item"},
        "ambiguous_multi_valid": {"department": ["orders", "billing"]},
    },
    {
        "id": "obvious_002",
        "category": "obvious",
        "message": "How do I reset my password?",
        "customer_context": {},
        "expected": {"department": "account", "urgency": 0, "frustration": 0},
    },
]

# Convenience: dataset stats
def dataset_summary():
    categories = {}
    for case in BENCHMARK_DATASET:
        categories[case["category"]] = categories.get(case["category"], 0) + 1
    return {"total_cases": len(BENCHMARK_DATASET), "by_category": categories}