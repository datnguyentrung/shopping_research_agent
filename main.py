import argparse
import asyncio
import json
import sys

from util import ensure_api_key_configured

from shopping_research import shopping_research

# Workaround for Playwright's NotImplementedError on Windows
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


def build_input(topic: str) -> dict:
    return {
        "topic": topic,
        "target_platform": "google_shopping",
        "duration_seconds": 45,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run local smoke setup for ShortsPipelineAgent.")
    parser.add_argument("topic", nargs="?", default="AI thay doi cong viec trong 5 nam toi")
    parser.add_argument("--run", action="store_true", help="Run agent ngay trong local script (co retry).")
    args = parser.parse_args()

    ensure_api_key_configured()

    payload = build_input(args.topic)
    print("Loaded root agent:", shopping_research.root_agent.name)
    print("Sample input payload:")
    print(json.dumps(payload, ensure_ascii=False, indent=2))

    if not args.run:
        print("\nNext step: run this project with your ADK workflow (for example adk web / adk run).")
        print("Hoac chay local voi retry: python main.py \"ao khoac da\" --run")
        return

    try:
        result = shopping_research.run_agent_with_retry(payload)
        print("\nAgent result:")
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    except Exception as exc:
        print(f"\nAgent failed after retries: {exc}")


if __name__ == "__main__":
    main()
