import streamlit as st

from src.ui.base_layout import style_background_dashboard, style_base_layout

from src.components.header import header_dashboard
from src.components.subject_card import subject_card


def teacher_screen():

    style_background_dashboard()
    style_base_layout()

    if "teacher_data" in st.session_state:
        teacher_dashboard()
    elif 'teacher_login_type' not in st.session_state or st.session_state.teacher_login_type=="login":
        teacher_screen_login()
    elif st.session_state.teacher_login_type == "register":
        teacher_screen_register()





def teacher_dashboard():
    teacher_data = st.session_state.teacher_data
    c1, c2 = st.columns(2, vertical_alignment='center', gap='xxlarge')
    with c1:
        header_dashboard()
    with c2:
        st.subheader(f"""Welcome, {teacher_data['name']} """)
        if st.button("Logout", type='secondary', key='loginbackbtn', shortcut="control+backspace"):
            st.session_state['is_logged_in'] = False
            del st.session_state.teacher_data 
            st.rerun()


    st.space()

    if "current_teacher_tab" not in st.session_state:
        st.session_state.current_teacher_tab = 'take_attendance'
    tab1, tab2, tab3, tab4 = st.columns(4)


    with tab1:
        type1 = "primary" if st.session_state.current_teacher_tab == 'take_attendance' else "tertiary"
        if st.button('Take Attendance',type=type1, width='stretch', icon=':material/ar_on_you:'):
            st.session_state.current_teacher_tab = 'take_attendance'
            st.rerun()

    with tab2:
        type2 = "primary" if st.session_state.current_teacher_tab == 'manage_subjects' else "tertiary"
        if st.button('Manage Subjects', type=type2, width='stretch', icon=':material/book_ribbon:'):
            st.session_state.current_teacher_tab = 'manage_subjects'
            st.rerun()

    with tab3:
        type3 = "primary" if st.session_state.current_teacher_tab == 'attendance_records' else "tertiary"
        if st.button('Attendance Records',type=type3, width='stretch', icon=':material/cards_stack:'):
            st.session_state.current_teacher_tab = 'attendance_records'
            st.rerun()

    with tab4:
        type4 = "primary" if st.session_state.current_teacher_tab == 'voice_reviews' else "tertiary"
        if st.button('Voice Reviews', type=type4, width='stretch', icon=':material/mic:'):
            st.session_state.current_teacher_tab = 'voice_reviews'
            st.rerun()


    st.divider()

    if st.session_state.current_teacher_tab == "take_attendance":
        teacher_tab_take_attendance()
    if st.session_state.current_teacher_tab == "manage_subjects":
        teacher_tab_manage_subjects()
    if st.session_state.current_teacher_tab == "attendance_records":
        teacher_tab_attendance_records()
    if st.session_state.current_teacher_tab == "voice_reviews":
        teacher_tab_voice_reviews()

    



