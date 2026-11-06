create or replace function public.delete_teacher_subject(
    p_subject_id bigint,
    p_teacher_id bigint
)
returns boolean
language plpgsql
security invoker
set search_path = ''
as $$
begin
    perform 1
    from public.subjects
    where subject_id = p_subject_id
      and teacher_id = p_teacher_id
    for update;

    if not found then
        raise exception 'This subject does not belong to the signed-in teacher.';
    end if;

    delete from public.voice_attendance_submissions
    where subject_id = p_subject_id;

    delete from public.attendance_logs
    where subject_id = p_subject_id;

    delete from public.subject_students
    where subject_id = p_subject_id;

    delete from public.class_sessions
    where subject_id = p_subject_id;

    delete from public.subjects
    where subject_id = p_subject_id
      and teacher_id = p_teacher_id;

    if not found then
        raise exception 'The subject could not be deleted.';
    end if;

    return true;
end;
$$;

revoke all on function public.delete_teacher_subject(bigint, bigint) from public;
grant execute on function public.delete_teacher_subject(bigint, bigint) to service_role;
grant delete on public.voice_attendance_submissions,
    public.attendance_logs,
    public.subject_students,
    public.class_sessions,
    public.subjects
to service_role;

notify pgrst, 'reload schema';
