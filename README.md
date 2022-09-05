# Report That Pantry

## Description

Little Free Pantries are small food pantries located around the world aimed at targeted food insecurity. Our website, [ReportThatPantry.org](http://reportthatpantry.org/), is dedicated to helping food pantries remain stocked through the use of QR code technology. QR codes that link to our site are placed on food pantries, which allow pantry stewards to stay up to date on the current status of their pantries.
# Report That Pantry Web App

## Setup & Installtion

Make sure you have the latest version of Python installed. It is recommended to use a virtual enviornment.

```bash
git clone <repo-url>
```
python dependencies:
```bash
pip install -r requirements.txt
```
set up your configuration variables:
```bash
create .env file in root directory and add 
SQLALCHEMY_DATABASE_URI = {database_uri_here} and save it
GOOGLE_MAPS_KEY='XXX'
MAIL_USERNAME = 'XXX'
MAIL_PASSWORD = 'XXX'

```
javascript dependencies:
```bash
cd website/static
npm i
create .env file in root directory with:
```
SQLALCHEMY_DATABASE_URI = {database_uri_here}
MAIL_USERNAME = {mail_username_here}
MAIL_PASSWORD = {mail_password_here}
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
