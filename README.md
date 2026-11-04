# Locked — deployment skeleton

This is a class deployment exercise, not the full Locked product.

It demonstrates one path:

**user input → frontend → Flask → PostgreSQL → JSON → frontend result**

Open the page, enter a user ID, screen-on hours, and a target (default 4 hours), then click **Check Goal**.

- If screen-on time is at or under the target, the page shows **✅ Goal completed**.
- Otherwise it shows **❌ Goal not completed**.
- The backend also inserts a row into `screen_time_observations` and confirms that save on the page.

## How frontend, backend, and database connect

- The browser loads `GET /` (HTML/CSS/JS) from Flask.
- JavaScript posts JSON to `POST /api/check-goal` on the same origin. It never sees `DATABASE_URL`.
- Flask reads `DATABASE_URL` from the environment, creates `users` / `screen_time_observations` if needed (`schema.sql`), then writes an observation.
- Flask returns JSON; the page displays the result.

Placeholder values used only because the form does not collect every column:

- new users: `operating_system = Android`, `age = 25`
- `app_usage_time_min` = screen-on hours × 60
- `number_of_apps_installed` = 20
- `user_behavior_class` = a temporary 1–5 band from screen-on time

## Environment

Required:

```
DATABASE_URL
```

Put the public Railway URL in a local `.env` file. Never commit `.env`. Never paste the URL into frontend JavaScript.

## Run locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Then open http://127.0.0.1:5000

Checks:

- http://127.0.0.1:5000/health → `{"status":"ok"}`
- Check Goal with hours below the target (completed)
- Check Goal with hours above the target (not completed)

## Deploy (Railway)

Start command:

```
gunicorn app:app --bind 0.0.0.0:$PORT
```

(`Procfile` already uses this. `gunicorn app:app` also works if Railway injects the bind/port.)

Set a service variable:

```
DATABASE_URL=${{Postgres.DATABASE_URL}}
```

Use the private URL on Railway (app and Postgres in the same project). Do not put `DATABASE_PUBLIC_URL` in GitHub.

Deployment URL (fill in after Railway generates a domain):

```
https://YOUR-APP.up.railway.app
```
