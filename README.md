# Report That Pantry

## Description

Little Free Pantries are small food pantries located around the world aimed at targeted food insecurity. ReportThatPantry.org is dedicated to helping food pantries remain stocked through the use of QR code technology. QR codes that link to our site are placed on food pantries, which allow pantry stewards to stay up to date on the current status of their pantries.

## Setup & Installtion

Make sure you have the latest version of Python installed. It is recommended to use a virtual enviornment.

```bash
git clone <repo-url>
```

```bash
pip install -r requirements.txt
```
create .env file in root directory with:
```
SQLALCHEMY_DATABASE_URI = {database_uri_here}
MAIL_USERNAME = {mail_username_here}
MAIL_PASSWORD = {mail_password_here}
```

## Running The App

```bash
flask run
```

## Viewing The App

Go to `http://127.0.0.1:5000`
