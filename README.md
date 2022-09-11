# Report That Pantry Web App

## Setup & Installation

Make sure you have the latest version of Python installed.

```bash
git clone <repo-url>
```

Install project dependencies within a virtual environment,

```bash
python3 -m venv .venv
source ./.venv/bin/activate
pip install -r requirements.txt
```

Set up your configuration variables, create `.env` file (`cp .env.sample .env`) in root directory and fill in the environment variables.

```bash
SQLALCHEMY_DATABASE_URI = ""
GOOGLE_MAPS_KEY = ""
MAIL_USERNAME = ""
MAIL_PASSWORD = ""
TWILIO_ACCOUNT_SID = ""
TWILIO_AUTH_TOKEN = ""
```

Install javascript dependencies,

```bash
cd website/static
npm i
```

## Running The App

From project root,

```bash
. venv/bin/activate
export FLASK_APP=main
flask run
```

## Viewing The App

Go to `http://127.0.0.1:5000`

## Troubleshooting

Though not required for development some may run into issues installing `psycopg2-binary==2.8.6` — either temporarily comment this out in `requirements.txt` or install postgresql — `brew install postgresql` on mac.