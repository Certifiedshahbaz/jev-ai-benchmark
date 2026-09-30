import asyncio
import sys
import os

# Ensure backend directory is in sys.path so app module can be imported
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app.services.typesafe_service import typesafe_service
from typesafe_sdk import Noul

async def main():
    print("=" * 65)
    print("SERALI JEV WORKFORCE LAB — Stage 2 TypeSafe SDK Integration Test")
    print("=" * 65)

    test_state = {
        "customer_message": "I ordered a laptop 5 days ago and the tracking status hasn't updated. I need to know where it is right now!"
    }

    questions = {
        "is_shipping_inquiry": Noul(
            instructions="Is the customer asking about shipping, tracking, delivery status, or package location?"
        )
    }

    print(f"\n[Test Payload]")
    print(f"State: {test_state}")
    print(f"Question: Noul('is_shipping_inquiry')")
    print("\nSending request to TypeSafe Jev API via official SDK...")

    try:
        result = await typesafe_service.evaluate(
            state=test_state,
            questions=questions,
        )

        print("\n" + "-" * 65)
        print("RESULT: SUCCESS")
        print("-" * 65)
        print(f"  Model Version:  {result.get('model')}")
        print(f"  Request ID:     {result.get('request_id')}")
        print(f"  Input Tokens:   {result.get('usage', {}).get('input_tokens')}")
        print(f"  Output Tokens:  {result.get('usage', {}).get('output_tokens')}")

        print("\n  Parsed Answers:")
        answers = result.get("answers", {})
        for k, v in answers.items():
            print(f"    - {k}: {v}")

        print("\n  Timing Breakdown:")
        timing = result.get("timing", {})
        print(f"    - Prep Latency:  {timing.get('prep_ms')} ms")
        print(f"    - API Latency:   {timing.get('api_ms')} ms")
        print(f"    - Total Latency: {timing.get('total_ms')} ms")
        print("=" * 65)

    except Exception as e:
        print("\n" + "-" * 65)
        print("RESULT: FAILED")
        print("-" * 65)
        print(f"Error details: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
