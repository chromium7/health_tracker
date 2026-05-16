# HealthTracker

Server-rendered Django app for tracking an elderly patient's health
metrics, medications, hydration, and documents. Caregivers can view and
log on the patient's behalf. All accounts are created in Django Admin.

## Requirements

- Python 3.13
- PostgreSQL (a running instance reachable as configured in
  `health_tracker/local_settings.py`)
- Redis (used by the default cache configuration)

## Setup

```bash
python -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt
pip install -r requirements-dev.txt

python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

The application listens on http://127.0.0.1:8000/ by default. The login
form is at `/login/`; the admin is at `/admin/`.

## Creating patient and caregiver accounts

There is no frontend signup. Accounts are created exclusively through
the admin:

1. Run `python manage.py createsuperuser` and log in to `/admin/`.
2. Add a new User. Set `role = patient`, set a 4-digit `pin`, and
   leave `patient_profile` blank. Save.
3. Add additional Users with `role = caregiver`, a 4-digit `pin`, and
   `patient_profile` pointing at the patient created in step 2.

The admin form rejects misconfigurations: a caregiver without a
`patient_profile`, or a patient with one set, will fail validation.

## Roles

- **patient** - Owns health data. The patient sees and logs their own
  metrics, medications, water intake, and documents.
- **caregiver** - Linked to exactly one patient via `patient_profile`.
  Logs and views data on behalf of that patient. The view layer
  resolves the relevant patient via `User.get_patient()`.

## Tests

```bash
python manage.py test tests
```

The test suite uses Django's `TestCase`. Per project policy, external
dependencies (file systems, etc.) are mocked or routed to a temporary
directory.

## Mobile-only PWA

HealthTracker ships as a Progressive Web App targeting smartphone
browsers only. There are no desktop layouts.

- Manifest: `GET /manifest.webmanifest` (rendered from
  `templates/manifest.webmanifest`).
- Service worker: `GET /sw.js` (rendered from `templates/sw.js`,
  served at root scope so it controls the whole app).
- Install prompts appear automatically in supported browsers once the
  manifest and service worker resolve.

### Required icons

Drop these two PNG files in place before installing the app:

```
static_files/icons/icon-192.png   (192 x 192)
static_files/icons/icon-512.png   (512 x 512)
```

Both are referenced from `manifest.webmanifest` and the iOS
`apple-touch-icon` link. Until you provide them, the install flow
still works but the home-screen icon falls back to a browser default.

## Notes

- PINs are stored as plaintext for MVP simplicity. Production must
  switch to hashed PINs via `make_password` / `check_password` (see
  `health_tracker/apps/users/backends.py`).
- Document uploads validate against the client-supplied
  `content_type`. Production should switch to magic-byte inspection
  via `python-magic` (see comment in
  `health_tracker/apps/documents/forms.py`).
- Local media is written under `MEDIA_ROOT`. Production should swap
  this for S3 via `django-storages` + `boto3`.
