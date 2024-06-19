# Report That Pantry

## Description

Little Free Pantries are small food pantries located around the world aimed at targeted food insecurity. Our website, [ReportThatPantry.org](http://reportthatpantry.org/), is dedicated to helping food pantries remain stocked through the use of QR code technology. QR codes that link to our site are placed on food pantries, which allow pantry stewards to stay up to date on the current status of their pantries.


## Contributing

If you are interesting in contributing to the development of this site, please reach out to me at info@reportthatpantry.org

## Setup & Installtion

Make sure you have the latest version of Python installed. It is recommended to use a virtual enviornment.

Clone the repo:
```bash
git clone <repo-url>
```

Install required python packages
```bash
pip install -r requirements.txt
```

Note: It is possible that psycopg2-binary might throw an error during installation. If that happens, try running
```bash
pip install psycopg2
```

create .env file in root directory with the following environment variables
```
DATABASE_URL = {database_uri_here}
MAIL_USERNAME = {mail_username_here}
MAIL_PASSWORD = {mail_password_here}
MAIL_SERVER = '{mail_server_here}'
MAIL_PORT = {mail_port_here}
MAIL_USE_TLS = False
MAIL_USE_SSL = True
SECRET_KEY = {secret_key_here}
UPLOAD_FOLDER = {upload_folder_here}
```

## Running The App

```bash
export FLASK_APP=main.py
flask run
```

## Viewing The App

Go to `http://127.0.0.1:5000`
