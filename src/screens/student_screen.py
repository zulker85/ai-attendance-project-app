import streamlit as st

from src.components.header import header_dashboard
from src.components.subject_card import subject_card
from src.components.voice_input import voice_input
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
            st.session_state['student_face_scan_generation'] = (
                st.session_state.get('student_face_scan_generation', 0) + 1
            )
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

    _render_student_profile(student_data, logs)
    _render_multipose_face_enrollment(student_data)
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

    _render_recent_checkins(logs)
    _render_student_exam_portal(student_id)
    _render_exam_results(student_id)


def _render_student_exam_portal(student_id):
    from src.database.db import (
        get_available_exams_for_student,
        get_student_exam_attempts,
        submit_student_exam_attempt,
    )
    from src.pipelines.exam_marking import (
        calculate_exam_result,
        validate_student_answers,
    )
    from src.pipelines.paper_pipeline import (
        decode_storage_paths,
        download_stored_pages,
        evaluate_configured_exam,
    )

    st.divider()
    st.subheader("Online examinations")
    try:
        exams = get_available_exams_for_student(student_id)
        attempts = get_student_exam_attempts(student_id)
    except Exception as error:
        st.error(f"Could not load online examinations: {error}")
        return

    if attempts:
        with st.expander("Your submitted exams", expanded=False):
            for attempt in attempts:
                exam = attempt.get("exam_papers") or {}
                subject = exam.get("subjects") or {}
                st.markdown(
                    f"**{exam.get('title', 'Exam')}** · "
                    f"{subject.get('name', 'Subject')} "
                    f"({subject.get('subject_code', '')})"
                )
                if attempt["status"] == "verified":
                    st.success(
                        f"Verified: {attempt.get('final_marks')} / "
                        f"{exam.get('max_marks')}"
                    )
                else:
                    st.info("Submitted; waiting for teacher review.")

    if not exams:
        st.info("No new online exams are currently available for your subjects.")
        return

    for exam in exams:
        scheme = exam["marking_scheme"]
        subject = exam.get("subjects") or {}
        with st.container(border=True):
            st.markdown(
                f"### {exam['title']} · {subject.get('name', 'Subject')} "
                f"({subject.get('subject_code', '')})"
            )
            st.caption(
                f"Total: {exam['max_marks']} marks · One submission per exam."
            )
            paper_path = exam.get("question_paper_path")
            if paper_path:
                with st.expander("View question paper"):
                    try:
                        pages = download_stored_pages(
                            decode_storage_paths(paper_path)
                        )
                        for page_index, page in enumerate(pages, start=1):
                            st.image(
                                page,
                                caption=f"Question paper page {page_index}",
                            )
                    except Exception as error:
                        st.warning(f"Could not display the question paper: {error}")

            for module in scheme.get("modules", []):
                st.markdown(
                    f"**{module['name']} — {module['max_marks']} marks**"
                )
                for group in module.get("or_groups", []):
                    st.info(
                        f"OR group {group['label']}: answer whichever "
                        f"alternative(s) you attempt. If you answer more than "
                        f"{group['allowed_attempts']}, each is evaluated "
                        "separately and only the highest-scoring permitted "
                        "alternative(s) count."
                    )
                for question in module.get("questions", []):
                    if question.get("or_group_id"):
                        st.caption(
                            f"{question['label']} — {question['max_marks']} marks "
                            f"(OR group {question['or_group_id']}; evaluated separately)"
                        )
                    else:
                        st.caption(
                            f"{question['label']} — {question['max_marks']} marks"
                            + (" · Compulsory" if question.get("compulsory") else "")
                        )
                    for subquestion in question.get("subquestions", []):
                        st.caption(
                            f"{subquestion['label']} — "
                            f"{subquestion['max_marks']} marks"
                        )

            with st.form(f"student_exam_attempt_{exam['exam_id']}"):
                answer_text = {}
                for module in scheme.get("modules", []):
                    st.subheader(
                        f"{module['name']} · {module['max_marks']} marks"
                    )
                    for question in module.get("questions", []):
                        st.markdown(
                            f"**{question['label']} · {question['max_marks']} marks**"
                        )
                        if question.get("or_group_id"):
                            st.caption(
                                "Alternative question; its answers are scored "
                                "separately from the other OR alternatives."
                            )
                        targets = question.get("subquestions", [])
                        if targets:
                            for subquestion in targets:
                                answer_text[subquestion["subquestion_id"]] = (
                                    st.text_area(
                                        f"Answer {subquestion['label']} "
                                        f"({subquestion['max_marks']} marks)",
                                        key=(
                                            f"student_answer_{exam['exam_id']}_"
                                            f"{subquestion['subquestion_id']}"
                                        ),
                                        height=120,
                                    )
                                )
                        else:
                            answer_text[question["question_id"]] = st.text_area(
                                f"Answer {question['label']} "
                                f"({question['max_marks']} marks)",
                                key=(
                                    f"student_answer_{exam['exam_id']}_"
                                    f"{question['question_id']}"
                                ),
                                height=140,
                            )
                confirmed = st.checkbox(
                    "I have reviewed my answers and understand the OR scoring rule.",
                    key=f"student_exam_confirm_{exam['exam_id']}",
                )
                submitted = st.form_submit_button(
                    "Submit examination",
                    type="primary",
                    disabled=not confirmed,
                )
            if submitted:
                answers = {
                    "answers": answer_text,
                    "selected_alternatives": {},
                }
                try:
                    answers = validate_student_answers(scheme, answers)
                    with st.spinner("Evaluating your answers..."):
                        target_scores = evaluate_configured_exam(
                            scheme,
                            text_answers=answers["answers"],
                        )
                        result = calculate_exam_result(
                            scheme,
                            target_scores,
                        )
                        submit_student_exam_attempt(
                            exam["exam_id"],
                            student_id,
                            answers,
                            result,
                        )
                except Exception as error:
                    st.error(f"Could not submit this examination: {error}")
                else:
                    st.success(
                        "Your answers were submitted and evaluated. The teacher "
                        "will review the result before it is published."
                    )
                    st.rerun()


