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
S3_KEY = {}
S3_SECRET = {}
S3_BUCKET = {}
DATABASE_URL = {}
MAIL_USERNAME = {}
MAIL_PASSWORD = {}
MAIL_SERVER = {}
MAIL_PORT = {}
MAIL_USE_TLS = 'True'
MAIL_USE_SSL = 'False'
SECRET_KEY = {}
```

## Running The App
You can run this app using either bash or python

using bash:
```bash
export FLASK_APP=main.py
flask run
```
using python:
```python
python main.py
```

## Viewing The App

Go to `http://127.0.0.1:5000`
