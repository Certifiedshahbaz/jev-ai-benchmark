from jev import call_jev
import json

message = "I was charged twice for my order and I need the duplicate payment refunded today. I'm really frustrated."

questions = {
    "department": {
        "type": "choice",
        "instructions": "Which team should handle this?",
        "criteria": {
            "billing": "Payments, charges and refunds",
            "technical": "Bugs and technical problems",
            "shipping": "Delivery and shipment problems",
            "other": "Anything else",
        },
    },
    "refund_requested": {
        "type": "noul",
        "instructions": "Does the customer request a refund?",
    },
    "urgency": {
        "type": "score",
        "instructions": "How time-sensitive is this request?",
        "criteria": ["No deadline", "Within a week", "Today or sooner"],
    },
    "frustration": {
        "type": "score",
        "instructions": "How frustrated does the customer appear in their message?",
        "criteria": [
            "Calm, matter-of-fact",
            "Frustrated but civil",
            "Very angry, strong language",
        ],
    },
    "issue_type": {
        "type": "choice",
        "instructions": "What specific type of issue is this?",
        "criteria": {
            "duplicate_charge": "Customer was billed more than once for the same order",
            "wrong_amount": "Customer was charged an incorrect amount",
            "subscription_issue": "Problem with a recurring subscription",
            "other_billing": "Any other billing-related issue",
        },
    },
    "needs_human": {
        "type": "noul",
        "instructions": "This request is complex or sensitive enough that a human agent should handle it instead of an automated system",
    },
}

def print_decision_trace(result):
    print("\nJEV Decision Trace")
    print("─" * 40)
    for question_id, answer in result["answers"].items():
        print(f"\n{question_id}")
        if answer["type"] == "choice":
            for option, prob in sorted(answer["probabilities"].items(), key=lambda x: -x[1]):
                marker = "→" if option == answer["choice"] else " "
                print(f"  {marker} {option:20s} {prob:.2f}")
        elif answer["type"] == "score":
            print(f"  score: {answer['score']} ({answer['legend'][str(int(round(answer['score'])))]})")
        elif answer["type"] == "noul":
            print(f"  probability: {answer['noul']:.2f}")

result = call_jev(message, questions)
print_decision_trace(result)
