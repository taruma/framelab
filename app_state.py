import streamlit as st


PHASE1_DONE = "phase1_done"
CONVERSATION_MESSAGES = "conversation_messages"
PHASE1_OUTPUT = "phase1_output"
PHASE1_REASONING = "phase1_reasoning"
PHASE1_USAGE = "phase1_usage"
PHASE2_OUTPUT = "phase2_output"
PHASE2_REASONING = "phase2_reasoning"
PHASE2_USAGE = "phase2_usage"
PREFER_RESPONSES_API = "prefer_responses_api"


def init_state() -> None:
    defaults = {
        PHASE1_DONE: False,
        CONVERSATION_MESSAGES: [],
        PHASE1_OUTPUT: "",
        PHASE1_REASONING: "",
        PHASE1_USAGE: None,
        PHASE2_OUTPUT: "",
        PHASE2_REASONING: "",
        PHASE2_USAGE: None,
        PREFER_RESPONSES_API: True,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value
