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