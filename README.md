# ai-attendance-project-app

## Supabase setup

Before using the student portal, run `sql/students.sql` in the Supabase SQL
Editor. This creates the `public.students` table used for student profiles and
reloads the PostgREST schema cache. The app stores face and voice embeddings as
arrays of floating-point values. Use the server-side `SUPABASE_KEY` configured
in Streamlit secrets to access the table.

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

Older voice requests remain available in **Voice Reviews**. New voice submissions
are session-bound; students explicitly consent before recording, and the
per-subject voice dialog does not collect location. In the main Live Check-in
panel, students can optionally share GPS for either verification method.

## Live, trust-aware class check-in

After the base `students`, `subjects`, `teachers`, `subject_students`, and
`attendance_logs` tables exist, run `sql/class_checkin_sessions.sql` in the
Supabase SQL Editor. This migration creates expiring class sessions, check-in
records, teacher review functions, and an optional class-session reference on
attendance records. It is safe to rerun. Keep the configured Supabase key
server-side; the new tables and RPC functions are restricted to `service_role`.

In **Live Check-in**, a teacher opens a 5–60 minute session. An eight-digit code
can be rotated or the session closed at any time. The QR code opens the student
page with that code prefilled; students must still sign in and be enrolled in
the matching class. A network-accessible deployment is needed for students to
open the QR link from their devices. Teachers should close a session or open a
new one for that subject to finalize it; students without a submitted check-in
are then recorded absent, while borderline requests remain available for review.

Students explicitly consent before using face or voice matching. A strong face
match (distance at most 0.45) or voice match (similarity at least 0.80) records
attendance automatically. Borderline matches are sent to **Live Check-in**
teacher review; unmatched attempts are not marked present. These thresholds
are initial engineering defaults, not validated identity guarantees: evaluate
them with consented, representative data before any real-world deployment.
Voice verification is available as an alternative to face verification. GPS
sharing is optional, and accuracy above 200 metres is shown as a review flag,
not treated as proof of misconduct. Captured check-in photos and audio are
processed for matching and not stored by the session-check-in flow.
Initial face/voice profile consent and subsequent successful biometric sign-ins
are timestamped on the student profile. Each check-in also records its
verification method, score, and any teacher decision.

The student privacy panel can delete the profile, biometric embeddings,
enrollments, attendance records, and voice requests. Deletion is permanent.

## Evaluating this major project

Use a consented, representative evaluation set and report false-accept and
false-reject rates separately for face and voice, match latency, borderline
review rate, and results across lighting, camera quality, face angle, and
recording conditions. Compare verification alternatives, include teacher
review outcomes, and avoid reporting a single accuracy figure without its
conditions or sample size. The included tests exercise code generation and
check-in decision boundaries; they do not certify biometric accuracy.

For crowded classroom photos, upload or capture multiple clear views from
different parts of the room. Face detection keeps more image detail than the
previous 800-pixel resize and retries with stronger upsampling when fewer faces
are detected than enrolled profiles. Attendance recognition is limited to the
selected subject's enrolled students. The review screen reports detected faces
that could not be matched; review the roster before saving and use student voice
verification in **Live Check-in** for missed students. Occlusion, faces
that are too small or turned away, poor lighting, and missing or outdated
student profiles can still prevent a match, so a single group photo cannot
guarantee perfect recognition.