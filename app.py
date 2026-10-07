
import streamlit as st

from src.screens.home_screen import home_screen

def main():
    st.set_page_config(
        page_title='SnapClass - Making Attendance faster using AI',
        page_icon= "https://i.ibb.co/YTYGn5qV/logo.png"
    )
    if 'login_type' not in st.session_state:
        st.session_state['login_type'] = None

    page = st.query_params.get('page')
    if page not in ('home', 'student', 'teacher'):
        page = 'student' if st.query_params.get('join-code') else 'home'
    st.session_state['login_type'] = None if page == 'home' else page

    match page:
        case 'teacher':
            from src.screens.teacher_screen import teacher_screen

            teacher_screen()

        case 'student':
            from src.screens.student_screen import student_screen

            student_screen()
        
        case 'home':
            home_screen()

    join_code = st.query_params.get('join-code')
    if (
        join_code
        and page == 'student'
        and st.session_state.get('is_logged_in')
        and st.session_state.get('user_role') == 'student'
    ):
        from src.components.dialog_auto_enroll import auto_enroll_dialog

        auto_enroll_dialog(join_code)


main()