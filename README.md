# Flask Web App Tutorial

## Description

Little free pantries are located around the world to combat food insecurity. Our website, [ReportThatPantry.org](http://www.reportthatpantry.org/), utilizes QR code technology to keep food pantries stocked. Our QR codes are placed on every pantry, allowing pantry stewards to track the current status of their pantries.

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
