# Report That Pantry Web App

## Setup & Installtion

Make sure you have the latest version of Python installed.

```bash
git clone <repo-url>
```

```bash
pip install -r requirements.txt
```

```bash
create .env file in root directory and add 
SQLALCHEMY_DATABASE_URI = {database_uri_here} and save it
GOOGLE_MAPS_KEY='XXX'
MAIL_USERNAME = 'XXX'
MAIL_PASSWORD = 'XXX'

```

## Running The App

```bash
. venv/bin/activate
export FLASK_APP=main
flask run
```

## Viewing The App

Go to `http://127.0.0.1:5000`
