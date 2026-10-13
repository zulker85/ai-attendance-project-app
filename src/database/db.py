from src.database.config import supabase
import bcrypt



def hash_pass(pwd):
    return bcrypt.hashpw(pwd.encode(), bcrypt.gensalt()).decode()

def check_pass(pwd, hashed):
    return bcrypt.checkpw(pwd.encode(), hashed.encode())


def check_teacher_exists(username):
    # Check for unique username, returns false when username is already taken
    response = supabase.table("teachers").select("username").eq("username", username).execute()
    return len(response.data) > 0 



def create_teacher(username, password, name):

    data = { "username" : username, "password": hash_pass(password), "name": name}
    response = supabase.table("teachers").insert(data).execute()
    return response.data


def teacher_login(username, password):
    response = supabase.table("teachers").select("*").eq("username", username).execute()
    if response.data:
        teacher = response.data[0]
        if check_pass(password, teacher['password']):
            return teacher
    return None


def get_all_students():
    response = supabase.table('students').select("*").execute()
    return response.data

def create_student(
    new_name,
    face_embedding=None,
    voice_embedding=None,
    face_consent=False,
    voice_consent=False,
):
    from datetime import datetime, timezone

    consented_at = datetime.now(timezone.utc).isoformat()
    data = {
        'name': new_name,
        'face_embedding': face_embedding,
        'voice_embedding': voice_embedding,
        'face_consent_at': consented_at if face_consent else None,
        'voice_consent_at': consented_at if voice_consent else None,
    }
    response = supabase.table('students').insert(data).execute()
    return response.data


def save_student_voice_profile(student_id, voice_embedding):
    from datetime import datetime, timezone

    response = (
        supabase.table('students')
        .update({
            'voice_embedding': voice_embedding,
            'voice_consent_at': datetime.now(timezone.utc).isoformat(),
        })
        .eq('student_id', student_id)
        .select('*')
        .execute()
    )
    if not response.data:
        raise ValueError('Could not save the voice profile for this student.')
    from src.pipelines.face_pipeline import get_trained_model

    get_trained_model.clear()
    return response.data[0]


def record_student_biometric_consent(student_id, method):
    from datetime import datetime, timezone

    consent_columns = {
        'face': 'face_consent_at',
        'voice': 'voice_consent_at',
    }
    if method not in consent_columns:
        raise ValueError('Unsupported biometric consent type.')

    response = (
        supabase.table('students')
        .update({
            consent_columns[method]: datetime.now(timezone.utc).isoformat()
        })
        .eq('student_id', student_id)
        .select('student_id')
        .execute()
    )
    if not response.data:
        raise ValueError('Could not record biometric consent.')


def delete_student_account(student_id):
    response = supabase.rpc(
        'delete_student_account',
        {'p_student_id': student_id},
    ).execute()
    if not response.data:
        raise ValueError('The student profile could not be deleted.')
    from src.pipelines.face_pipeline import get_trained_model

    get_trained_model.clear()


def create_subject(subject_code, name, section, teacher_id):
    data = {"subject_code": subject_code, "name": name, "section": section, "teacher_id": teacher_id}
    response = supabase.table("subjects").insert(data).execute()
    return response.data

def get_teacher_subjects(teacher_id):
    response = supabase.table('subjects').select(
        "*, subject_students(count), attendance_logs(timestamp, class_session_id)"
    ).eq("teacher_id", teacher_id).execute()
    subjects = response.data


    for sub in subjects:
        sub['total_students'] = sub.get("subject_students", [{}])[0].get('count', 0) if sub.get('subject_students') else 0
        attendance = sub.get('attendance_logs', [])
        unique_sessions = len({
            ('session', log['class_session_id'])
            if log.get('class_session_id') is not None
            else ('timestamp', log['timestamp'])
            for log in attendance
        })
        sub['total_classes'] = unique_sessions


        sub.pop('subject_student', None)
        sub.pop('attendance_logs', None)

    return subjects


def  enroll_student_to_subject(student_id, subject_id):
    data = {'student_id': student_id, "subject_id": subject_id}
    response= supabase.table('subject_students').insert(data).execute()
    return response.data


def  unenroll_student_to_subject(student_id, subject_id):
    response= supabase.table('subject_students').delete().eq('student_id', student_id).eq('subject_id', subject_id).execute()
    return response.data



def get_student_subjects(student_id):
    response = supabase.table('subject_students').select('*, subjects(*)').eq('student_id', student_id).execute()
    return response.data


def get_student_attendance(student_id):
    response = supabase.table('attendance_logs').select('*, subjects(*)').eq('student_id', student_id).execute()
    return response.data


def create_attendance(logs):
    response = supabase.table('attendance_logs').insert(logs).execute()
    return response.data

