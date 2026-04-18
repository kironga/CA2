# CA2 - Authentication of Academic Credentials

CA2 is a Django web system for secure academic credential verification using:
- National ID as primary lookup key
- OTP sent to the citizen's registered email
- Institution-sourced academic records

## Implemented Modules
- Government/Admin interface (supervision dashboard + Django admin)
- Institution/Exam body interface (add/edit/list certificate records)
- Citizen interface (register and maintain National ID + OTP email)
- HR interface (request OTP, verify OTP, view verified records)

## Core Architecture
- `accounts`: custom user model and role-based access control
- `citizens`: citizen profile, National ID, OTP email
- `institutions`: institutions and certificate records
- `verification`: OTP request lifecycle and verification flow

## Roles
- `GOV_ADMIN` (Government/Admin)
- `INST_ADMIN` (Institution Admin)
- `HR_MANAGER`
- `CITIZEN`

## Key Models
- `accounts.User`: custom auth user with `role`
- `citizens.CitizenProfile`: `user`, `national_id` (unique), `otp_email` (unique)
- `institutions.Institution`: institution metadata
- `institutions.InstitutionProfile`: links institution admin to institution
- `institutions.CertificateRecord`: institution-issued credential data
- `verification.OTPRequest`: OTP hash, expiry, attempts, request metadata

## Security Notes
- Passwords use Django's built-in password hashing.
- OTPs are never stored in plain text (hashed with `make_password`).
- OTP has expiry (`10` minutes), one-time-use, and max attempts (`5`).
- Role-based checks restrict module access by user type.
- Session timeout is set to 5 minutes.

## Email OTP (Real SMTP)
Default email backend is SMTP and is environment-driven in `ca2/settings.py`.

Set these variables before running the server:
- `DJANGO_EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend`
- `DJANGO_EMAIL_HOST=smtp.gmail.com`
- `DJANGO_EMAIL_PORT=587`
- `DJANGO_EMAIL_USE_TLS=true`
- `DJANGO_EMAIL_HOST_USER=<your_real_email>`
- `DJANGO_EMAIL_HOST_PASSWORD=<your_app_password>`
- `DJANGO_DEFAULT_FROM_EMAIL=<your_verified_sender>`

For Gmail, use an App Password (not your normal account password).

See `.env.example` for the full variable list.

## OTP Anti-Abuse Controls
- OTP cooldown window: 60 seconds per citizen
- Daily cap per citizen: 10 requests
- Daily cap per HR account: 40 requests
- OTP expiry: 10 minutes
- OTP max attempts: 5
- OTP records include request IP and user-agent for audit trail

## Basic REST APIs
Session-authenticated JSON endpoints:
- `GET /api/institutions/certificates/` (Institution Admin)
- `POST /api/institutions/certificates/create/` (Institution Admin)
- `POST /api/hr/request-otp/` (HR Manager)
- `POST /api/hr/verify-otp/` (HR Manager)

## Job Alerts
- HR managers can create job alerts at `/job-alerts/new/`
- Alerts are distributed to registered citizen emails
- Delivery logs are stored for traceability
- Citizens can view recent alerts at `/job-alerts/citizen/`

## Local Setup
1. Create and activate a Python virtual environment.
2. Install dependencies:
   - `pip install -r requirements.txt`
3. Run migrations:
   - `python manage.py migrate`
4. Create superuser:
   - `python manage.py createsuperuser`
5. Start server:
   - `python manage.py runserver`

If you see a missing column error (for example on job alerts URLs), run migrations again:
- `python manage.py migrate`

## Production Settings
- Use `ca2.settings_production` module:
  - `set DJANGO_SETTINGS_MODULE=ca2.settings_production`
- Required environment variables:
  - `DJANGO_SECRET_KEY`
  - `DJANGO_ALLOWED_HOSTS`
- Recommended environment variables:
  - `DJANGO_EMAIL_BACKEND`, `DJANGO_EMAIL_HOST`, `DJANGO_EMAIL_PORT`, `DJANGO_EMAIL_HOST_USER`, `DJANGO_EMAIL_HOST_PASSWORD`

## Main URLs
- Login: `/login/`
- Citizen registration: `/citizen-register/`
- Citizen profile: `/citizens/profile/`
- Institution records: `/institutions/certificates/`
- HR OTP flow:
  - request: `/verification/request-otp/`
  - verify: `/verification/verify-otp/`
  - records: `/verification/records/`

## Testing
Tests included for:
- OTP generation/validation and email sending
- OTP send-failure cleanup path
- Institution record entry and access control
- Citizen registration and role redirect

Run:
- `python manage.py test`

## Requirement Mapping (Proposal Alignment)
- Multi-user interfaces: implemented via role dashboards and per-module routes
- ID-centric design: National ID used in OTP and record lookup
- Email OTP adaptation: implemented in citizen profile and verification service
- Data integrity: institution-only edit access for certificates
- Fraud supervision simulation: government dashboard + admin visibility
- Basic extensibility for job alerts: citizen email registry is ready for notification module
