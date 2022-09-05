# Report That Pantry Web App

## Setup & Installation

Make sure you have the latest version of Python installed.

```bash
git clone <repo-url>
```
python dependencies:
```bash
pip install -r requirements.txt
```

set up your configuration variables, create `.env` file in root directory and add

```bash
SQLALCHEMY_DATABASE_URI = 'database uri'
GOOGLE_MAPS_KEY='XXX'
MAIL_USERNAME = 'XXX'
MAIL_PASSWORD = 'XXX'

```
javascript dependencies:
```bash
cd website/static
npm i
```

## Running The App
from project root:
```bash
. venv/bin/activate
export FLASK_APP=main
flask run
```

## Viewing The App

Go to `http://127.0.0.1:5000`
