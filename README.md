# TutorDesk

**A scheduling and payments app for private tutors.** Teachers manage students, groups and a weekly schedule. Students see their lessons, check their balance and buy lesson packages online.

I built it because I know tutors who keep all of this in notebooks, spreadsheets and chat messages: who paid, how many lessons are left, who owes for last week. TutorDesk keeps it all in one place.

> Built with Django, PostgreSQL, Celery, Redis, HTMX and the Monobank payment API. Runs in Docker.

---

## What it does

### For teachers
- **Students and groups.** Add students individually or put them into groups. Each student can have their own set of available tariffs.
- **Weekly schedule.** A week view that shows individual and group lessons, highlights today and shows the **free slots** between lessons. Click a free slot and the form opens with that time already filled in.
- **Conflict detection.** The app won't let you book two lessons at the same time, for the teacher or for a student. Group lessons are checked too.
- **Invite links.** Generate a personal link for a student. When they open it and log in or sign up, their account is linked to the profile you created for them.

### For students
- **My teachers.** See every teacher and group you study with, along with your active packages and lesson balance.
- **Buy lessons online.** Pick a tariff, pay through Monobank, and the lessons are added to your balance as soon as the bank confirms the payment.
- **Live payment status.** After checkout you're sent back to the app, and the page checks the payment status automatically for up to a minute. No manual refreshing.

### Accounts
- Email-based login with no usernames. Registration requires email activation.
- Password reset via time-limited links (30 minutes), plus password change for logged-in users.
- Email notifications for activation, password reset, password changes and successful payments.

---

## Tech stack and how I used it

| Technology | What it does in this project |
|---|---|
| **Django 5.2** | Core of the app: custom `User` model with email login, class-based views, forms, admin. Split settings for `dev` and `prod`. |
| **PostgreSQL 16** | Main database. I used DB-level constraints (`CheckConstraint`, conditional `UniqueConstraint`) so invalid data can't get in, even from outside the app. |
| **HTMX** | Interactive forms and list updates without a JS framework. A small `HTMXFormMixin` returns validation errors inline and redirects with `HX-Redirect` on success. |
| **Celery + Redis** | Emails are sent in the background with automatic retries, so a slow mail server never slows down a request. |
| **Monobank Acquiring API** | Creates invoices and redirects to checkout. A webhook receives the payment status. |
| **cryptography (ECDSA)** | Verifies the `X-Sign` signature on every Monobank webhook, so nobody can fake a "payment succeeded" call. |
| **Django templates + vanilla CSS/JS** | My own small design system (CSS variables, components), responsive layout and HTML emails styled to match the site. |
| **WhiteNoise** | Serves compressed, cache-busted static files directly from Django, with no separate static server needed. |
| **Gunicorn** | Production WSGI server. |
| **Docker + Docker Compose** | One command starts the whole stack: web, Postgres, Redis, Celery worker, Celery Beat and Mailhog. There's a separate production compose file. |
| **Mailhog** | Catches all outgoing email in local development so you can read it in the browser. |
| **uv** | Dependency management with a lockfile for reproducible installs. |

---

## Things I'm proud of

**Payments that can't be faked.**
The webhook checks Monobank's ECDSA signature before it trusts anything. The bank's public key is cached for a week. If a signature fails, the app fetches a fresh key once and retries, which handles key rotation without downtime. Completing an order is idempotent, so if the bank sends the same webhook again, the student doesn't get their lessons twice.

**A lesson balance that stays correct.**
A student can have several packages at once, some expiring and some not. When a lesson is written off, the app takes it from the package that expires soonest. The rows are locked with `select_for_update()` inside a transaction, so two simultaneous requests can't spend the same lesson. If a student runs out, the balance goes negative and shows as debt, and their next purchase covers it automatically.

**Access control built in from the start.**
`TeacherRequiredMixin` and `StudentRequiredMixin`, with matching decorators for function views, guard every endpoint. Every query is also scoped to the current user, so changing an ID in the URL won't show you someone else's student, lesson or invite link.

**Services behind interfaces.**
Payments (`IPaymentsService`) and notifications (`INotificationsService`) sit behind small abstract classes. The views don't know they're talking to Monobank or SMTP, so switching providers means writing one new class.

**Soft delete.**
Students and groups are deactivated instead of deleted, so lesson and payment history stays intact. A custom `active_objects` manager hides inactive records everywhere.

---

## Getting started

You only need **Docker**.

```bash
git clone https://github.com/<your-username>/tutordesk.git
cd tutordesk
cp .env.example .env
docker compose up --build
```

That's it. On startup the container waits for the database, runs migrations and collects static files.

| Service | URL |
|---|---|
| App | http://localhost:8000 |
| Admin | http://localhost:8000/admin |
| Mailhog (emails) | http://localhost:8025 |

Create an admin account:

```bash
docker compose exec web python manage.py createsuperuser
```

### Production

```bash
docker compose -f docker-compose.prod.yaml up --build -d
```

The production setup runs Gunicorn with `DEBUG=False`, doesn't publish the database and Redis ports, and serves hashed static files. Before starting it, set `DJANGO_SECRET_KEY`, `ALLOWED_HOSTS` and (behind HTTPS) `USE_HTTPS=True` in `.env`.

---

## Configuration

All settings come from environment variables. See [`.env.example`](.env.example) for the full list.

| Variable | Purpose |
|---|---|
| `DJANGO_SETTINGS_MODULE` | `tutor_app.settings.dev` or `tutor_app.settings.prod` |
| `DJANGO_SECRET_KEY` | Django secret key (required in production) |
| `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS` | Domains the app is served from |
| `POSTGRES_*` | Database connection |
| `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND` | Redis for Celery |
| `EMAIL_*`, `DEFAULT_FROM_EMAIL` | SMTP settings (Mailhog locally) |
| `MONOBANK_TOKEN` | Monobank Acquiring API token |

---

## Project structure

```
tutor_app/       settings (base / dev / prod), urls, celery app
user/            custom user, registration, activation, password reset, invites, role mixins
schedule/        students, groups, lessons, weekly schedule, conflict checks
subscriptions/   tariff plans and student lesson packages
payments/        orders, Monobank checkout, webhook
services/        payment and notification services behind interfaces, Celery tasks
templates/       pages, reusable components, HTML emails
static/          CSS design system and a small amount of vanilla JS
```

---

## What's next

- Automated tests for the balance logic and the payment webhook
- CI pipeline (lint and tests on every push)
- Attendance tracking UI for group lessons
- Teacher dashboard with monthly income and unpaid lessons

---

## Author

**Dmytro**, Python / Django developer.
Feel free to reach out on [LinkedIn](https://www.linkedin.com/in/<your-profile>) or by [email](mailto:<your-email>).
