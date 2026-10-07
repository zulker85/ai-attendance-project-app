from typing import Literal

import streamlit as st


def navigate_to(page: Literal["home", "student", "teacher"]) -> None:
    st.session_state["login_type"] = None if page == "home" else page
    st.query_params["page"] = page
    st.rerun()