def _render_exam_results(student_id):
    from src.database.db import get_verified_paper_results

    st.divider()
    st.subheader("Exam Results")
    try:
        results = get_verified_paper_results(student_id)
    except Exception as error:
        st.error(f"Could not load your verified exam results: {error}")
        return
    if not results:
        st.info(
            "No verified exam scores were found for your account "
            f"(Student ID #ST-{student_id})."
        )
        return

    for result in results:
        exam = result.get("exam_papers") or {}
        subject = exam.get("subjects") or {}
        with st.container(border=True):
            st.markdown(
                f"**{exam.get('title', 'Exam')}** · "
                f"{subject.get('name', 'Subject')} "
                f"({subject.get('subject_code', '')})"
            )
            question_paper_path = exam.get("question_paper_path")
            if question_paper_path:
                with st.expander("View question paper"):
                    try:
                        from src.pipelines.paper_pipeline import (
                            decode_storage_paths,
                            download_stored_pages,
                        )

                        question_pages = download_stored_pages(
                            decode_storage_paths(question_paper_path)
                        )
                        for page_index, question_page in enumerate(
                            question_pages, start=1
                        ):
                            st.image(
                                question_page,
                                caption=f"Question paper page {page_index}",
                            )
                    except Exception as error:
                        st.warning(
                            "The question paper could not be displayed: "
                            f"{error}"
                        )
            st.metric(
                "Verified score",
                f"{result.get('final_marks')} / {exam.get('max_marks')}",
            )
            st.caption(f"Published {result.get('reviewed_at')}")
            details = result.get("evaluation_details") or []
            if isinstance(details, dict) and "modules" in details:
                for module in details["modules"]:
                    with st.expander(
                        f"{module['name']} · {module['awarded_marks']} / "
                        f"{module['max_marks']} marks"
                    ):
                        for question in module["questions"]:
                            counted = (
                                " · counted"
                                if question.get("counted_for_score")
                                else " · alternative not counted"
                                if question.get("or_group_id")
                                else ""
                            )
                            st.markdown(
                                f"**{question['question_no']}** · "
                                f"{question['awarded_marks']} / "
                                f"{question['max_marks']} marks{counted}"
                            )
                            for subquestion in question.get("subquestions", []):
                                st.caption(
                                    f"{subquestion['question_no']} · "
                                    f"{subquestion['awarded_marks']} / "
                                    f"{subquestion['max_marks']} marks · "
                                    f"{subquestion['semantic_match_pct']}% match"
                                )
                                st.caption(subquestion.get("feedback", ""))
            else:
                with st.expander("Question-wise feedback"):
                    for question in details:
                        st.markdown(
                            f"**Question {question['question_no']}** · "
                            f"{question['awarded_marks']} / {question['max_marks']} "
                            f"({question['semantic_match_pct']}% semantic match)"
                        )
                        st.caption(question.get("feedback", ""))


def _render_student_profile(student_data, logs):
    import pandas as pd

    present_count = sum(bool(log.get("is_present")) for log in logs)
    held_count = len(logs)
    attendance_rate = (100 * present_count / held_count) if held_count else 0
    dated_logs = [
        log
        for log in logs
        if log.get("timestamp")
    ]
    dated_logs.sort(
        key=lambda log: pd.to_datetime(log["timestamp"], errors="coerce", utc=True),
        reverse=True,
    )
    attendance_streak = 0
    for log in dated_logs:
        if not log.get("is_present"):
            break
        attendance_streak += 1

    st.subheader("Student profile")
    st.markdown(
        f"**{student_data['name']}** · Student ID "
        f"`#ST-{student_data['student_id']}` · "
        f"{'On track' if attendance_rate >= 75 else 'Needs attention'}"
    )
    first, second, third, fourth = st.columns(4)
    first.metric("Attendance", f"{attendance_rate:.1f}%")
    second.metric("Classes attended", f"{present_count} / {held_count}")
    third.metric("Current streak", f"{attendance_streak} classes")
    fourth.metric(
        "Face profile",
        "Calibrated" if student_data.get("face_embedding") else "Not enrolled",
    )
    st.caption(
        "Voice profile: Enrolled"
        if student_data.get("voice_embedding")
        else "Voice profile: Not enrolled"
    )


def _render_recent_checkins(logs):
    import pandas as pd

    st.subheader("Recent check-ins")
    if not logs:
        st.info("Your check-in history will appear here after your first class.")
        return

    history = []
    for log in logs:
        subject = log.get("subjects") or {}
        timestamp = pd.to_datetime(log.get("timestamp"), errors="coerce", utc=True)
        history.append(
            {
                "Timestamp": timestamp,
                "Course": (
                    f"{subject.get('subject_code', '')} — "
                    f"{subject.get('name', 'Course')}"
                ).strip(" —"),
                "Status": "Present" if log.get("is_present") else "Absent",
                "Verification": log.get("verification_method", "Attendance record"),
            }
        )
    recent = pd.DataFrame(history).sort_values("Timestamp", ascending=False).head(10)
    recent["Timestamp"] = (
        recent["Timestamp"].dt.tz_convert(None).dt.strftime("%Y-%m-%d %H:%M")
    )
    st.dataframe(recent, width="stretch", hide_index=True)


