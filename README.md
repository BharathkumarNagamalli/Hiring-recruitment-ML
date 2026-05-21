# HireML - Hiring & Recruitment Process Optimization using ML

An AI-powered full-stack recruitment platform built with Python, Flask, Scikit-learn, NLTK, Pandas, and SQLite.

## Features

- Resume parsing (PDF + text) with NLP keyword extraction
- ML matching engine (TF-IDF + Logistic Regression + Decision Tree)
- Real-time scoring dashboard with Chart.js analytics
- Shortlisted candidate CSV export
- Auto-trained on 1000+ synthetic candidate-job pairs

## Tech Stack

**Backend:** Python, Flask, SQLAlchemy, Scikit-learn, Pandas, NLTK  
**Frontend:** HTML5, Bootstrap 5, Chart.js, JavaScript  
**Database:** SQLite  
**Deployment:** Render / Railway

## Setup & Run

```bash
# 1. Clone the repo
git clone https://github.com/BharathkumarNagamalli/hiring-recruitment-ml.git
cd hiring-recruitment-ml

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the app
python app.py
```

Open `http://localhost:5000` in your browser.

On first run:

- ML models are auto-trained (takes ~10 seconds)
- 5 sample jobs and 20 sample candidates are seeded

## Deployment on Render

1. Push to GitHub
2. Go to render.com → New Web Service
3. Connect your repo
4. Build command: `pip install -r requirements.txt`
5. Start command: `gunicorn app:app --bind 0.0.0.0:$PORT`

## Project Structure
