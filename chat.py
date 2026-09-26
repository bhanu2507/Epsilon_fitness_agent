#!/usr/bin/env python3
"""CLI chat loop for the Epsilon Fitness Agent, scoped to one user's profile.

Uses Claude's tool calling (via the Anthropic SDK's tool runner) so the model
fetches the user's profile/progress only when it actually needs them, instead
of every turn's system prompt carrying that data whether it's relevant or not.
"""

import json
import sys

import anthropic
from anthropic import beta_tool
from dotenv import load_dotenv

from epsilon_fitness_agent.progress import summarize_progress
from epsilon_fitness_agent.storage import profiles

load_dotenv()

MODEL = "claude-opus-5"

SYSTEM_PROMPT = """You are Epsilon, a personal fitness and wellness assistant.

You help with:
- Personalized workout and exercise recommendations
- Diet and meal recommendations based on user preferences
- Nearby gym and fitness facility recommendations
- Fitness and nutrition progress tracking
- Ongoing fitness and wellness guidance

You have tools to look up the current user's profile and their locally
computed progress stats - use them instead of guessing or assuming. Once
you've fetched something earlier in this conversation, don't re-fetch it
unless the user's question suggests it may have changed.

Tailor every recommendation to the user's goals, equipment access, dietary
preferences/restrictions, and injuries/limitations. Ask clarifying questions
when you don't have enough to make a safe, specific recommendation.

When answering a progress question, keep it compact: lead with the takeaway
(trending up/down/flat, on-track or not), cite only the 1-2 numbers that
support it, and skip straight to what to do next."""


def build_system_prompt(user_id: str) -> str:
    if profiles.get(user_id) is None:
        raise ValueError(f"No profile found for user_id={user_id!r}")
    return SYSTEM_PROMPT


def build_tools(user_id: str) -> list:
    """Tools scoped to one user via closure, so the model never has to pass
    (or hallucinate) a user_id argument."""

    @beta_tool
    def get_profile() -> str:
        """Get the current user's fitness profile: goals, equipment access,
        dietary preferences/restrictions, injuries/limitations, and other
        demographics. Call this before giving any personalized workout,
        meal, or gym recommendation."""
        return json.dumps(profiles.get(user_id), indent=2)

    @beta_tool
    def get_progress_summary() -> str:
        """Get the current user's progress: workout consistency, meal
        logging stats, and weight/body-fat trends, precomputed locally from
        their logged history (trust these numbers over any mental math of
        your own). "total_logged": 0 for a section means nothing has been
        logged yet - say so plainly rather than inventing history. Call this
        when asked about progress, trends, or consistency."""
        return json.dumps(summarize_progress(user_id), indent=2)

    return [get_profile, get_progress_summary]


def run_turn(client: anthropic.Anthropic, messages: list, tools: list, system_prompt: str) -> tuple[str, list]:
    """Run one user turn to completion via the tool runner, mirroring the
    full conversation (including tool_use/tool_result blocks) back into
    `messages` since the runner doesn't expose its internal copy.

    Returns (final_text, tool_names_called).
    """
    runner = client.beta.messages.tool_runner(
        model=MODEL,
        max_tokens=4096,
        system=system_prompt,
        tools=tools,
        messages=messages,
    )

    final_text = ""
    tool_names_called = []

    for message in runner:
        messages.append({"role": "assistant", "content": message.content})
        for block in message.content:
            if block.type == "tool_use":
                tool_names_called.append(block.name)

        tool_response = runner.generate_tool_call_response()
        if tool_response is not None:
            messages.append(tool_response)

        text = next((b.text for b in message.content if b.type == "text"), None)
        if text:
            final_text = text

    return final_text, tool_names_called


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python chat.py <user_id>")
        sys.exit(1)

    user_id = sys.argv[1]
    system_prompt = build_system_prompt(user_id)
    tools = build_tools(user_id)

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

        reply, tool_names_called = run_turn(client, messages, tools, system_prompt)

        for name in tool_names_called:
            print(f"  [tool] {name}")
        print(f"\nEpsilon: {reply}\n")


if __name__ == "__main__":
    main()