def teacher_tab_take_attendance():
    from src.database.db import get_teacher_subjects

    teacher_id = st.session_state.teacher_data['teacher_id']
    st.header('Take AI Attendance')


    if 'attendance_images' not in st.session_state:
        st.session_state.attendance_images = []

    subjects = get_teacher_subjects(teacher_id)

    if not subjects:
        st.warning('You havent created any subjects yet! Please create one to begin!')
        return
    
    subject_options = {f"{s['name']} - {s['subject_code']}": s['subject_id'] for s in subjects}

    col1, col2 = st.columns([3,1], vertical_alignment='bottom')

    with col1:
        selected_subject_label = st.selectbox('Select Subject', options=list(subject_options.keys()))

    with col2:
        if st.button('Add Photos', type='primary', icon=':material/photo_prints:', width='stretch'):
            from src.components.dialog_add_photo import add_photos_dialog

            add_photos_dialog()

    selected_subject_id = subject_options[selected_subject_label]

    st.divider()

    if st.session_state.attendance_images:
        st.header('Added Photos')
        gallery_cols = st.columns(4)

        for idx, img in enumerate(st.session_state.attendance_images):
            with gallery_cols[idx % 4 ]:
                st.image(img, width='stretch', caption=f'Photo {idx+1}')
    has_photos = bool(st.session_state.attendance_images)
    c1, c2 = st.columns(2)

    with c1:
        if st.button('Clear all photos', width='stretch', type='tertiary', icon=':material/delete:', disabled=not has_photos):
            st.session_state.attendance_images = []
            st.rerun()


    with c2:
        
        if st.button('Run Face Analysis', width='stretch', type='secondary', icon=':material/analytics:', disabled=not has_photos):
            with st.spinner('Deep scanning classroom photos...'):
                from datetime import datetime

                import numpy as np
                import pandas as pd

                from src.components.dialog_attendance_results import attendance_result_dialog
                from src.database.config import supabase
                from src.pipelines.face_pipeline import predict_attendance

                all_detected_ids = {}

                for idx, img in enumerate(st.session_state.attendance_images):
                    img_np = np.array(img.convert('RGB'))
                    detected, _, _ = predict_attendance(img_np)


                    if detected:
                        for sid in detected.keys():
                            student_id = int(sid)

                            all_detected_ids.setdefault(student_id, []).append(f"Photo {idx+1}")

                enrolled_res = supabase.table('subject_students').select("*, students(*)").eq('subject_id',selected_subject_id ).execute()
                enrolled_students = enrolled_res.data

                if not enrolled_students:
                    st.warning('No students enrolled in this course')
                else:

                    results, attendance_to_log  = [], []

                    current_timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


                    for node in enrolled_students:
                        student = node['students']
                        sources = all_detected_ids.get(int(student['student_id']), [])
                        is_present= len(sources) > 0

                        results.append({
                            "Name": student['name'],
                            "ID": student['student_id'],
                            "Source": ", ".join(sources) if is_present else "-",
                            "Status": "✅ Present" if is_present else "❌ Absent"
                        })

                        attendance_to_log.append({
                            'student_id': student['student_id'],
                            'subject_id': selected_subject_id,
                            'timestamp': current_timestamp,
                            'is_present': bool(is_present)
                        })

                attendance_result_dialog(pd.DataFrame(results), attendance_to_log)

def teacher_tab_manage_subjects():
    from src.database.db import get_teacher_subjects

    teacher_id = st.session_state.teacher_data['teacher_id']
    col1, col2 = st.columns(2)
    with col1:
        st.header('Manage Subjects', width='stretch')

    with col2:
        if st.button('Create New Subject', width='stretch'):
            from src.components.dialog_create_subject import create_subject_dialog

            create_subject_dialog(teacher_id)


    # LIST all SUBJECTS
    subjects = get_teacher_subjects(teacher_id)
    if subjects:
        for sub in subjects:
            stats = [
                ("🫂", "Students", sub['total_students']),
                ("🕰️", "Classes", sub['total_classes']),
            ]
        def share_btn():
            if st.button(f"Share Code: {sub['name']}", key=f"share_{sub['subject_code']}", icon=":material/share:"):
                from src.components.dialog_share_subject import share_subject_dialog

                share_subject_dialog(sub['name'], sub['subject_code'])
            st.space()

        subject_card(
            name = sub['name'],
            code = sub['subject_code'],
            section = sub['section'],
            stats=stats,
            footer_callback=share_btn
        )
    else:
        st.info("NO SUBJECTS FOUND. CREATE ONE ABOVE")


