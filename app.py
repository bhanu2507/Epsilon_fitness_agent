"""Streamlit chat UI for the Epsilon Fitness Agent."""

import anthropic
import streamlit as st
from dotenv import load_dotenv

from chat import build_system_prompt, build_tools, run_turn
from epsilon_fitness_agent.conversations import clear_conversation, load_conversation, save_conversation
from epsilon_fitness_agent.storage import profiles

load_dotenv()

st.set_page_config(page_title="Epsilon Fitness Agent", page_icon="🏋️")

st.markdown(
    """
    <style>
    [data-testid="stSidebar"] {
        min-width: 220px;
        max-width: 220px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_resource
def get_client() -> anthropic.Anthropic:
    return anthropic.Anthropic()


def render_assistant_turn(tool_names: list, text: str) -> None:
    for name in tool_names:
        st.caption(f"🔧 called `{name}`")
    st.markdown(text)


all_profiles = profiles.load_all()
profile_labels = {p["user_id"]: f"{p['name']} ({p['user_id']})" for p in all_profiles}

with st.sidebar:
    st.header("User")
    selected_user_id = st.selectbox(
        "Chatting as",
        options=list(profile_labels.keys()),
        format_func=lambda uid: profile_labels[uid],
    )
    profile = profiles.get(selected_user_id)
    st.subheader("Profile")
    st.json(profile, expanded=False)

    if st.button("Clear conversation"):
        clear_conversation(selected_user_id)
        st.session_state.pop("api_messages", None)
        st.session_state.pop("display", None)
        st.session_state.pop("chat_user_id", None)
        st.rerun()

# Load this user's conversation whenever the selected user changes - the
# agent picks up where it left off across sessions, not just within one.
if st.session_state.get("chat_user_id") != selected_user_id:
    st.session_state.chat_user_id = selected_user_id
    saved = load_conversation(selected_user_id)
    st.session_state.api_messages = saved["messages"]  # full history sent to the model (incl. tool calls)
    st.session_state.display = saved["display"]  # [{"role", "text", "tools": [...]}] for rendering

st.title("🏋️ Epsilon Fitness Agent")
st.caption(f"Personalized fitness & wellness assistant — chatting as {profile['name']}")
if st.session_state.display:
    st.caption(f"↩ Resumed a previous conversation ({len(st.session_state.display)} messages)")

for entry in st.session_state.display:
    with st.chat_message(entry["role"]):
        if entry["role"] == "assistant":
            render_assistant_turn(entry.get("tools", []), entry["text"])
        else:
            st.markdown(entry["text"])

if user_input := st.chat_input("Ask about workouts, meals, gyms, or your progress..."):
    st.session_state.display.append({"role": "user", "text": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)
    st.session_state.api_messages.append({"role": "user", "content": user_input})

    system_prompt = build_system_prompt(selected_user_id)
    tools = build_tools(selected_user_id)
    client = get_client()

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            reply, tool_names_called = run_turn(
                client, st.session_state.api_messages, tools, system_prompt
            )
        render_assistant_turn(tool_names_called, reply)

    st.session_state.display.append(
        {"role": "assistant", "text": reply, "tools": tool_names_called}
    )
    save_conversation(selected_user_id, st.session_state.api_messages, st.session_state.display)
