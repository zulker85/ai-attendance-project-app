from secrets import randbelow

from src.pipelines.face_matching import FACE_MATCH_THRESHOLD

FACE_AUTO_APPROVE_DISTANCE = FACE_MATCH_THRESHOLD * 0.75
FACE_REVIEW_DISTANCE = FACE_MATCH_THRESHOLD
VOICE_AUTO_APPROVE_SCORE = 0.8
VOICE_REVIEW_SCORE = 0.65


def generate_class_access_code():
    return f"{randbelow(100_000_000):08d}"


def checkin_decision(method, score):
    if method == "face":
        if not 0 <= score <= FACE_REVIEW_DISTANCE:
            raise ValueError("Face verification did not match the saved profile.")
        if score <= FACE_AUTO_APPROVE_DISTANCE:
            return "approved", ()
        return "pending", ("borderline_face_match",)

    if method == "voice":
        if not VOICE_REVIEW_SCORE <= score <= 1:
            raise ValueError("Voice verification did not match the saved profile.")
        if score >= VOICE_AUTO_APPROVE_SCORE:
            return "approved", ()
        return "pending", ("borderline_voice_match",)

    raise ValueError("Unsupported verification method.")


def checkin_risk_flags(method, score, location_accuracy_m=None):
    _, flags = checkin_decision(method, score)
    if location_accuracy_m is not None and location_accuracy_m > 200:
        flags += ("low_gps_accuracy",)
    return flags
