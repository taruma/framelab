import streamlit as st


PHASE1_DONE = "phase1_done"
CONVERSATION_MESSAGES = "conversation_messages"
PHASE1_OUTPUT = "phase1_output"
PHASE1_REASONING = "phase1_reasoning"
PHASE2_OUTPUT = "phase2_output"
PHASE2_REASONING = "phase2_reasoning"


def init_state() -> None:
    defaults = {
        PHASE1_DONE: False,
        CONVERSATION_MESSAGES: [],
        PHASE1_OUTPUT: "",
        PHASE1_REASONING: "",
        PHASE2_OUTPUT: "",
        PHASE2_REASONING: "",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value
