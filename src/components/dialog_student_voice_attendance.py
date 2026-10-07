import streamlit as st
from streamlit_geolocation import streamlit_geolocation


@st.dialog("Submit Voice Attendance")
def student_voice_attendance_dialog(subject, student):
    st.write(
        f"Record your voice for **{subject['name']}**. "
        "Your voice-match score, submission time, and GPS location will be shared "
        "with your teacher for review."
    )

    location = streamlit_geolocation()
    if not isinstance(location, dict):
        st.info("Select the location button above and allow GPS access to continue.")
        latitude = longitude = accuracy = None
    else:
        latitude = location.get('latitude')
        longitude = location.get('longitude')
        accuracy = location.get('accuracy')

    try:
        latitude = float(latitude)
        longitude = float(longitude)
        accuracy = float(accuracy) if accuracy is not None else None
    except (TypeError, ValueError):
        latitude = longitude = accuracy = None

    has_location = (
        latitude is not None
        and longitude is not None
        and -90 <= latitude <= 90
        and -180 <= longitude <= 180
        and (accuracy is None or accuracy >= 0)
    )
    if has_location:
        st.caption(
            f"GPS fix received (accuracy: {accuracy} m)"
            if accuracy is not None
            else "GPS fix received."
        )
    else:
        st.warning("GPS location is required before you can submit.")

    voice_profile = student.get('voice_embedding')
    if not voice_profile:
        st.warning(
            "Your account has no saved voice profile. Enroll now with one "
            "recording, then provide a separate sample for this attendance request."
        )
        enrollment_audio = st.audio_input(
            "Record a voice profile sample",
            key=f"voice_profile_enrollment_{student['student_id']}",
        )
        attendance_audio = st.audio_input(
            "Record a fresh sample for attendance",
            key=f"voice_attendance_sample_{student['student_id']}",
        )
        if st.button(
            "Enroll voice and send attendance",
            type="primary",
            width="stretch",
            disabled=(
                not has_location
                or enrollment_audio is None
                or attendance_audio is None
            ),
        ):
            with st.spinner("Enrolling and matching your voice..."):
                from src.database.db import (
                    save_student_voice_profile,
                    submit_voice_attendance,
                )
                from src.pipelines.voice_pipeline import (
                    get_voice_embedding,
                    identify_speaker,
                )

                profile_embedding = get_voice_embedding(
                    enrollment_audio.getvalue()
                )
                attendance_embedding = get_voice_embedding(
                    attendance_audio.getvalue()
                )
                if profile_embedding is None or attendance_embedding is None:
                    st.error("Voice analysis failed. Please record both samples again.")
                    return

                matched_student_id, score = identify_speaker(
                    attendance_embedding,
                    {student['student_id']: profile_embedding},
                )
                if matched_student_id != student['student_id']:
                    st.error(
                        "The fresh attendance sample did not match the new voice "
                        "profile. Please record both samples again."
                    )
                    return

                updated_student = save_student_voice_profile(
                    student['student_id'],
                    profile_embedding,
                )
                student.update(updated_student)
                if (
                    st.session_state.get('student_data', {}).get('student_id')
                    == student['student_id']
                ):
                    st.session_state.student_data.update(updated_student)

                submit_voice_attendance(
                    student_id=student['student_id'],
                    student_name=student['name'],
                    subject_id=subject['subject_id'],
                    subject_name=subject['name'],
                    subject_code=subject['subject_code'],
                    voice_match_score=float(score),
                    latitude=latitude,
                    longitude=longitude,
                    location_accuracy_m=accuracy,
                )

            st.success("Voice profile enrolled and attendance sent to your teacher.")
            st.rerun()
        return

    audio_data = st.audio_input(
        "Record a short voice sample",
        key=f"voice_attendance_existing_{student['student_id']}",
    )
    if st.button(
        "Analyze and send to teacher",
        type="primary",
        width="stretch",
        disabled=not has_location or audio_data is None,
    ):
        with st.spinner("Matching your voice..."):
            from src.database.db import submit_voice_attendance
            from src.pipelines.voice_pipeline import (
                get_voice_embedding,
                identify_speaker,
            )

            embedding = get_voice_embedding(audio_data.getvalue())
            if embedding is None:
                st.error("Voice analysis failed. Please record again.")
                return

            matched_student_id, score = identify_speaker(
                embedding,
                {student['student_id']: voice_profile},
            )
            if matched_student_id != student['student_id']:
                st.error("Voice did not match your saved profile. Please try again.")
                return

            submit_voice_attendance(
                student_id=student['student_id'],
                student_name=student['name'],
                subject_id=subject['subject_id'],
                subject_name=subject['name'],
                subject_code=subject['subject_code'],
                voice_match_score=float(score),
                latitude=latitude,
                longitude=longitude,
                location_accuracy_m=accuracy,
            )

        st.success("Voice match sent to your teacher for approval.")
        st.rerun()