def teacher_tab_attendance_records():
    from datetime import datetime

    import pandas as pd

    from src.database.db import get_attendance_for_teacher

    st.header('Attendance Records')

    teacher_id = st.session_state.teacher_data['teacher_id']

    records = get_attendance_for_teacher(teacher_id)
    if not records:
        return
    
    data = []

    for r in records:
        ts = r.get('timestamp')
        parsed_ts = (
            datetime.fromisoformat(ts.replace('Z', '+00:00'))
            if ts
            else None
        )
        subject = r['subjects']
        student = r.get('students') or {}

        data.append({
            "ts_group": parsed_ts.replace(microsecond=0).isoformat() if parsed_ts else None,
            "Time": parsed_ts.strftime("%Y-%m-%d %I:%M %p") if parsed_ts else "N'A",
            "Subject ID": subject['subject_id'],
            "Subject": subject['name'],
            "Subject Code": subject['subject_code'],
            "Student ID": r['student_id'],
            "Name": student.get('name', 'Unknown'),
            "is_present": bool(r.get('is_present', False))
        })

    df = pd.DataFrame(data)

    detail_df = df.drop_duplicates(
        subset=['Subject ID', 'ts_group', 'Student ID'],
        keep='last',
    ).copy()
    sessions = (
        detail_df[['Subject ID', 'Student ID', 'ts_group']]
        .drop_duplicates()
        .sort_values(['Subject ID', 'Student ID', 'ts_group'])
    )
    sessions['Classes Held (through this class)'] = (
        sessions.groupby(['Subject ID', 'Student ID']).cumcount() + 1
    )
    detail_df = detail_df.merge(
        sessions,
        on=['Subject ID', 'Student ID', 'ts_group'],
        how='left',
    )
    detail_df = detail_df.sort_values(
        ['Subject ID', 'ts_group', 'Student ID']
    )
    detail_df['Classes Attended (through this class)'] = (
        detail_df.groupby(['Subject ID', 'Student ID'])['is_present'].cumsum()
    )
    detail_df['Attendance'] = detail_df['is_present'].map(
        {True: 'Present', False: 'Absent'}
    )
    csv_df = detail_df[
        [
            'Time',
            'Subject',
            'Subject Code',
            'Name',
            'Student ID',
            'Attendance',
            'Classes Attended (through this class)',
            'Classes Held (through this class)',
        ]
    ]

    st.download_button(
        'Download detailed attendance CSV',
        data=csv_df.to_csv(index=False).encode('utf-8-sig'),
        file_name='attendance_records.csv',
        mime='text/csv',
    )

    summary = (
        df.groupby(['ts_group', 'Time', 'Subject', 'Subject Code'])
        .agg(
            Present_Count = ('is_present', 'sum'),
            Total_Count =('is_present', 'count')
        ).reset_index()

    )

    summary['Attendance Stats'] = (
        "✅ " + summary['Present_Count'].astype(str) + " /"
        + summary['Total_Count'].astype(str) + ' Students'
    )

    display_df = ( summary.sort_values(by='ts_group' ,ascending=False)
                  [['Time', 'Subject', 'Subject Code', 'Attendance Stats']]
                  )
    
    st.dataframe(display_df, width='stretch', hide_index=True)


def teacher_tab_voice_reviews():
    from src.database.db import (
        get_pending_voice_attendance_for_subjects,
        get_teacher_subjects,
        review_voice_attendance,
    )

    teacher_id = st.session_state.teacher_data['teacher_id']
    subjects = get_teacher_subjects(teacher_id)
    subject_ids = [subject['subject_id'] for subject in subjects]

    st.header('Pending Voice Attendance')
    submissions = get_pending_voice_attendance_for_subjects(subject_ids)
    if not submissions:
        st.info('There are no voice attendance requests waiting for review.')
        return

    for submission in submissions:
        with st.container(border=True):
            st.subheader(submission['student_name'])
            st.write(
                f"{submission['subject_name']} ({submission['subject_code']})"
            )
            st.caption(
                f"Submitted: {submission['submitted_at']} · "
                f"Voice match: {submission['voice_match_score']:.1%}"
            )
            location_url = (
                "https://www.google.com/maps/search/?api=1&query="
                f"{submission['latitude']},{submission['longitude']}"
            )
            st.markdown(f"[View submitted GPS location]({location_url})")
            if submission.get('location_accuracy_m') is not None:
                st.caption(
                    f"Reported GPS accuracy: {submission['location_accuracy_m']} m"
                )

            approve_col, reject_col = st.columns(2)
            with approve_col:
                if st.button(
                    'Approve',
                    key=f"approve_voice_{submission['submission_id']}",
                    type='primary',
                    width='stretch',
                ):
                    try:
                        review_voice_attendance(
                            submission['submission_id'],
                            teacher_id,
                            approved=True,
                        )
                    except ValueError as error:
                        st.warning(str(error))
                    else:
                        st.success('Attendance approved.')
                        st.rerun()
            with reject_col:
                if st.button(
                    'Reject',
                    key=f"reject_voice_{submission['submission_id']}",
                    type='secondary',
                    width='stretch',
                ):
                    try:
                        review_voice_attendance(
                            submission['submission_id'],
                            teacher_id,
                            approved=False,
                        )
                    except ValueError as error:
                        st.warning(str(error))
                    else:
                        st.success('Attendance rejected.')
                        st.rerun()