def get_attendance_for_teacher(teacher_id):
    response = (
        supabase.table('attendance_logs')
        .select("*, subjects!inner(*), students(name), class_sessions(started_at)")
        .eq('subjects.teacher_id', teacher_id)
        .execute()
    )
    return response.data


def get_student_voice_attendance(student_id):
    response = (
        supabase.table('voice_attendance_submissions')
        .select('*')
        .eq('student_id', student_id)
        .order('submitted_at', desc=True)
        .execute()
    )
    return response.data


def get_pending_voice_attendance_for_subjects(subject_ids):
    if not subject_ids:
        return []

    response = (
        supabase.table('voice_attendance_submissions')
        .select('*')
        .in_('subject_id', subject_ids)
        .eq('status', 'pending')
        .order('submitted_at', desc=True)
        .execute()
    )
    return response.data


def submit_voice_attendance(
    student_id,
    student_name,
    subject_id,
    subject_name,
    subject_code,
    voice_match_score,
    latitude,
    longitude,
    location_accuracy_m,
):
    response = supabase.rpc(
        'submit_voice_attendance',
        {
            'p_student_id': student_id,
            'p_student_name': student_name,
            'p_subject_id': subject_id,
            'p_subject_name': subject_name,
            'p_subject_code': subject_code,
            'p_voice_match_score': voice_match_score,
            'p_latitude': latitude,
            'p_longitude': longitude,
            'p_location_accuracy_m': location_accuracy_m,
        },
    ).execute()
    return response.data


def review_voice_attendance(submission_id, teacher_id, approved):
    response = supabase.rpc(
        'review_voice_attendance',
        {
            'p_submission_id': submission_id,
            'p_teacher_id': teacher_id,
            'p_approved': approved,
        },
    ).execute()
    if not response.data:
        raise ValueError('This request was already reviewed or is not in your classes.')
    return response.data


def open_class_session(subject_id, teacher_id, access_code, duration_minutes):
    response = supabase.rpc(
        'open_class_session',
        {
            'p_subject_id': subject_id,
            'p_teacher_id': teacher_id,
            'p_access_code': access_code,
            'p_duration_minutes': duration_minutes,
        },
    ).execute()
    if not response.data:
        raise ValueError('The class session could not be opened.')
    return response.data[0]


def rotate_class_session_code(session_id, teacher_id, access_code):
    response = supabase.rpc(
        'rotate_class_session_code',
        {
            'p_session_id': session_id,
            'p_teacher_id': teacher_id,
            'p_access_code': access_code,
        },
    ).execute()
    if not response.data:
        raise ValueError('The active class code could not be rotated.')
    return response.data[0]


def close_class_session(session_id, teacher_id):
    response = supabase.rpc(
        'close_class_session',
        {'p_session_id': session_id, 'p_teacher_id': teacher_id},
    ).execute()
    if not response.data:
        raise ValueError('The class session could not be closed.')
    return response.data[0]


def get_class_sessions_for_teacher(teacher_id):
    response = (
        supabase.table('class_sessions')
        .select('*, subjects(name, subject_code, section)')
        .eq('teacher_id', teacher_id)
        .order('started_at', desc=True)
        .limit(100)
        .execute()
    )
    return response.data


def submit_class_checkin(
    access_code,
    student_id,
    verification_method,
    verification_score,
    subject_id=None,
    latitude=None,
    longitude=None,
    location_accuracy_m=None,
):
    response = supabase.rpc(
        'submit_class_checkin',
        {
            'p_access_code': access_code,
            'p_student_id': student_id,
            'p_subject_id': subject_id,
            'p_verification_method': verification_method,
            'p_verification_score': verification_score,
            'p_latitude': latitude,
            'p_longitude': longitude,
            'p_location_accuracy_m': location_accuracy_m,
        },
    ).execute()
    if not response.data:
        raise ValueError('The check-in request was not saved.')
    return response.data[0]


def get_pending_class_checkins(teacher_id):
    response = (
        supabase.table('class_checkins')
        .select(
            '*, students(name), '
            'class_sessions!inner(subject_id, teacher_id, subjects(name, subject_code, section))'
        )
        .eq('status', 'pending')
        .eq('class_sessions.teacher_id', teacher_id)
        .order('submitted_at')
        .execute()
    )
    return response.data


def review_class_checkin(checkin_id, teacher_id, approved):
    response = supabase.rpc(
        'review_class_checkin',
        {
            'p_checkin_id': checkin_id,
            'p_teacher_id': teacher_id,
            'p_approved': approved,
        },
    ).execute()
    if not response.data:
        raise ValueError('This request was already reviewed or is not in your classes.')
    return response.data[0]


def save_student_voice_profile(student_id, voice_embedding):
    response = (
        supabase.table('students')
        .update({'voice_embedding': voice_embedding})
        .eq('student_id', student_id)
        .select('*')
        .execute()
    )
    if not response.data:
        raise ValueError('Could not save the voice profile for this student.')
    return response.data[0]
