"""Streamlit chat UI for the Epsilon Fitness Agent."""

import anthropic
import streamlit as st
from dotenv import load_dotenv

from chat import MODEL, build_system_prompt
from epsilon_fitness_agent.storage import profiles

load_dotenv()

st.set_page_config(page_title="Epsilon Fitness Agent", page_icon="🏋️")


@st.cache_resource
def get_client() -> anthropic.Anthropic:
    return anthropic.Anthropic()


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
        st.session_state.pop("messages", None)
        st.session_state.pop("chat_user_id", None)
        st.rerun()

# Reset the conversation whenever the selected user changes.
if st.session_state.get("chat_user_id") != selected_user_id:
    st.session_state.chat_user_id = selected_user_id
    st.session_state.messages = []

st.title("🏋️ Epsilon Fitness Agent")
st.caption(f"Personalized fitness & wellness assistant — chatting as {profile['name']}")

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if user_input := st.chat_input("Ask about workouts, meals, gyms, or your progress..."):
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    system_prompt = build_system_prompt(selected_user_id)
    client = get_client()

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            response = client.messages.create(
                model=MODEL,
                max_tokens=4096,
                system=system_prompt,
                messages=st.session_state.messages,
            )
            reply = next((b.text for b in response.content if b.type == "text"), "")
        st.markdown(reply)

    st.session_state.messages.append({"role": "assistant", "content": reply})
