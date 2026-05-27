# HireML — Hiring & Recruitment Process Optimization

An AI-powered full-stack recruitment platform built with Python, Flask, Scikit-learn, NLTK, and SQLite. Automates candidate-job matching using ML models and NLP-based resume parsing.

---

## Project Structure

```
Hiring-recruitment-ML/
├── backend/                    # Python Flask backend
│   ├── app.py                  # Main Flask app & all routes
│   ├── models/
│   │   ├── database.py         # SQLAlchemy models (Job, Candidate, User...)
│   │   └── ml_engine.py        # ML matching engine (TF-IDF + Logistic Regression)
│   ├── utils/
│   │   ├── nlp_processor.py    # Resume parsing, skill extraction, NLP utils
│   │   └── data_generator.py   # Synthetic training data generator
│   └── requirements.txt        # Python dependencies
│
├── frontend/                   # Templates and static assets
│   ├── templates/              # Jinja2 HTML templates
│   │   ├── index.html
│   │   ├── apply.html
│   │   ├── jobs.html
│   │   ├── dashboard.html
│   │   ├── recruiter.html
│   │   └── ...
│   └── static/
│       ├── css/style.css
│       └── js/main.js
│
├── Procfile                    # Render/Railway deployment config
├── .gitignore
└── README.md
```

---

## Features

- Resume parsing (PDF, DOCX, TXT) with NLP keyword extraction
- ML matching engine — TF-IDF + Logistic Regression + Decision Tree
- Role-based auth: Candidate, Recruiter, Admin
- Real-time scoring dashboard with Chart.js analytics
- Candidate pipeline: Applied → Shortlisted → Interview → Hired
- Job board with filters (location, type, work mode, category)
- Shortlisted candidate CSV export
- Auto-trains on 1000+ synthetic candidate-job pairs on first run

---

## Tech Stack

| Layer     | Technologies                                          |
|-----------|-------------------------------------------------------|
| Backend   | Python, Flask, SQLAlchemy, Scikit-learn, NLTK, Pandas |
| Frontend  | HTML5, Bootstrap 5, Chart.js, JavaScript, Jinja2      |
| Database  | SQLite                                                |
| Deployment| Render / Railway                                      |

---

## Setup & Run

```bash
# 1. Clone the repo
git clone https://github.com/BharathkumarNagamalli/Hiring-recruitment-ML.git
cd Hiring-recruitment-ML

# 2. Install dependencies
pip install -r backend/requirements.txt

# 3. Run the app
python -m backend.app
```

Open `http://localhost:5000` in your browser.

> On first run: ML models auto-train (~10 seconds), 5 sample jobs and 20 sample candidates are seeded.

---

## Deployment on Render

1. Push to GitHub
2. Go to [render.com](https://render.com) → New Web Service → Connect repo
3. **Build command:** `pip install -r backend/requirements.txt`
4. **Start command:** `gunicorn backend.app:app --bind 0.0.0.0:$PORT`

---

## Author

**Bharath Kumar Nagamalli**  
[GitHub](https://github.com/BharathkumarNagamalli) · [Portfolio](https://BharathkumarNagamalli.github.io) · [LinkedIn](https://linkedin.com/in/bharath-kumar-nagamalli-711587233)
