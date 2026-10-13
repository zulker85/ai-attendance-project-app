import streamlit as st

from src.ui.base_layout import style_background_dashboard, style_base_layout

from src.components.header import header_dashboard
from src.components.subject_card import subject_card
from src.ui.navigation import navigate_to

def student_dashboard():
    from src.database.db import (
        get_student_subjects,
        get_student_attendance,
        get_student_voice_attendance,
        unenroll_student_to_subject,
    )

    student_data = st.session_state.student_data
    student_id = student_data['student_id']
    c1, c2 = st.columns(2, vertical_alignment='center', gap='xxlarge')
    with c1:
        header_dashboard()
    with c2:
        st.subheader(f"""Welcome, {student_data['name']} """)
        if st.button("Logout", type='secondary', key='loginbackbtn', shortcut="control+backspace"):
            st.session_state['is_logged_in'] = False
            del st.session_state.student_data 
            st.rerun()


    st.space()

    c1, c2 =st.columns(2)
    with c1:
        st.header('Your Enrolled Subjects')
    with c2:
        if st.button('Enroll in Subject', type='primary', width='stretch'):
            from src.components.dialog_enroll import enroll_dialog

            enroll_dialog()


    st.divider()


    with st.spinner('Loading your enrolled subjects..'):
        subjects = get_student_subjects(student_id)
        logs = get_student_attendance(student_id)
        voice_submissions = get_student_voice_attendance(student_id)

    _render_student_privacy_controls(student_data)
    _render_live_class_checkin(student_data)

    stats_map = {}

    for log in logs:
        sid = log['subject_id']

        if sid not in stats_map:
            stats_map[sid] = {"total":0, "attended": 0}

        stats_map[sid]['total'] +=1

        if log.get('is_present'):
            stats_map[sid]['attended'] += 1

    submissions_by_subject = {}
    for submission in voice_submissions:
        submissions_by_subject.setdefault(submission['subject_id'], []).append(submission)

    cols = st.columns(2)
    for i, sub_node in enumerate(subjects):
        sub = sub_node['subjects']
        sid = sub['subject_id']


        stats = stats_map.get(sid,{"total":0, "attended": 0} )
        def unenroll_button():
                if st.button("Unenroll from tihs course", type='tertiary', width='stretch', icon=':material/delete_forever:'):
                    unenroll_student_to_subject(student_id, sid)
                    st.toast(f'Unenrolled from {sub["name"]} successfully!')
                    st.rerun()

        with cols[i % 2]:

            subject_card(
                name = sub['name'],
                code =sub['subject_code'],
                section = sub['section'],
                stats = [
                    ('📅', 'Total', stats['total']),
                    ('✅', 'Attended', stats['attended']),
                ],
                footer_callback=unenroll_button
            )

            with st.expander(f"Voice check-in history for {sub['name']}"):
                for submission in submissions_by_subject.get(sid, []):
                    if submission.get('status') == 'superseded':
                        continue
                    st.caption(
                        f"{submission['submitted_at']} — "
                        f"{submission['status'].capitalize()}"
                    )

                if st.button(
                    "Check in with voice",
                    key=f"voice_attendance_{sid}",
                    type="primary",
                    width="stretch",
                ):
                    from src.components.dialog_student_voice_attendance import (
                        student_voice_attendance_dialog,
                    )

                    student_voice_attendance_dialog(sub, student_data)


@st.dialog("Delete student account")
def _confirm_student_account_deletion(student_id):
    st.warning(
        "This permanently deletes your profile and biometric embeddings, "
        "enrollments, attendance records, and voice attendance requests. "
        "This cannot be undone."
    )
    confirm = st.checkbox(
        "I understand that all of this account's data will be deleted.",
        key=f"confirm_student_delete_{student_id}",
    )
    cancel_col, delete_col = st.columns(2)
    with cancel_col:
        if st.button("Cancel", width="stretch"):
            st.rerun()
    with delete_col:
        if st.button(
            "Delete my account",
            type="primary",
            width="stretch",
            disabled=not confirm,
        ):
            from src.database.db import delete_student_account

            with st.spinner("Deleting your account data..."):
                delete_student_account(student_id)
            st.session_state.pop("student_data", None)
            st.session_state["is_logged_in"] = False
            st.success("Your account and associated data were deleted.")
            st.rerun()


def _render_student_privacy_controls(student_data):
    with st.expander("Privacy and biometric data"):
        st.write(
            "Face and optional voice templates are stored as numeric embeddings "
            "for matching; captured photos and recordings are processed in memory "
            "and are not saved by this check-in feature."
        )
        st.write(
            "A class check-in stores its time, verification method and score, "
            "and any location you explicitly choose to share. Your teacher can "
            "review uncertain matches. Deleting your account also deletes its "
            "attendance history and enrollments."
        )
        if st.button(
            "Delete my account and data",
            key=f"delete_student_account_{student_data['student_id']}",
            type="secondary",
        ):
            _confirm_student_account_deletion(student_data["student_id"])


