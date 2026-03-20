# POA System (Power of Attorney Management)

A web-based system built with **Flask** to manage Power of Attorney records inside a legal office.

The system helps organize clients, power of attorney records, users, and reports in a structured and secure way.

---

## Features

- User authentication system
- Manage Power of Attorney records
- Client management
- Activity tracking
- Reports and statistics
- File upload for documents
- Session management
- User management

---

## Tech Stack

- Python
- Flask
- Flask-SQLAlchemy
- Flask-Login
- SQLite
- HTML / CSS / Jinja2

---

## Project Structure

```

poa-system
│
├── app
│   ├── routes
│   ├── templates
│   ├── static
│   ├── models.py
│   └── utils.py
│
├── instance
│   └── qanoony.db
│
├── config.py
├── run.py
├── requirements.txt
└── seed_data.py

````

---

## Installation

Clone the repository

```bash
git clone https://github.com/hagaramr2005/poa-system.git
````

Move to project folder

```bash
cd poa-system
```

Create virtual environment

```bash
python -m venv .venv
```

Activate environment

```bash
.venv\Scripts\activate
```

Install dependencies

```bash
pip install -r requirements.txt
```

Run the application

```bash
python run.py
```

Open in browser

```
http://127.0.0.1:5000
```

---

## Notes

* The project uses **SQLite** for development.
* Uploaded files are stored in `app/static/uploads`.
* For production deployment it is recommended to use **PostgreSQL**.

---

## Author

Developed by **Hagar Amr & Youssef Hesham**
Computer and Data Science Student

