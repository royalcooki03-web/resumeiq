# ResumeIQ V2 — AI Resume Analyzer

## Features
- Login/Register with hashed passwords
- Dashboard
- PDF resume upload
- ATS-style score
- Matched and missing skills
- Improvement suggestions
- Analysis history
- Profile
- Logout
- Download text report
- SQLite database
- Responsive professional UI

## Mac setup

Open this folder in VS Code.

Terminal:
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py

Then open:
http://127.0.0.1:5000

Create an account first.

Note: The current analyzer is local/rule-based and does not require an API key. A real LLM/JD matching layer can be added later.