def check_pose_orientation(pose, yaw, detected_pose_label=None):
    """Return True if the measured yaw falls in the approximate zone for the requested pose.

    Zones are intentionally wide so a natural, comfortable head turn is enough.
    No strict angle or asymmetry requirements — any reasonable turn is accepted.
    """
    if yaw is None:
        return False
    if pose == "front":
        # Broadly facing camera — within ±25°
        return abs(yaw) <= 20
    if pose == "left":
        # Accept slight left turns, including measurements that are close to front.
        return -65 < yaw <= -10
    if pose == "right":
        # Accept slight right turns, including measurements near 10-15 degrees.
        return 10 <= yaw < 65
    if pose == "left_profile":
        # Ear starting to face camera — just past ~40° is enough, no 90° needed
        return yaw <= -65 or detected_pose_label == "left_profile"
    if pose == "right_profile":
        return yaw >= 65 or detected_pose_label == "right_profile"
    return False


def get_pose_capture_feedback(pose, analysis):
    if not analysis:
        return "Could not process image. Please capture again."
    face_count = analysis.get("face_count", 0)
    if face_count == 0:
        return (
            "No face detected. Make sure your full head (forehead to chin) is inside "
            "the frame with good lighting. Step back 1–2 feet if the face touches the borders."
        )
    if face_count > 1:
        return f"{face_count} faces detected. Please ensure only one person is in the camera frame."

    if not analysis.get("valid", False):
        brightness = analysis.get("brightness", 0.0)
        sharpness = analysis.get("sharpness", 0.0)
        face_ratio = analysis.get("face_ratio", 0.0)
        reasons = []
        if brightness < 30:
            reasons.append(f"lighting is too dim (brightness {brightness:.1f})")
        if sharpness < 2.0:
            reasons.append(f"image is blurry (sharpness {sharpness:.1f})")
        if face_ratio < 0.008:
            reasons.append("face is too far away")
        reason_str = ", ".join(reasons) if reasons else "quality parameters unmet"
        return f"Image quality is too low: {reason_str}. Face a light source, hold steady, and retake."

    yaw = analysis.get("yaw_degrees", 0.0)
    if check_pose_orientation(
        pose,
        yaw,
        detected_pose_label=analysis.get("pose_label"),
    ):
        if pose in {"left", "right"}:
            eye_width_ratio = analysis.get("eye_width_ratio")
            if eye_width_ratio is not None and eye_width_ratio < 1.18:
                if pose == "left":
                    return "Turn slightly further left so the right ear and cheek become visible."
                return "Turn slightly further right so the left ear and cheek become visible."
        return None  # accepted — no additional asymmetry gate

    # Simple directional guidance only
    if pose == "front":
        direction = "left" if yaw < -25 else "right"
        return f"Turn your head back toward the camera — you are facing too far {direction} ({abs(yaw):.0f}°)."
    if pose == "left":
        if yaw >= -15:
            return "Your head is still too centered. Turn gently to the LEFT — just enough to see your left cheek."
        if yaw >= -30:
            return "Your head is still too centered. Turn left a little more."
        if yaw < -65:
            return "Turned too far into full profile. Ease back slightly toward the left."
        return "That is too far left. Ease back a little so your face is still mostly visible."
    if pose == "right":
        if yaw <= 15:
            return "Turn your head gently to the RIGHT — just enough so the camera sees your right cheek."
        if yaw > 65:
            return "Turned too far into full profile. Ease back slightly toward the right."
        return "That is too far right. Ease back a little so your face is still mostly visible."
    if pose == "left_profile":
        return (
            "Turn your head further LEFT — aim for your right ear facing the camera. "
            "A comfortable ~45° turn is enough, you do NOT need a full 90°."
        )
    if pose == "right_profile":
        return (
            "Turn your head further RIGHT — aim for your left ear facing the camera. "
            "A comfortable ~45° turn is enough, you do NOT need a full 90°."
        )
    return f"Adjust your head angle (currently {yaw:.0f}°) and retake."


