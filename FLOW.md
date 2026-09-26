# Epsilon Fitness Agent — Application Flow

Diagrams use [Mermaid](https://mermaid.js.org/) syntax, which renders natively on GitHub.

## High-level flow

Claude decides at runtime which (if any) tools it needs — it doesn't always fetch
everything. Once fetched, results stay in the conversation so later turns don't
re-fetch them.

```mermaid
flowchart TD
    A[User picks a profile\nsidebar dropdown / CLI arg] --> B[User sends a message]
    B --> C["run_turn()\n(chat.py)"]
    C --> D["Claude (claude-opus-5)\nvia Tool Runner"]

    D -->|needs profile facts| E[get_profile tool]
    D -->|needs progress/trends| F[get_progress_summary tool]
    D -->|needs nearby gyms| G[find_nearby_gyms tool]
    D -->|has enough already| H[Compose answer directly]

    E --> I["storage.py\nprofiles JSONStore"]
    F --> J["progress.py\nsummarize_progress()"]
    J --> K["storage.py\nworkout/meal/progress JSONStore"]
    G --> L["gyms.py\nsearch_nearby_gyms()"]
    L --> M[Google Places API]

    I --> D
    J --> D
    L --> D
    H --> N[Final response text]
    D --> N

    N --> O["app.py (Streamlit) or chat.py (CLI)\nrenders reply + tool-call tags"]
    O --> U[User]
```

## Per-turn sequence (example: "Find me a good gym nearby")

```mermaid
sequenceDiagram
    participant U as User
    participant App as app.py / chat.py
    participant Claude as Claude (Tool Runner)
    participant Tools as Tool functions (chat.py)
    participant Data as storage.py / progress.py
    participant Places as Google Places API

    U->>App: "Find me a good gym nearby"
    App->>Claude: messages + system prompt + tool defs

    Claude-->>App: tool_use: get_profile
    App->>Tools: get_profile()
    Tools->>Data: profiles.get(user_id)
    Data-->>Tools: profile JSON
    Tools-->>App: tool_result
    App->>Claude: tool_result appended to messages

    Claude-->>App: tool_use: find_nearby_gyms(radius_km)
    App->>Tools: find_nearby_gyms()
    Tools->>Places: POST /places:searchNearby
    Places-->>Tools: nearby places
    Tools-->>App: tool_result (sorted by distance, computed locally)
    App->>Claude: tool_result appended to messages

    Claude-->>App: final text (no more tool calls)
    App-->>U: rendered reply, with "🔧 called ..." tags per tool used
```

## Components

| File | Role |
|---|---|
| `data/*.json` | Mock user profiles, workout/meal/progress logs |
| `epsilon_fitness_agent/storage.py` | `JSONStore` — load/query/save/delete over the JSON files |
| `epsilon_fitness_agent/progress.py` | Local (non-LLM) trend computation from logs — sessions/week, macro averages, weight/body-fat deltas |
| `epsilon_fitness_agent/gyms.py` | Google Places API wrapper — nearby gym search, local distance sort (haversine) |
| `chat.py` | System prompt, the 3 tool definitions (`get_profile`, `get_progress_summary`, `find_nearby_gyms`), and `run_turn()` — the tool-calling loop |
| `app.py` | Streamlit chat UI — renders messages and tool-call tags, drives `run_turn()` per user input |
| `.env` | `ANTHROPIC_API_KEY`, `GOOGLE_MAPS_API_KEY` |

## Why tool calling instead of always injecting data

Earlier versions embedded the full profile + all logs into every system prompt.
Now the model calls tools only when a question actually needs that data, and reuses
results already fetched earlier in the same conversation — cutting tokens on
generic questions (e.g. "what's the difference between HIIT and steady-state
cardio?") to near zero extra context.
