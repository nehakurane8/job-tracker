# JobTrack - Job Application Tracker

A full stack job application tracker with a Kanban-style dashboard, built with FastAPI, SQLAlchemy and JavaScript.

## Features
- User registration and login with JWT authentication
- Passwords stored as secure hashes
- Each user can access only their own applications
- Kanban board: Applied, Interview, Selected, Rejected
- Auto-generated Swagger API docs at /docs

## Tech Stack
Python, FastAPI, SQLAlchemy, SQLite, JWT, JavaScript, HTML/CSS

## How to run
```bash
git clone https://github.com/nehakurane8/job-tracker.git
cd job-tracker
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload
```
Open http://127.0.0.1:8000 (API docs at http://127.0.0.1:8000/docs)

## API Endpoints
| Method | Endpoint | Description |
|---|---|---|
| POST | /register | Create an account |
| POST | /login | Get a JWT token |
| GET | /jobs | List my applications |
| POST | /jobs | Add an application |
| PUT | /jobs/{id} | Update an application |
| DELETE | /jobs/{id} | Delete an application |