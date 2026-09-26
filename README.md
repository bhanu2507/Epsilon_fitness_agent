# Epsilon_fitness_agent

Personalized fitness & wellness assistant, powered by Claude.

## Setup

1. Install dependencies:
   ```
   uv sync
   ```
2. Add your Anthropic API key to `.env`:
   ```
   ANTHROPIC_API_KEY=sk-ant-...
   ```

## Run

**Streamlit chat UI:**
```
uv run streamlit run app.py
```
Then open http://localhost:8501 and pick a user from the sidebar.

**CLI chat loop:**
```
uv run python chat.py <user_id>
```
e.g. `uv run python chat.py u001` (see `data/user_profiles.json` for available user IDs).