def _get_pose_camera_config(pose):
    configs = {
        "front": {
            "title": "Front View",
            "hud_title": "● LOOK STRAIGHT AT THE CAMERA LENS ●",
            "hud_subtitle": "Keep your chin level, shoulders relaxed, and face centered",
            "in_image_instruction": "● LOOK DIRECTLY INTO CAMERA LENS (0°) ●",
            "camera_label": "📷 Front Pose: Look straight into the camera lens (chin level)",
            "framing_tip": "📏 Step back 1.5–2 ft until your entire head (forehead to chin) is inside the frame with space above your hair.",
            "gradient": "linear-gradient(90deg, #1e3a8a, #0284c7)",
            "hud_bg": "rgba(2, 132, 199, 0.95)",
            "border_color": "#38bdf8",
            "arrow_icon": "●",
        },
        "left": {
            "title": "Slight Left View",
            "hud_title": "⟵ ⟵ TURN HEAD TO YOUR LEFT (~30°) ⟵ ⟵",
            "hud_subtitle": "Point your nose toward the LEFT edge of your screen · Keep both eyes visible",
            "in_image_instruction": "⟵ TURN HEAD LEFT (~30°) · Point nose this way ⟵",
            "camera_label": "📷 Slight Left: Turn head ~30° toward the LEFT edge of your screen",
            "framing_tip": "⚠️ Turn only ~30° (do not turn into a full profile). Both eyes and right cheek must be visible.",
            "gradient": "linear-gradient(90deg, #0f766e, #0d9488)",
            "hud_bg": "rgba(13, 148, 136, 0.95)",
            "border_color": "#2dd4bf",
            "arrow_icon": "⟵",
        },
        "right": {
            "title": "Slight Right View",
            "hud_title": "⟶ ⟶ TURN HEAD TO YOUR RIGHT (~30°) ⟶ ⟶",
            "hud_subtitle": "Point your nose toward the RIGHT edge of your screen · Keep both eyes visible",
            "in_image_instruction": "⟶ TURN HEAD RIGHT (~30°) · Point nose this way ⟶",
            "camera_label": "📷 Slight Right: Turn head ~30° toward the RIGHT edge of your screen",
            "framing_tip": "⚠️ Turn only ~30° (do not turn into a full profile). Both eyes and left cheek must be visible.",
            "gradient": "linear-gradient(90deg, #b45309, #d97706)",
            "hud_bg": "rgba(217, 119, 6, 0.95)",
            "border_color": "#fbbf24",
            "arrow_icon": "⟶",
        },
        "left_profile": {
            "title": "Full Left Profile",
            "hud_title": "⟵ ⟵ ⟵ FULL LEFT PROFILE (TURN LEFT 90°) ⟵ ⟵ ⟵",
            "hud_subtitle": "Turn head left until your left ear faces the camera (side profile only)",
            "in_image_instruction": "⟵⟵ TURN TO FULL LEFT PROFILE (90°) ⟵⟵",
            "camera_label": "📷 Left Profile: Turn head fully left so left ear faces camera",
            "framing_tip": "📏 Keep head inside the frame so the profile curve of nose and chin is visible.",
            "gradient": "linear-gradient(90deg, #4c1d95, #6d28d9)",
            "hud_bg": "rgba(109, 40, 217, 0.95)",
            "border_color": "#a78bfa",
            "arrow_icon": "⟵⟵",
        },
        "right_profile": {
            "title": "Full Right Profile",
            "hud_title": "⟶ ⟶ ⟶ FULL RIGHT PROFILE (TURN RIGHT 90°) ⟶ ⟶ ⟶",
            "hud_subtitle": "Turn head right until your right ear faces the camera (side profile only)",
            "in_image_instruction": "⟶⟶ TURN TO FULL RIGHT PROFILE (90°) ⟶⟶",
            "camera_label": "📷 Right Profile: Turn head fully right so right ear faces camera",
            "framing_tip": "📏 Keep head inside the frame so the profile curve of nose and chin is visible.",
            "gradient": "linear-gradient(90deg, #831843, #be185d)",
            "hud_bg": "rgba(190, 24, 93, 0.95)",
            "border_color": "#f472b6",
            "arrow_icon": "⟶⟶",
        },
    }
    return configs.get(pose, configs["front"])