def login_teacher(username, password):
    from src.database.db import teacher_login

    if not username or not password:
        return False
    
    teacher = teacher_login(username, password)

    if teacher:
        st.session_state.user_role ='teacher'
        st.session_state.teacher_data = teacher
        st.session_state.is_logged_in = True
        return True
    

    return False
def teacher_screen_login():
    c1, c2 = st.columns(2, vertical_alignment='center', gap='xxlarge')
    with c1:
        header_dashboard()
    with c2:
        if st.button("Go back to Home", type='secondary', key='loginbackbtn', shortcut="control+backspace"):
            st.session_state['login_type'] = None
            st.rerun()

    st.header('Login using password', text_alignment='center')
    st.space()
    st.space()


    teacher_username = st.text_input("Enter username", placeholder='ananyaroy')

    teacher_pass = st.text_input("Enter password", type='password', placeholder="Enter password")

    st.divider()

    btnc1, btnc2 = st.columns(2)

    with btnc1:
        if st.button('Login', icon=':material/passkey:', shortcut='control+enter', width='stretch'):
            if login_teacher(teacher_username, teacher_pass):
                st.toast("welcome back!", icon="👋")
                st.rerun()
            else:
                st.error("Invalid username and password combo")

    with btnc2:
        if st.button('Register Instead', type="primary", icon=':material/passkey:', width='stretch'):
            st.session_state.teacher_login_type = 'register'




def register_teacher(teacher_username, teacher_name, teacher_pass, teacher_pass_confirm):
    from src.database.db import check_teacher_exists, create_teacher

    if not teacher_username or not teacher_name or not teacher_pass:
        return False, "All Fields are required!"
    if check_teacher_exists(teacher_username):
        return False, "Username already taken"
    if teacher_pass != teacher_pass_confirm:
        return False, "Password doesn't match"
    
    try:
        create_teacher(teacher_username, teacher_pass, teacher_name)
        return True, "Sucessfully Created! Login Now"
    except Exception as e:
        return False, "Unexpected Error!"
    

def teacher_screen_register():
    c1, c2 = st.columns(2, vertical_alignment='center', gap='xxlarge')
    with c1:
        header_dashboard()
    with c2:
        if st.button("Go back to Home", type='secondary', key='loginbackbtn', shortcut="control+backspace"):
            st.session_state['login_type'] = None
            st.rerun()



    st.header('Register your teacher profile')

    st.space()
    st.space()

    
    teacher_username = st.text_input("Enter username", placeholder='ananyaroy')

    teacher_name = st.text_input("Enter name", placeholder='Ananya Roy')

    teacher_pass = st.text_input("Enter password", type='password', placeholder="Enter password")

    teacher_pass_confirm = st.text_input("Confirm your password", type='password', placeholder="Enter password")

    st.divider()

    btnc1, btnc2 = st.columns(2)

    with btnc1:
        if st.button('Register now', icon=':material/passkey:', shortcut='control+enter', width='stretch'):
            success, message = register_teacher(teacher_username, teacher_name, teacher_pass, teacher_pass_confirm)
            if success:
                st.success(message)
                st.session_state.teacher_login_type = "login"
                st.rerun()
            else:
                st.error(message)


    with btnc2:
        if st.button('Login Instead', type="primary", icon=':material/passkey:', width='stretch'):
            st.session_state.teacher_login_type = 'login'
