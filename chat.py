#!/usr/bin/env python3
"""CLI chat loop for the Epsilon Fitness Agent, scoped to one user's profile."""

import json
import sys

import anthropic
from dotenv import load_dotenv

from epsilon_fitness_agent.progress import summarize_progress
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

The current user's progress, precomputed locally from their logged history
(this data is authoritative - trust these numbers over any mental math of
your own). "total_logged": 0 for a section means they haven't logged anything
of that type yet - say so plainly rather than inventing history. A few of
their most recent raw workout/meal entries are included for qualitative
detail (notes, specific foods/exercises) alongside the computed stats:

{progress_json}

Tailor every recommendation to this profile and progress data: respect their
goals, equipment access, dietary preferences/restrictions, and injuries/
limitations. Ask clarifying questions when the profile or progress data
doesn't give you enough to make a safe, specific recommendation."""


def build_system_prompt(user_id: str) -> str:
    profile = profiles.get(user_id)
    if profile is None:
        raise ValueError(f"No profile found for user_id={user_id!r}")
    return SYSTEM_TEMPLATE.format(
        profile_json=json.dumps(profile, indent=2),
        progress_json=json.dumps(summarize_progress(user_id), indent=2),
    )


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
