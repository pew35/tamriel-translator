# Tamriel Translator Django Business Demo

This folder is a learning-oriented Django demo for a future commercial version of
Tamriel Translator. It does not replace the current FastAPI backend.

## Current Scope

This demo is fully mocked. It does not call:

- the real FastAPI translator backend
- OpenAI
- `/translate-text`
- `/translate-screenshot`

The current goal is to learn and demonstrate the commercial product layer:

- account creation and login
- account roles
- monthly budget selection
- mock API usage records
- owner-only usage visibility

The mock translator page only simulates usage. When a user clicks a simulation
button, Django creates a fake `UsageRecord` with random input/output token
counts and an estimated API cost.

## Included Demo Features

- a seeded test account: `peggy` / `123`
- an unlimited tester plan
- mock text and screenshot usage records
- dashboard totals for requests, tokens, and estimated cost
- Django admin views for plans, profiles, and usage records
- owner-only console for all account usage

## Data Model

This demo uses Django's built-in `User` model for username and password.
Passwords are stored by Django as password hashes, not plain text.

Business data is stored in three custom models:

| Model | Purpose |
| --- | --- |
| `Plan` | Represents a product plan, such as an unlimited owner tester plan |
| `UserProfile` | Connects a Django user to a role, plan, display name, and monthly budget |
| `UsageRecord` | Stores one mock API request, including request type, tokens, cost, status, and time |

Monthly usage is not stored as a single hardcoded counter. Instead, each request
creates one `UsageRecord`, and monthly totals are calculated by querying records
created during the current month.

## Run

```powershell
cd django_demo
..\backend\venv\Scripts\python.exe manage.py migrate
..\backend\venv\Scripts\python.exe manage.py seed_demo
..\backend\venv\Scripts\python.exe manage.py runserver
```

Open:

```text
http://127.0.0.1:8000/
```

Demo owner account:

```text
username: peggy
password: 123
role: owner
monthly budget: $10
```

Peggy is both a normal demo user and the owner account. Because Peggy has the
`owner` role and Django staff permissions, she can open:

```text
http://127.0.0.1:8000/console/
http://127.0.0.1:8000/admin/
```

## Demo Flow

1. Login as Peggy or create a new tester account.
2. Choose a `$5` or `$10` monthly API budget when registering.
3. Enter the mock translator page.
4. Click the text or screenshot simulation buttons.
5. Each click creates a `UsageRecord`.
6. Peggy can open `/console/` to see monthly usage across accounts.

The current token cost is estimated from the GPT-5.4 mini pricing model:

- input: `$0.75 / 1M tokens`
- output: `$4.50 / 1M tokens`

The app stores budget in USD and computes usage cost from each mock request's
input/output tokens. Monthly usage is calculated by querying `UsageRecord`
created during the current month.

For a rough blended estimate, `$10` is about 3.8M total tokens if input and
output tokens are weighted 50/50. The actual cost display uses separate
input/output prices, which is closer to how real API billing works.

## How This Connects Later

The future production flow would be:

```text
User logs in
-> translator sends request with user identity
-> real backend calls OpenAI
-> backend reads OpenAI usage metadata
-> backend writes UsageRecord
-> owner console shows real monthly usage and cost
```

There are two likely integration paths:

1. Keep FastAPI as the translation API and let it write usage records to the
   same database after each OpenAI call.
2. Move translation endpoints into Django and let Django handle both auth and
   usage recording in one backend.

This branch does not choose between those paths yet. It only prototypes the
account, role, budget, and usage-management layer.

## Next Steps

1. Add production-style usage tests around the mock flow.
2. Connect real translation API calls to `UsageRecord`.
3. Add billing provider integration.
4. Add account-level usage enforcement.
