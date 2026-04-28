#!/usr/bin/env python3
"""Smoke test for llm.call_llm.

Run from the project root:
    python llm_test.py
"""

import os
import sys


PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from llm import call_llm


def main() -> int:
    messages = [
        {"role": "system", "content": "You are a concise assistant."},
        {"role": "user", "content": "What is the capital of Finland?"},
    ]

    print("Running LLM proxy smoke test...")
    try:
        response = call_llm(messages, temperature=0.0)
    except Exception as exc:
        print(f"FAILED: {exc}")
        return 1

    if not response or not response.strip():
        print("FAILED: Empty response returned by llm.call_llm")
        return 1

    print("SUCCESS: call_llm returned a response")
    print("Response:")
    print(response)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())