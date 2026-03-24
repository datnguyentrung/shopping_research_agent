import argparse
import json

from util import ensure_api_key_configured

from shopping_research import shopping_research


def build_input(topic: str) -> dict:
    return {
        "topic": topic,
        "target_platform": "google_shopping",
        "duration_seconds": 45,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run local smoke setup for ShortsPipelineAgent.")
    parser.add_argument("topic", nargs="?", default="AI thay doi cong viec trong 5 nam toi")
    args = parser.parse_args()

    ensure_api_key_configured()


    print("Loaded root agent:", shopping_research.root_agent.name)
    print("Sample input payload:")
    print(json.dumps(build_input(args.topic), ensure_ascii=False, indent=2))
    print("\nNext step: run this project with your ADK workflow (for example adk web / adk run).")


if __name__ == "__main__":
    main()
