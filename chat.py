#!/usr/bin/env python3
"""CLI chat loop for the Epsilon Fitness Agent, scoped to one user's profile."""

import json
import sys

import anthropic
from dotenv import load_dotenv

from epsilon_fitness_agent.storage import profiles

load_dotenv()

MODEL = "claude-opus-5"

SYSTEM_TEMPLATE = """You are Epsilon, a personal fitness and wellness assistant.

You help with:
- Personalized workout and exercise recommendations
- Diet and meal recommendations based on user preferences
- Nearby gym and fitness facility recommendations
- Fitness and nutrition progress tracking
- Ongoing fitness and wellness guidance

The current user's profile:
{profile_json}

Tailor every recommendation to this profile: respect their goals, equipment access,
dietary preferences/restrictions, and injuries/limitations. Ask clarifying questions
when the profile doesn't give you enough to make a safe, specific recommendation."""


def build_system_prompt(user_id: str) -> str:
    profile = profiles.get(user_id)
    if profile is None:
        raise ValueError(f"No profile found for user_id={user_id!r}")
    return SYSTEM_TEMPLATE.format(profile_json=json.dumps(profile, indent=2))


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python chat.py <user_id>")
        sys.exit(1)

    user_id = sys.argv[1]
    system_prompt = build_system_prompt(user_id)

    client = anthropic.Anthropic()
    messages = []

    print(f"Chatting as {user_id}. Type 'exit' to quit.\n")

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if user_input.lower() in ("exit", "quit"):
            break
        if not user_input:
            continue

        messages.append({"role": "user", "content": user_input})

        response = client.messages.create(
            model=MODEL,
            max_tokens=4096,
            system=system_prompt,
            messages=messages,
        )

        reply = next((b.text for b in response.content if b.type == "text"), "")
        print(f"\nEpsilon: {reply}\n")

        messages.append({"role": "assistant", "content": reply})


if __name__ == "__main__":
    main()
