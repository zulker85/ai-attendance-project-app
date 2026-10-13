from hashlib import sha256

import streamlit as st


@st.dialog("Voice check-in")
def student_voice_attendance_dialog(subject, student):
    student_id = student["student_id"]
    subject_id = subject["subject_id"]
    verification_key = f"voice_checkin_verification_{student_id}_{subject_id}"

    st.write(
        f"Submit a fresh voice check-in for **{subject['name']}** using the "
        "short-lived code displayed by your teacher. Your teacher can review "
        "borderline matches. This voice dialog does not request your location; "
        "use Live class check-in above if you want to share optional GPS."
    )
    access_code = st.text_input(
        "Class access code",
        max_chars=8,
        key=f"voice_session_code_{student_id}_{subject_id}",
    ).strip()
    consent = st.checkbox(
        "I consent to matching this recording against my voice profile and "
        "sharing the match result with my teacher.",
        key=f"voice_session_consent_{student_id}_{subject_id}",
    )
    voice_profile = student.get("voice_embedding")
    profile_audio = None
    if not voice_profile:
        st.info(
            "No voice profile is saved. To use this option, create one with "
            "a profile recording and a separate check-in recording. Only the "
            "numeric voice template is saved."
        )
        profile_audio = st.audio_input(
            "Record a voice profile sample",
            key=f"voice_profile_enrollment_{student_id}",
            disabled=not consent,
        )

    attendance_audio = st.audio_input(
        "Record a fresh check-in sample",
        key=f"voice_attendance_sample_{student_id}_{subject_id}",
        disabled=not consent,
    )

    profile_audio_bytes = profile_audio.getvalue() if profile_audio else None
    attendance_audio_bytes = (
        attendance_audio.getvalue() if attendance_audio else None
    )
    profile_audio_digest = (
        sha256(profile_audio_bytes).hexdigest()
        if profile_audio_bytes is not None
        else None
    )
    attendance_audio_digest = (
        sha256(attendance_audio_bytes).hexdigest()
        if attendance_audio_bytes is not None
        else None
    )
    verification = st.session_state.get(verification_key)
    verification_is_current = (
        consent
        and attendance_audio_digest is not None
        and verification is not None
        and verification["attendance_audio_digest"] == attendance_audio_digest
        and verification["profile_audio_digest"] == profile_audio_digest
    )

    if st.button(
        "Check voice sample",
        disabled=(
            not consent
            or attendance_audio is None
            or (not voice_profile and profile_audio is None)
        ),
        key=f"check_voice_sample_{student_id}_{subject_id}",
    ):
        from src.pipelines.class_checkin import (
            VOICE_AUTO_APPROVE_SCORE,
            VOICE_REVIEW_SCORE,
        )
        from src.pipelines.voice_pipeline import (
            get_voice_embedding,
            identify_speaker,
        )

        with st.spinner("Checking your voice sample..."):
            if not voice_profile:
                voice_profile = get_voice_embedding(profile_audio_bytes)
            attendance_embedding = get_voice_embedding(attendance_audio_bytes)
            if voice_profile is None or attendance_embedding is None:
                st.error("Voice analysis failed. Please record both samples again.")
                return

            matched_student_id, score = identify_speaker(
                attendance_embedding,
                {student_id: voice_profile},
                threshold=VOICE_REVIEW_SCORE,
            )
            verification = {
                "attendance_audio_digest": attendance_audio_digest,
                "profile_audio_digest": profile_audio_digest,
                "matched": matched_student_id == student_id,
                "score": float(score),
                "voice_profile": voice_profile,
                "auto_approve_score": VOICE_AUTO_APPROVE_SCORE,
            }
            st.session_state[verification_key] = verification
            verification_is_current = True

    if verification_is_current:
        if verification["matched"]:
            st.success(
                f"Voice matched your profile "
                f"({verification['score']:.1%} similarity)."
            )
            if verification["score"] < verification["auto_approve_score"]:
                st.info(
                    "This is a borderline match and will need teacher review "
                    "after you submit."
                )
            else:
                st.caption("This match is strong enough for automatic approval.")
        else:
            similarity_message = (
                f" ({verification['score']:.1%} similarity)"
                if verification["score"] >= 0
                else ""
            )
            st.warning(
                "The recording did not match your saved voice profile"
                f"{similarity_message}. "
                "Please record a fresh sample or ask your teacher for help."
            )

    if st.button(
        "Verify voice and check in",
        type="primary",
        width="stretch",
        disabled=(
            not access_code.isdigit()
            or len(access_code) != 8
            or not consent
            or not verification_is_current
            or not verification["matched"]
        ),
        key=f"submit_voice_checkin_{student_id}_{subject_id}",
    ):
        from src.database.db import (
            save_student_voice_profile,
            submit_class_checkin,
        )

        with st.spinner("Submitting your voice check-in..."):
            if not voice_profile:
                voice_profile = verification["voice_profile"]

            try:
                checkin = submit_class_checkin(
                    access_code,
                    student_id,
                    "voice",
                    verification["score"],
                    subject_id=subject_id,
                )
            except Exception as error:
                st.error(f"Check-in could not be submitted: {error}")
                return

            if not student.get("voice_embedding"):
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
                    student.update(updated_student)
                    if (
                        st.session_state.get("student_data", {}).get("student_id")
                        == student_id
                    ):
                        st.session_state.student_data.update(updated_student)

        if checkin["status"] == "pending":
            st.info(
                "Your voice match needs a quick teacher review before attendance "
                "is recorded."
            )
        else:
            st.success("Voice check-in verified and attendance recorded.")
        st.rerun()
