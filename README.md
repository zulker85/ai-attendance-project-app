# ai-attendance-project-app

## Student voice attendance

Before using student voice attendance, run `sql/voice_attendance_submissions.sql`
in the Supabase SQL Editor. The application reads and writes this table using
the server-side `SUPABASE_KEY`; configure it as a Supabase service-role key in
Streamlit secrets (not the publishable/anon key) and never expose it in browser
code or commit it. In Supabase, copy a server-side secret/service-role key from
the project's API keys settings and set it as `SUPABASE_KEY` in
`.streamlit/secrets.toml`. Keep that key private; it has elevated database
access. The table and RPC functions intentionally restrict access to
`service_role` only, so rerunning the SQL migration will not resolve a
permission error caused by using a publishable/anon key.

Students submit a voice sample and must allow GPS access. The submission time,
location, GPS accuracy, and voice-match score are shared with the teacher of
that class. If a student has no saved voice profile, the submission dialog lets
them enroll one immediately using a profile recording and a separate attendance
recording. Teachers review requests in the **Voice Reviews** tab. Approval
records the submission in the existing attendance log. A new submission
replaces an earlier pending request; reviewed decisions remain in the student's
history.

For crowded classroom photos, upload or capture multiple clear views from
different parts of the room. Face detection keeps more image detail than the
previous 800-pixel resize and retries with stronger upsampling when fewer faces
are detected than enrolled profiles. Attendance recognition is limited to the
selected subject's enrolled students. The review screen reports detected faces
that could not be matched; review the roster before saving and use student voice
attendance plus the **Voice Reviews** tab for missed students. Occlusion, faces
that are too small or turned away, poor lighting, and missing or outdated
student profiles can still prevent a match, so a single group photo cannot
guarantee perfect recognition.