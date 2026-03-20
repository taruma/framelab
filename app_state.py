import streamlit as st


PHASE1_DONE = "phase1_done"
CONVERSATION_MESSAGES = "conversation_messages"
PHASE1_OUTPUT = "phase1_output"
PHASE1_REASONING = "phase1_reasoning"
PHASE1_USAGE = "phase1_usage"
PHASE1_EDITED_BY_USER = "phase1_edited_by_user"
PHASE2_OUTPUT = "phase2_output"
PHASE2_REASONING = "phase2_reasoning"
PHASE2_USAGE = "phase2_usage"
PHASE2_EDITED_BY_USER = "phase2_edited_by_user"
PREFER_RESPONSES_API = "prefer_responses_api"
IS_PROCESSING = "is_processing"
PENDING_ACTION = "pending_action"
LAST_ERROR = "last_error"


def init_state() -> None:
    defaults = {
        PHASE1_DONE: False,
        CONVERSATION_MESSAGES: [],
        PHASE1_OUTPUT: "",
        PHASE1_REASONING: "",
        PHASE1_USAGE: None,
        PHASE1_EDITED_BY_USER: False,
        PHASE2_OUTPUT: "",
        PHASE2_REASONING: "",
        PHASE2_USAGE: None,
        PHASE2_EDITED_BY_USER: False,
        PREFER_RESPONSES_API: True,
        IS_PROCESSING: False,
        PENDING_ACTION: None,
        LAST_ERROR: "",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value