def _render_live_class_checkin(student_data):
    import math

    import numpy as np
    from PIL import Image

    student_id = student_data["student_id"]
    query_code = st.query_params.get("session-code", "")
    st.subheader("Live class check-in")
    st.caption(
        "Use the short-lived code from your teacher. Face and voice are checked "
        "against your saved profile; uncertain matches go to teacher review. "
        "GPS is optional."
    )
    access_code = st.text_input(
        "Class access code",
        value=query_code,
        max_chars=8,
        key=f"session_access_code_{student_id}",
        help="You can type the code or open the link in your teacher's QR code.",
    ).strip()

    method = st.radio(
        "Verification method",
        ("Face", "Voice"),
        horizontal=True,
        key=f"session_checkin_method_{student_id}",
    )
    share_location = st.checkbox(
        "Share my current location with my teacher (optional)",
        key=f"share_checkin_location_{student_id}",
    )
    location = None
    if share_location:
        from streamlit_geolocation import streamlit_geolocation

        location = streamlit_geolocation()
        st.caption(
            "Location is sent only with this request. You can continue without "
            "a GPS fix by turning this option off."
        )

    latitude = longitude = accuracy = None
    if isinstance(location, dict):
        try:
            latitude = float(location["latitude"])
            longitude = float(location["longitude"])
            accuracy_value = location.get("accuracy")
            accuracy = float(accuracy_value) if accuracy_value is not None else None
            if (
                not math.isfinite(latitude)
                or not math.isfinite(longitude)
                or not -90 <= latitude <= 90
                or not -180 <= longitude <= 180
                or (
                    accuracy is not None
                    and (not math.isfinite(accuracy) or accuracy < 0)
                )
            ):
                raise ValueError("Invalid location")
        except (KeyError, TypeError, ValueError):
            latitude = longitude = accuracy = None

    if share_location and latitude is not None:
        st.caption(
            f"GPS fix available (reported accuracy: {accuracy:.0f} m)."
            if accuracy is not None
            else "GPS fix available."
        )
    elif share_location:
        st.info(
            "Waiting for a GPS fix. Turn off location sharing to continue "
            "without sending location."
        )

    if method == "Face":
        face_consent = st.checkbox(
            "I consent to checking this photo against my saved face profile.",
            key=f"face_checkin_consent_{student_id}",
            disabled=not student_data.get("face_embedding"),
        )
        if not student_data.get("face_embedding"):
            st.info(
                "There is no saved face profile for this account. Use voice "
                "verification or ask your teacher for help."
            )
        photo = st.camera_input(
            "Take a fresh photo for this check-in",
            key=f"class_checkin_camera_{student_id}",
            disabled=not face_consent,
        )
        if st.button(
            "Verify and check in",
            type="primary",
            width="stretch",
            disabled=(
                not access_code.isdigit()
                or len(access_code) != 8
                or not face_consent
                or photo is None
                or (share_location and latitude is None)
            ),
            key=f"face_checkin_submit_{student_id}",
        ):
            from src.database.db import submit_class_checkin
            from src.pipelines.face_pipeline import measure_face_match

            with st.spinner("Checking your face..."):
                image = np.asarray(
                    Image.open(photo).convert("RGB")
                )
                distance, face_count = measure_face_match(
                    image, student_data["face_embedding"]
                )
                if face_count != 1:
                    st.warning(
                        "Keep only your face in the frame. You can try again or "
                        "choose voice verification."
                    )
                    return
                from src.pipelines.face_matching import FACE_MATCH_THRESHOLD

                if (
                    distance is None
                    or not math.isfinite(distance)
                    or distance > FACE_MATCH_THRESHOLD
                ):
                    st.warning(
                        "The photo did not match your saved profile. Try again "
                        "with good lighting or use voice verification."
                    )
                    return
                try:
                    checkin = submit_class_checkin(
                        access_code,
                        student_id,
                        "face",
                        distance,
                        latitude=latitude,
                        longitude=longitude,
                        location_accuracy_m=accuracy,
                    )
                except Exception as error:
                    st.error(f"Check-in could not be submitted: {error}")
                    return
            _show_checkin_result(checkin)

    else:
        voice_consent = st.checkbox(
            "I consent to checking this recording against my voice profile.",
            key=f"voice_checkin_consent_{student_id}",
        )
        voice_profile = student_data.get("voice_embedding")
        if voice_profile:
            profile_audio = None
        else:
            st.info(
                "No voice profile is saved. You may create one using two "
                "separate recordings; only the numeric voice template is saved."
            )
            profile_audio = st.audio_input(
                "Record a voice profile sample",
                key=f"checkin_voice_profile_{student_id}",
                disabled=not voice_consent,
            )
        attendance_audio = st.audio_input(
            "Record a fresh sample for this check-in",
            key=f"checkin_voice_sample_{student_id}",
            disabled=not voice_consent,
        )
        if st.button(
            "Verify voice and check in",
            type="primary",
            width="stretch",
            disabled=(
                not access_code.isdigit()
                or len(access_code) != 8
                or not voice_consent
                or attendance_audio is None
                or (not voice_profile and profile_audio is None)
                or (share_location and latitude is None)
            ),
            key=f"voice_checkin_submit_{student_id}",
        ):
            from src.database.db import (
                save_student_voice_profile,
                submit_class_checkin,
            )
            from src.pipelines.voice_pipeline import (
                get_voice_embedding,
                identify_speaker,
            )

            with st.spinner("Checking your voice..."):
                if not voice_profile:
                    voice_profile = get_voice_embedding(profile_audio.getvalue())
                attendance_embedding = get_voice_embedding(
                    attendance_audio.getvalue()
                )
                if voice_profile is None or attendance_embedding is None:
                    st.error("Voice analysis failed. Please record both samples again.")
                    return
                matched_id, score = identify_speaker(
                    attendance_embedding,
                    {student_id: voice_profile},
                )
                if matched_id != student_id or score < 0.65:
                    st.warning(
                        "The recording did not match the saved voice profile. "
                        "Try again or ask your teacher for help."
                    )
                    return
                try:
                    checkin = submit_class_checkin(
                        access_code,
                        student_id,
                        "voice",
                        float(score),
                        latitude=latitude,
                        longitude=longitude,
                        location_accuracy_m=accuracy,
                    )
                except Exception as error:
                    st.error(f"Check-in could not be submitted: {error}")
                    return
                if not student_data.get("voice_embedding"):
                    try:
                        updated_student = save_student_voice_profile(
                            student_id, voice_profile
                        )
                    except Exception as error:
                        st.error(
                            "Check-in was submitted, but the voice profile could "
                            f"not be saved: {error}"
                        )
                    else:
                        student_data.update(updated_student)
                        st.session_state.student_data.update(updated_student)
            _show_checkin_result(checkin)


