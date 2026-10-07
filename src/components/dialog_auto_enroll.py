import streamlit as st
from src.database.db import enroll_student_to_subject
from src.database.config import supabase


def _close_invite():
    st.query_params["page"] = "student"
    st.query_params.pop("join-code", None)
    st.rerun()


@st.dialog("Quick Enrollment")
def auto_enroll_dialog(subject_code):
    student_id = st.session_state.student_data['student_id']


    res = supabase.table('subjects').select('subject_id, name').eq('subject_code', subject_code).execute()
    if not res.data:
        st.error('Subject Code not found!')
        if st.button('Close'):
            _close_invite()
        return
    subject = res.data[0]

    check = supabase.table('subject_students').select('*').eq('subject_id', subject['subject_id']).eq('student_id', student_id).execute()
    if check.data:
        st.info('Youre already enrolled!')
        if st.button('Got it!'):
            _close_invite()
        return
    st.markdown(f'Would you like to enroll in **{subject['name']}**?')

    col1, col2 = st.columns(2)

    with col1:
        if st.button('No thanks'):
            _close_invite()
    with col2:
        if st.button('Yes enroll now!', type='primary', width='stretch'):
            enroll_student_to_subject(student_id, subject['subject_id'])
            st.success('Joined succesfully!')
            _close_invite()