def _render_camera_hud_header(cfg):
    st.markdown(
        f"""
        <style>
        [data-testid="stCameraInput"],
        [data-testid="stCameraInputWebcamComponent"],
        [data-testid="stCameraInputWebcamStyledBox"] {{
            position: relative !important;
        }}
        [data-testid="stCameraInputWebcamStyledBox"]::before,
        [data-testid="stCameraInputWebcamComponent"]::before {{
            content: "" !important;
            position: absolute !important;
            top: 6% !important;
            left: 50% !important;
            transform: translateX(-50%) !important;
            width: 215px !important;
            height: 275px !important;
            border: 3px dashed {cfg['border_color']} !important;
            border-radius: 50% 50% 48% 48% / 58% 58% 42% 42% !important;
            pointer-events: none !important;
            z-index: 100 !important;
            box-shadow: 0 0 0 9999px rgba(10, 15, 26, 0.42) !important;
        }}
        [data-testid="stCameraInputWebcamStyledBox"]::after,
        [data-testid="stCameraInputWebcamComponent"]::after {{
            content: "{cfg['in_image_instruction']}" !important;
            position: absolute !important;
            top: 14px !important;
            left: 50% !important;
            transform: translateX(-50%) !important;
            background: {cfg['hud_bg']} !important;
            color: #ffffff !important;
            padding: 7px 18px !important;
            border-radius: 999px !important;
            border: 2.5px solid {cfg['border_color']} !important;
            font-size: 0.92rem !important;
            font-weight: 800 !important;
            letter-spacing: 0.04em !important;
            z-index: 101 !important;
            pointer-events: none !important;
            box-shadow: 0 4px 16px rgba(0, 0, 0, 0.75) !important;
            white-space: nowrap !important;
            text-align: center !important;
            text-shadow: 0 1px 3px rgba(0, 0, 0, 0.9) !important;
        }}
        </style>
        <div style="background:{cfg['gradient']};color:white;padding:0.75rem 1rem;
                    border-radius:12px 12px 0 0;border:2px solid {cfg['border_color']};
                    border-bottom:none;margin-top:0.6rem;box-shadow:0 4px 15px rgba(0,0,0,0.3)">
            <div style="font-size:1.15rem;font-weight:800;letter-spacing:0.04em;text-align:center;text-shadow:0 2px 4px rgba(0,0,0,0.6)">
                {cfg['hud_title']}
            </div>
            <div style="font-size:0.88rem;opacity:0.95;text-align:center;margin-top:0.25rem;font-weight:500">
                {cfg['hud_subtitle']}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_camera_hud_footer(cfg):
    st.markdown(
        f"""
        <div style="background:var(--sa-raised-surface, #1e293b);border:1px solid var(--sa-border, #334155);
                    border-radius:0 0 12px 12px;padding:0.55rem 0.9rem;margin-top:-0.3rem;margin-bottom:0.8rem;
                    font-size:0.85rem;color:var(--sa-muted, #94a3b8);text-align:center">
            {cfg['framing_tip']}
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_face_pose_guide(pose):
    configs = {
        "front": {
            "title": "Front View",
            "badge": "Center & Level (0°)",
            "instruction": "Look directly into the camera lens with your chin level and shoulders squared.",
            "tip": "Align your eyes with the eye-line marker and keep your forehead and chin fully inside the oval.",
            "arrow": "●",
            "angle_cue": "0° Center",
            "nose_target": 42,
        },
        "left": {
            "title": "Slight Left View",
            "badge": "Turn Head Left (25°–45°)",
            "instruction": "Turn your head gently to your left until your nose points toward the left edge of your screen.",
            "tip": "Turn only ~30°. Keep both eyes and your right cheek clearly visible in the preview.",
            "arrow": "⟵",
            "angle_cue": "~30° Left",
            "nose_target": 26,
        },
        "right": {
            "title": "Slight Right View",
            "badge": "Turn Head Right (25°–45°)",
            "instruction": "Turn your head gently to your right until your nose points toward the right edge of your screen.",
            "tip": "Turn only ~30°. Keep both eyes and your left cheek clearly visible in the preview.",
            "arrow": "⟶",
            "angle_cue": "~30° Right",
            "nose_target": 58,
        },
        "left_profile": {
            "title": "Full Left Profile",
            "badge": "Left Profile (~90°)",
            "instruction": "Turn your head fully to your left so your left ear faces the camera.",
            "tip": "Keep your head inside the frame so the profile outline of your nose and cheek are captured.",
            "arrow": "⟵⟵",
            "angle_cue": "90° Left",
            "nose_target": 14,
        },
        "right_profile": {
            "title": "Full Right Profile",
            "badge": "Right Profile (~90°)",
            "instruction": "Turn your head fully to your right so your right ear faces the camera.",
            "tip": "Keep your head inside the frame so the profile outline of your nose and cheek are captured.",
            "arrow": "⟶⟶",
            "angle_cue": "90° Right",
            "nose_target": 70,
        },
    }
    cfg = configs.get(pose, configs["front"])
    badge_text = cfg["badge"]
    instruction = cfg["instruction"]
    tip = cfg["tip"]
    arrow = cfg["arrow"]
    nose_x = cfg["nose_target"]
    angle_cue = cfg["angle_cue"]

    st.markdown(
        f"""
        <style>
        [data-testid="stCameraInput"] {{
            position: relative;
            max-width: 580px;
            margin: 0.5rem auto 1rem;
        }}
        [data-testid="stCameraInput"] > div:first-child {{
            position: relative;
            border-radius: 14px;
            overflow: hidden;
            border: 2px solid var(--sa-border, #334155);
        }}
        /* Cutout oval guide on camera preview */
        [data-testid="stCameraInput"] > div:first-child::before {{
            content: "";
            position: absolute;
            top: 7%;
            left: 50%;
            transform: translateX(-50%);
            width: 210px;
            height: 270px;
            border: 2.5px dashed #38bdf8;
            border-radius: 50% 50% 48% 48% / 58% 58% 42% 42%;
            pointer-events: none;
            z-index: 10;
            box-shadow: 0 0 0 9999px rgba(10, 15, 26, 0.35);
        }}
        /* Eye-level indicator line */
        [data-testid="stCameraInput"] > div:first-child::after {{
            content: "▲ ALIGN EYES HERE · {badge_text} ▲";
            position: absolute;
            top: 32%;
            left: 50%;
            transform: translateX(-50%);
            color: #e0f2fe;
            background: rgba(14, 165, 233, 0.65);
            font-size: 0.68rem;
            font-weight: 700;
            letter-spacing: 0.06em;
            pointer-events: none;
            z-index: 11;
            padding: 2px 8px;
            border-radius: 4px;
            white-space: nowrap;
            text-align: center;
            text-shadow: 0 1px 2px rgba(0,0,0,0.9);
        }}
        </style>
        <div style="background:var(--sa-raised-surface, #1e293b);border:1px solid var(--sa-border, #334155);
                    border-radius:14px;padding:1rem 1.2rem;margin:0.5rem 0 1rem;display:flex;
                    gap:1.2rem;align-items:center;box-shadow:0 2px 8px rgba(0,0,0,0.15)">
            <svg width="90" height="92" viewBox="0 0 84 88" aria-label="Face alignment guide" style="flex:none">
                <rect x="4" y="3" width="76" height="70" rx="10" fill="none"
                      stroke="#38bdf8" stroke-width="1.5" stroke-dasharray="4 3"/>
                <ellipse cx="42" cy="35" rx="22" ry="26" fill="rgba(56, 189, 248, 0.08)"
                         stroke="#38bdf8" stroke-width="2"/>
                <line x1="26" y1="31" x2="58" y2="31" stroke="#38bdf8" stroke-width="1" stroke-dasharray="2 2"/>
                <circle cx="34" cy="31" r="2.5" fill="#38bdf8"/>
                <circle cx="50" cy="31" r="2.5" fill="#38bdf8"/>
                <path d="M42 33 L{nose_x} 43" fill="none" stroke="#f59e0b" stroke-width="2.5" stroke-linecap="round"/>
                <text x="42" y="86" text-anchor="middle" fill="#38bdf8"
                      font-size="12" font-weight="700">{arrow} {angle_cue}</text>
            </svg>
            <div style="flex:1">
                <div style="display:flex;align-items:center;gap:0.5rem;margin-bottom:0.3rem">
                    <span style="font-weight:700;font-size:1.05rem">{cfg['title']}</span>
                    <span style="background:rgba(56, 189, 248, 0.18);color:#38bdf8;padding:0.15rem 0.5rem;
                                 border-radius:999px;font-size:0.75rem;font-weight:600">
                        {cfg['badge']}
                    </span>
                </div>
                <div style="font-size:0.92rem;line-height:1.35;margin-bottom:0.35rem">{instruction}</div>
                <div style="font-size:0.83rem;color:var(--sa-muted, #94a3b8);line-height:1.3">
                    💡 <strong>Framing tip:</strong> {tip}
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_multipose_face_enrollment(student_data):
    import numpy as np
    from PIL import Image

    student_id = student_data["student_id"]
    pose_stages = [
        ("front", "Front", 0.0, 18.0),
        ("left", "Slight left", -18.0, -75.0),
        ("right", "Slight right", 18.0, 75.0),
        ("left_profile", "Left profile", -75.0, -180.0),
        ("right_profile", "Right profile", 75.0, 180.0),
    ]

    with st.expander("Multi-pose face enrollment"):
        from src.database.db import get_student_face_templates

        try:
            templates = get_student_face_templates(student_id)
        except Exception:
            templates = []
        registered = {row.get("pose_label") for row in templates}
        captures = st.session_state.setdefault("multi_pose_captures", {})
        capture_quality = st.session_state.setdefault(
            "multi_pose_capture_quality",
            {},
        )
        completed = registered | set(captures)
        from src.pipelines.face_pipeline import missing_required_face_poses

        missing_required = missing_required_face_poses(completed)
        status_lines = [
            f"{'✅' if pose in completed else '⬜'} {label}: "
            f"{'Completed' if pose in completed else 'Pending'}"
            for pose, label, _, _ in pose_stages
        ]
        st.caption(" · ".join(status_lines))
        st.info(
            "Front, slight left, and slight right poses are required before saving. "
            "Profile views are optional."
        )
        if missing_required:
            missing_labels = [
                label for pose, label, _, _ in pose_stages
                if pose in missing_required
            ]
            st.warning("Still required: " + ", ".join(missing_labels))
        face_consent = st.checkbox(
            "I consent to storing these pose-specific face templates.",
            key=f"multi_pose_consent_{student_id}",
        )
        pose_key = f"multi_pose_selected_{student_id}"
        next_pose = st.session_state.pop(
            f"multi_pose_advance_{student_id}",
            None,
        )
        if next_pose is not None:
            st.session_state[pose_key] = next_pose
        elif pose_key not in st.session_state:
            st.session_state[pose_key] = next(
                (pose for pose, _, _, _ in pose_stages if pose not in completed),
                "front",
            )
        selected_pose = st.selectbox(
            "Pose to update",
            [pose for pose, _, _, _ in pose_stages],
            format_func=lambda pose: dict((p, label) for p, label, _, _ in pose_stages)[pose],
            key=pose_key,
        )
        pose_label = dict((p, label) for p, label, _, _ in pose_stages)[selected_pose]
        st.write(f"Requested view: **{pose_label}**")
        _render_face_pose_guide(selected_pose)
        cam_cfg = _get_pose_camera_config(selected_pose)
        _render_camera_hud_header(cam_cfg)
        photo = st.camera_input(
            cam_cfg["camera_label"],
            key=f"multi_pose_camera_{student_id}_{selected_pose}",
            disabled=not face_consent,
        )
        _render_camera_hud_footer(cam_cfg)
        if photo is not None:
            with st.spinner("Checking pose quality..."):
                image = np.asarray(Image.open(photo).convert("RGB"))
                from src.pipelines.face_pipeline import analyze_face_capture

                analysis = analyze_face_capture(image)
                feedback = get_pose_capture_feedback(selected_pose, analysis)
                if feedback:
                    st.error(feedback)
                else:
                        duplicate = any(
                            float(np.linalg.norm(
                                np.asarray(existing, dtype=np.float64)
                                - np.asarray(analysis["embedding"], dtype=np.float64)
                            )) < 0.08
                            for pose, existing in captures.items()
                            if pose != selected_pose
                        )
                        if duplicate:
                            st.warning("This image is too similar to another captured pose.")
                        else:
                            captures[selected_pose] = analysis["embedding"].tolist()
                            capture_quality[selected_pose] = analysis["quality_score"]
                            next_pose = next(
                                (
                                    pose
                                    for pose, _, _, _ in pose_stages
                                    if pose not in registered and pose not in captures
                                ),
                                None,
                            )
                            if next_pose is not None:
                                st.session_state[
                                    f"multi_pose_advance_{student_id}"
                                ] = next_pose
                            st.rerun()
        if st.button(
            "Save completed poses",
            key=f"save_multi_pose_{student_id}",
            disabled=not face_consent or not captures or bool(missing_required),
            type="primary",
        ):
            from src.database.db import upsert_student_face_template
            from src.pipelines.face_pipeline import train_classifier

            saved = 0
            for pose, embedding in captures.items():
                upsert_student_face_template(
                    student_id,
                    pose,
                    embedding,
                    image_quality_score=capture_quality.get(pose),
                )
                saved += 1
            captures.clear()
            capture_quality.clear()
            train_classifier()
            st.success(f"Saved {saved} face template(s).")
            st.rerun()


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

    face_tab, voice_tab = st.tabs(["📷 Face Match", "🎙️ Voice Phrase"])
    with face_tab:
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
        missing_face_requirements = []
        if not (access_code.isdigit() and len(access_code) == 8):
            missing_face_requirements.append("a valid 8-digit class access code")
        if not face_consent:
            missing_face_requirements.append("consent to face matching")
        if photo is None:
            missing_face_requirements.append("a photo capture")
        if share_location and latitude is None:
            missing_face_requirements.append("GPS location fix (or uncheck location sharing)")

        if missing_face_requirements:
            st.caption(
                f"⚠️ **Cannot submit yet.** Please provide: {', '.join(missing_face_requirements)}."
            )

        if st.button(
            "Verify and check in",
            type="primary",
            width="stretch",
            disabled=bool(missing_face_requirements),
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
            _show_checkin_result(checkin, "face", float(distance))

    with voice_tab:
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
            profile_audio = voice_input(
                "Record a voice profile sample",
                key=f"checkin_voice_profile_{student_id}",
                disabled=not voice_consent,
            )
        attendance_audio = voice_input(
            "Record a fresh sample for this check-in",
            key=f"checkin_voice_sample_{student_id}",
            disabled=not voice_consent,
        )
        missing_voice_requirements = []
        if not (access_code.isdigit() and len(access_code) == 8):
            missing_voice_requirements.append("a valid 8-digit class access code")
        if not voice_consent:
            missing_voice_requirements.append("consent to voice matching")
        if not voice_profile and profile_audio is None:
            missing_voice_requirements.append("a voice profile sample (enrollment recording above)")
        if attendance_audio is None:
            missing_voice_requirements.append("a fresh check-in voice recording")
        if share_location and latitude is None:
            missing_voice_requirements.append("GPS location fix (or uncheck location sharing)")

        if missing_voice_requirements:
            st.caption(
                f"⚠️ **Cannot submit yet.** Please provide: {', '.join(missing_voice_requirements)}."
            )

        if st.button(
            "Verify voice and check in",
            type="primary",
            width="stretch",
            disabled=bool(missing_voice_requirements),
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
            _show_checkin_result(checkin, "voice", float(score))


def _show_checkin_result(checkin, method=None, score=None):
    if checkin["status"] == "pending":
        st.info(
            "Your match needs a quick teacher review. It will appear as pending "
            "until the teacher decides."
        )
    else:
        st.success("Check-in verified and attendance recorded.")
    if method == "face" and score is not None:
        st.caption(f"Face match distance: {score:.3f} (lower is closer).")
    elif method == "voice" and score is not None:
        st.caption(f"Voice match similarity: {score:.1%}.")
    if checkin.get("risk_flags"):
        st.caption(
            "Review flags: "
            + ", ".join(flag.replace("_", " ") for flag in checkin["risk_flags"])
        )


def student_screen():
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

        camera_photo = st.camera_input(
            "Position your face in the center",
            disabled=not sign_in_consent,
            key=(
                "student_face_signin_camera_"
                f"{st.session_state.get('student_face_scan_generation', 0)}"
            ),
        )
        uploaded_photo = None
        if sign_in_consent and camera_photo is None:
            st.caption(
                "If the camera is busy, close other apps or browser tabs using "
                "it, or upload a clear face photo instead."
            )
            uploaded_photo = st.file_uploader(
                "Upload a face photo if the camera is unavailable",
                type=["jpg", "jpeg", "png"],
                key=(
                    "student_face_signin_upload_"
                    f"{st.session_state.get('student_face_scan_generation', 0)}"
                ),
            )
        photo_source = camera_photo if camera_photo is not None else uploaded_photo
        photo_image = None
        if photo_source is not None:
            import numpy as np
            from PIL import Image

            try:
                with Image.open(photo_source) as image:
                    photo_image = np.array(image.convert("RGB"))
            except (OSError, ValueError):
                st.error("Could not read that image. Choose a valid JPG or PNG photo.")
                photo_source = None

        if not show_registration and st.button(
            "Register or re-enroll instead",
            key="register_student_profile",
        ):
            st.session_state['show_student_registration'] = True
            st.rerun()

        if photo_image is not None and not show_registration:
            from src.pipelines.face_pipeline import identify_student

            with st.spinner('AI is scanning..'):
                student, num_faces = identify_student(photo_image)

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

                    try:
                        record_student_biometric_consent(
                            student['student_id'], 'face'
                        )
                    except RuntimeError as error:
                        st.error(str(error))
                    else:
                        st.session_state.is_logged_in = True
                        st.session_state.user_role = 'student'
                        st.session_state.student_data = student
                        st.toast(f'Welcome Back {student["name"]}')
                        st.rerun()
                else:
                    st.warning(
                        'Face Not Recognized – Student Not Registered.'
                    )
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
        voice_audio = voice_input(
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

                try:
                    record_student_biometric_consent(student_id, 'voice')
                except RuntimeError as error:
                    st.error(str(error))
                else:
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
                "captured or uploaded photos are processed for matching and not "
                "retained. Voice enrollment is optional and stores a numeric "
                "template, not the recording."
            )
            st.subheader("Multi-pose face enrollment")
            import numpy as np
            from PIL import Image
            registration_poses = [
                ("front", "Front"),
                ("left", "Slight left"),
                ("right", "Slight right"),
                ("left_profile", "Left profile"),
                ("right_profile", "Right profile"),
            ]
            from src.pipelines.face_pipeline import missing_required_face_poses

            registration_captures = st.session_state.setdefault(
                "registration_multi_pose_captures",
                {},
            )
            registration_quality = st.session_state.setdefault(
                "registration_multi_pose_quality",
                {},
            )
            next_pose = st.session_state.pop("registration_multi_pose_advance", None)
            if next_pose is not None:
                st.session_state["registration_multi_pose"] = next_pose
            elif "registration_multi_pose" not in st.session_state:
                st.session_state["registration_multi_pose"] = next(
                    (
                        pose
                        for pose, _ in registration_poses
                        if pose not in registration_captures
                    ),
                    "front",
                )
            registration_pose = st.selectbox(
                "Capture pose",
                [pose for pose, _ in registration_poses],
                format_func=lambda pose: dict(registration_poses)[pose],
                key="registration_multi_pose",
            )
            registration_pose_label = dict(registration_poses)[registration_pose]
            registration_consent = st.checkbox(
                "I consent to creating pose-specific face templates.",
                key="registration_multi_pose_consent",
            )
            _render_face_pose_guide(registration_pose)
            reg_cam_cfg = _get_pose_camera_config(registration_pose)
            _render_camera_hud_header(reg_cam_cfg)
            registration_camera = st.camera_input(
                reg_cam_cfg["camera_label"],
                key=f"registration_multi_pose_camera_{registration_pose}",
                disabled=not registration_consent,
            )
            _render_camera_hud_footer(reg_cam_cfg)
            st.caption(
                " · ".join(
                    f"{'✅' if pose in registration_captures else '⬜'} {label}: "
                    f"{'Completed' if pose in registration_captures else 'Pending'}"
                    for pose, label in registration_poses
                )
            )
            missing_registration_poses = missing_required_face_poses(
                registration_captures
            )
            if missing_registration_poses:
                missing_labels = [
                    label
                    for pose, label in registration_poses
                    if pose in missing_registration_poses
                ]
                st.warning(
                    "Capture all required poses before creating the account: "
                    + ", ".join(missing_labels)
                )
            if registration_camera is not None:
                image = np.asarray(Image.open(registration_camera).convert("RGB"))
                from src.pipelines.face_pipeline import analyze_face_capture
                analysis = analyze_face_capture(image)
                feedback = get_pose_capture_feedback(registration_pose, analysis)
                if feedback:
                    st.error(feedback)
                else:
                    duplicate = any(
                        float(np.linalg.norm(
                            np.asarray(existing, dtype=np.float64)
                            - np.asarray(analysis["embedding"], dtype=np.float64)
                        )) < 0.08
                        for pose, existing in registration_captures.items()
                        if pose != registration_pose
                    )
                    if duplicate:
                        st.warning("This capture is too similar to a different completed pose.")
                    else:
                        registration_captures[registration_pose] = analysis["embedding"].tolist()
                        registration_quality[registration_pose] = analysis["quality_score"]
                        next_pose = next(
                            (
                                pose
                                for pose, _ in registration_poses
                                if pose not in registration_captures
                            ),
                            None,
                        )
                        if next_pose is not None:
                            st.session_state["registration_multi_pose_advance"] = next_pose
                        st.rerun()
            if not photo_source:
                st.info('Take or upload a clear face photo above to create your profile.')
            new_name = st.text_input("Enter your name", placeholder='E.g. Zulker')

            st.subheader('Optional : Voice Enrollment')
            st.info("Voice enrollment can be used as an alternative check-in method.")
            face_consent = st.checkbox(
                "I consent to face biometric processing to create my account."
            )
            voice_consent = st.checkbox(
                "I also consent to voice biometric processing (optional)."
            )


            audio_data = None

            if voice_consent:
                audio_data = voice_input(
                    "Record a short phrase for voice enrollment",
                    key="student_voice_enrollment_audio",
                )

            if st.button(
                'Create Account',
                type='primary',
                disabled=not face_consent or bool(missing_registration_poses),
            ):
                registration_captures = st.session_state.get(
                    "registration_multi_pose_captures",
                    {},
                )
                missing_registration_poses = missing_required_face_poses(
                    registration_captures
                )
                if missing_registration_poses:
                    st.error(
                        "Account not created. Capture the front, slight left, "
                        "and slight right poses first."
                    )
                elif new_name:
                    with st.spinner('Creating profile..'):
                        from src.database.db import (
                            create_student,
                            upsert_student_face_template,
                        )
                        from src.pipelines.face_pipeline import train_classifier
                        from src.pipelines.voice_pipeline import get_voice_embedding

                        front_embedding = registration_captures["front"]
                        voice_emb = None
                        if audio_data and voice_consent:
                            voice_emb = get_voice_embedding(audio_data.getvalue())

                        response_data = create_student(
                            new_name,
                            face_embedding=front_embedding,
                            voice_embedding=voice_emb,
                            face_consent=face_consent,
                            voice_consent=voice_consent,
                        )
                        if response_data:
                            student_id = response_data[0]["student_id"]
                            for pose, embedding in registration_captures.items():
                                upsert_student_face_template(
                                    student_id,
                                    pose,
                                    embedding,
                                    image_quality_score=registration_quality.get(pose),
                                )
                            st.session_state.pop(
                                "registration_multi_pose_captures",
                                None,
                            )
                            st.session_state.pop(
                                "registration_multi_pose_quality",
                                None,
                            )
                            train_classifier()
                            st.session_state.is_logged_in = True
                            st.session_state.user_role = 'student'
                            st.session_state.student_data = response_data[0]
                            st.session_state['show_student_registration'] = False
                            st.toast(f'Profile Created! Hi {new_name}!')
                            st.rerun()
                else:
                    st.warning('Please enter your name!')


        