def _show_checkin_result(checkin):
    if checkin["status"] == "pending":
        st.info(
            "Your match needs a quick teacher review. It will appear as pending "
            "until the teacher decides."
        )
    else:
        st.success("Check-in verified and attendance recorded.")
    if checkin.get("risk_flags"):
        st.caption(
            "Review flags: "
            + ", ".join(flag.replace("_", " ") for flag in checkin["risk_flags"])
        )


def student_screen():
    style_background_dashboard()
    style_base_layout()


    if "student_data" in st.session_state:
        student_dashboard()
        return
    
    c1, c2 = st.columns(2, vertical_alignment='center', gap='xxlarge')
    with c1:
        header_dashboard()
    with c2:
        if st.button("Go back to Home", type='secondary', key='loginbackbtn', shortcut="control+backspace"):
            st.session_state['show_student_registration'] = False
            navigate_to('home')

    st.header('Sign in to your student account', text_alignment='center')
    st.space()
    st.space()
    
    show_registration = st.session_state.get('show_student_registration', False)
    login_method = (
        'FaceID'
        if show_registration
        else st.radio(
            'Choose a sign-in method',
            ('FaceID', 'VoiceID'),
            horizontal=True,
            key='student_login_method',
        )
    )
    photo_source = None
    if login_method == 'FaceID':
        st.info(
            "FaceID compares a live camera image with your saved face template. "
            "Images are processed for matching and are not retained."
        )
        sign_in_consent = st.checkbox(
            "I consent to face verification for sign-in or profile setup.",
            key='student_face_signin_consent',
        )
        if not show_registration:
            from src.pipelines.face_pipeline import (
                get_trained_model,
                load_dlib_models,
            )

            with st.spinner('Preparing FaceID...'):
                load_dlib_models()
                get_trained_model()

        photo_source = st.camera_input(
            "Position your face in the center",
            disabled=not sign_in_consent,
        )

        if not show_registration and st.button(
            "Register or re-enroll instead",
            key="register_student_profile",
        ):
            st.session_state['show_student_registration'] = True
            st.rerun()

        if photo_source and not show_registration:
            import numpy as np
            from PIL import Image

            from src.pipelines.face_pipeline import identify_student

            img = np.array(Image.open(photo_source))

            with st.spinner('AI is scanning..'):
                student, num_faces = identify_student(img)

                if num_faces == 0:
                    st.warning(
                        'Face not detected. Adjust the lighting and center your '
                        'face; you can still register below.'
                    )
                    show_registration = True
                elif num_faces > 1:
                    st.warning('Multiple faces found. Keep only your face in the frame.')
                elif student:
                    from src.database.db import record_student_biometric_consent

                    record_student_biometric_consent(
                        student['student_id'], 'face'
                    )
                    st.session_state.is_logged_in = True
                    st.session_state.user_role = 'student'
                    st.session_state.student_data = student
                    st.toast(f'Welcome Back {student["name"]}')
                    st.rerun()
                else:
                    st.info('Face not recognized! Register your profile below.')
                    show_registration = True
    else:
        st.info(
            "VoiceID can sign in using an enrolled voice profile. Recordings are "
            "processed for matching and are not retained."
        )
        voice_consent = st.checkbox(
            "I consent to voice biometric processing for sign-in.",
            key='student_voice_signin_consent',
        )
        voice_audio = st.audio_input(
            "Record a fresh voice sample",
            disabled=not voice_consent,
            key='student_voice_signin_audio',
        )
        if st.button(
            "Verify voice and sign in",
            type='primary',
            disabled=not voice_consent or voice_audio is None,
            key='student_voice_signin_submit',
        ):
            from src.database.db import get_all_students
            from src.pipelines.voice_pipeline import (
                get_voice_embedding,
                identify_speaker,
            )

            with st.spinner('Checking your voice...'):
                embedding = get_voice_embedding(voice_audio.getvalue())
                students = get_all_students()
                voice_profiles = {
                    student['student_id']: student['voice_embedding']
                    for student in students
                    if student.get('voice_embedding')
                }
                student_id, score = identify_speaker(
                    embedding,
                    voice_profiles,
                    threshold=0.8,
                )
            if student_id is None:
                st.warning(
                    "Voice was not confidently matched to an enrolled profile. "
                    "Try again or use FaceID."
                )
            else:
                from src.database.db import record_student_biometric_consent

                record_student_biometric_consent(student_id, 'voice')
                student = next(
                    student
                    for student in students
                    if student['student_id'] == student_id
                )
                st.session_state.is_logged_in = True
                st.session_state.user_role = 'student'
                st.session_state.student_data = student
                st.toast(f'Welcome back {student["name"]}')
                st.rerun()
    if show_registration:
        with st.container(border=True):
            st.header('Register new Profile')
            st.info(
                "Your face embedding is stored for FaceID sign-in and matching; "
                "the captured photo is not retained. Voice enrollment is optional "
                "and stores a numeric template, not the recording."
            )
            if not photo_source:
                st.info('Take a clear face photo above to create your profile.')
            new_name = st.text_input("Enter your name", placeholder='E.g. Hamza Rizvi')

            st.subheader('Optional : Voice Enrollment')
            st.info("Voice enrollment can be used as an alternative check-in method.")
            face_consent = st.checkbox(
                "I consent to face biometric processing to create my account."
            )
            voice_consent = st.checkbox(
                "I also consent to voice biometric processing (optional)."
            )


            audio_data = None

            try:
                if voice_consent:
                    audio_data = st.audio_input('Record a short phrase for voice enrollment.')
            except Exception:
                st.error('Voice recording could not be captured.')

            if st.button(
                'Create Account',
                type='primary',
                disabled=not photo_source or not face_consent,
            ):
                if new_name:
                    with st.spinner('Creating profile..'):
                        import numpy as np
                        from PIL import Image

                        from src.database.db import create_student
                        from src.pipelines.face_pipeline import (
                            get_face_embeddings,
                            train_classifier,
                        )
                        from src.pipelines.voice_pipeline import get_voice_embedding

                        img = np.array(Image.open(photo_source))
                        encodings= get_face_embeddings(img)
                        if len(encodings) == 1:
                            face_emb = encodings[0].tolist()

                            voice_emb = None
                            if audio_data and voice_consent:
                                voice_emb = get_voice_embedding(audio_data.getvalue())

                            response_data = create_student(
                                new_name,
                                face_embedding=face_emb,
                                voice_embedding=voice_emb,
                                face_consent=face_consent,
                                voice_consent=voice_consent,
                            )

                            if response_data:
                                train_classifier()
                                st.session_state.is_logged_in = True
                                st.session_state.user_role = 'student'
                                st.session_state.student_data = response_data[0]
                                st.session_state['show_student_registration'] = False
                                st.toast(f'Profile Created! Hi {new_name}!')
                                st.rerun()
                        elif len(encodings) > 1:
                            st.error('Only one face should be visible to register.')
                        else:
                            st.error(
                                'Face not detected in this photo. Retake it with your '
                                'face centered, well lit, and clearly visible.'
                            )

                else:
                    st.warning('Please enter your name!')


        