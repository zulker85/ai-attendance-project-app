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

def create_student(new_name, face_embedding=None, voice_embedding=None):
    data = {'name': new_name, 'face_embedding':face_embedding, "voice_embedding": voice_embedding}
    response = supabase.table('students').insert(data).execute()
    return response.data


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


def create_subject(subject_code, name, section, teacher_id):
    data = {"subject_code": subject_code, "name": name, "section": section, "teacher_id": teacher_id}
    response = supabase.table("subjects").insert(data).execute()
    return response.data

def get_teacher_subjects(teacher_id):
    response = supabase.table('subjects').select("*, subject_students(count), attendance_logs(timestamp)").eq("teacher_id", teacher_id).execute()
    subjects = response.data


    for sub in subjects:
        sub['total_students'] = sub.get("subject_students", [{}])[0].get('count', 0) if sub.get('subject_students') else 0
        attendance = sub.get('attendance_logs', [])
        unique_sessions = len(set(log['timestamp'] for log in attendance))
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
        .select("*, subjects!inner(*), students(name)")
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
