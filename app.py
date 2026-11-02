import streamlit as st

from agent import Agent

st.set_page_config(page_title="Credit Risk Agent", page_icon="📊", layout="wide")
st.title("Credit Risk Agent")

if "agent" not in st.session_state:
    st.session_state.agent = Agent()
    st.session_state.messages = []

for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

if prompt := st.chat_input("Ask about a client..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                reply = st.session_state.agent.chat(prompt)
            except Exception as e:
                reply = f"Erreur : {e}"
        st.markdown(reply)
    st.session_state.messages.append({"role": "assistant", "content": reply})