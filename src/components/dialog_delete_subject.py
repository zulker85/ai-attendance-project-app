import streamlit as st


@st.dialog("Delete subject")
def delete_subject_dialog(subject_id, teacher_id, subject_name, subject_code):
    st.warning(
        f"Delete {subject_name} ({subject_code}) permanently? This also deletes "
        "its student enrollments, attendance history, voice submissions, and "
        "live check-in sessions and reviews. This cannot be undone."
    )
    confirm = st.checkbox(
        "I understand that this subject and its related records will be deleted.",
        key=f"confirm_subject_delete_{subject_id}",
    )
    cancel_col, delete_col = st.columns(2)
    with cancel_col:
        if st.button("Cancel", width="stretch"):
            st.rerun()
    with delete_col:
        if st.button(
            "Delete subject",
            type="primary",
            width="stretch",
            disabled=not confirm,
        ):
            from src.database.db import delete_teacher_subject

            try:
                with st.spinner("Deleting subject and related records..."):
                    delete_teacher_subject(subject_id, teacher_id)
            except Exception as error:
                error_text = str(error)
                if "PGRST202" in error_text or "delete_teacher_subject" in error_text:
                    st.error(
                        "Supabase cannot find the delete function. Run "
                        "`sql/delete_teacher_subject.sql` in the Supabase SQL "
                        "Editor, then try again. If you already ran it, refresh "
                        "the Supabase API schema cache and wait a few seconds."
                    )
                else:
                    st.error(f"Could not delete the subject: {error_text}")
                return

            st.success(f"{subject_name} and its related records were deleted.")
            st.rerun()
