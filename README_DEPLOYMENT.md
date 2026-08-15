# ResumeIQ — Deployment Ready

## Local run
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
export SECRET_KEY="a-long-random-secret"
python app.py
```
Open http://127.0.0.1:5000

## Render
1. Put this project in a GitHub repository.
2. Create a Render Web Service from the repository.
3. Build command: `pip install -r requirements.txt`
4. Start command: `gunicorn app:app`
5. Set `SECRET_KEY` as a secret environment variable.
6. Deploy and use the generated HTTPS URL.

## Production note
This is suitable for a demo/small project. For serious multi-user production, move SQLite to PostgreSQL and uploads to persistent object storage.
