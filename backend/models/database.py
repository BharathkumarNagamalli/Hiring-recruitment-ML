import json
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from sqlalchemy import text
from werkzeug.security import generate_password_hash

db = SQLAlchemy()


class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(200), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(30), nullable=False, default='candidate')
    company_name = db.Column(db.String(200), default='')
    headline = db.Column(db.String(250), default='')
    phone = db.Column(db.String(50), default='')
    location = db.Column(db.String(120), default='')
    skills = db.Column(db.Text, default='')
    education = db.Column(db.Text, default='')
    experience_summary = db.Column(db.Text, default='')
    resume_text = db.Column(db.Text, default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    candidates = db.relationship('Candidate', backref='user', lazy=True)
    saved_jobs = db.relationship('SavedJob', backref='user', lazy=True)


class Job(db.Model):
    __tablename__ = 'jobs'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    required_skills = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(30), default='Open')
    company_name = db.Column(db.String(200), default='HireML Demo Company')
    location = db.Column(db.String(120), default='Remote')
    job_type = db.Column(db.String(50), default='Full-time')
    work_mode = db.Column(db.String(50), default='Remote')
    salary_range = db.Column(db.String(120), default='Not disclosed')
    experience_level = db.Column(db.String(80), default='Mid Level')
    category = db.Column(db.String(120), default='Technology')
    recruiter_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    candidates = db.relationship('Candidate', backref='job', lazy=True)
    match_results = db.relationship('MatchResult', backref='job', lazy=True)
    saved_by = db.relationship('SavedJob', backref='job', lazy=True)


class Candidate(db.Model):
    __tablename__ = 'candidates'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    name = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(200), nullable=False)
    phone = db.Column(db.String(50), default='')
    education = db.Column(db.Text, default='')
    resume_text = db.Column(db.Text, nullable=False)
    resume_filename = db.Column(db.String(255), default='')
    extracted_skills = db.Column(db.Text, default='[]')
    experience_years = db.Column(db.Integer, default=0)
    applied_job_id = db.Column(db.Integer, db.ForeignKey('jobs.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    match_results = db.relationship('MatchResult', backref='candidate', lazy=True)


class MatchResult(db.Model):
    __tablename__ = 'match_results'
    id = db.Column(db.Integer, primary_key=True)
    candidate_id = db.Column(db.Integer, db.ForeignKey('candidates.id'), nullable=False)
    job_id = db.Column(db.Integer, db.ForeignKey('jobs.id'), nullable=False)
    match_score = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(50), default='Pending')
    ai_decision = db.Column(db.String(50), default='Pending')
    pipeline_status = db.Column(db.String(50), default='Applied')
    recruiter_notes = db.Column(db.Text, default='')
    explanation_json = db.Column(db.Text, default='{}')
    model_used = db.Column(db.String(100), default='Logistic Regression')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    interviews = db.relationship('Interview', backref='match_result', lazy=True)
    messages = db.relationship('Message', backref='match_result', lazy=True)


class SavedJob(db.Model):
    __tablename__ = 'saved_jobs'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    job_id = db.Column(db.Integer, db.ForeignKey('jobs.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Interview(db.Model):
    __tablename__ = 'interviews'
    id = db.Column(db.Integer, primary_key=True)
    match_result_id = db.Column(db.Integer, db.ForeignKey('match_results.id'), nullable=False)
    scheduled_at = db.Column(db.String(100), default='')
    mode = db.Column(db.String(80), default='Video')
    interviewer = db.Column(db.String(200), default='')
    meeting_link = db.Column(db.String(300), default='')
    notes = db.Column(db.Text, default='')
    status = db.Column(db.String(50), default='Scheduled')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Message(db.Model):
    __tablename__ = 'messages'
    id = db.Column(db.Integer, primary_key=True)
    match_result_id = db.Column(db.Integer, db.ForeignKey('match_results.id'), nullable=False)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    sender_role = db.Column(db.String(30), default='system')
    body = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    sender = db.relationship('User', backref='messages')


SAMPLE_JOBS = [
    {
        "title": "Python Backend Developer",
        "description": "We are looking for a skilled Python Backend Developer experienced in building scalable REST APIs, microservices, and cloud deployments. The candidate should have strong knowledge of Flask or Django, database design, and DevOps practices.",
        "required_skills": "Python, Flask, Django, REST API, SQL, PostgreSQL, Docker, Git, Linux, Redis",
        "company_name": "CloudCore Systems",
        "location": "Hyderabad",
        "job_type": "Full-time",
        "work_mode": "Hybrid",
        "salary_range": "8-14 LPA",
        "experience_level": "2-5 Years",
        "category": "Backend Development"
    },
    {
        "title": "Data Scientist",
        "description": "Seeking a Data Scientist with experience in machine learning, statistical modeling, data visualization, and big data technologies. Must have strong Python skills and hands-on experience with Scikit-learn, TensorFlow, or PyTorch for building predictive models.",
        "required_skills": "Python, Machine Learning, TensorFlow, PyTorch, Pandas, NumPy, Scikit-learn, SQL, Tableau, Statistics",
        "company_name": "InsightWorks Analytics",
        "location": "Bengaluru",
        "job_type": "Full-time",
        "work_mode": "On-site",
        "salary_range": "10-18 LPA",
        "experience_level": "3-6 Years",
        "category": "Data Science"
    },
    {
        "title": "Full Stack Web Developer",
        "description": "Looking for a Full Stack Developer skilled in both frontend and backend development. Experience with React, Node.js, and Python required. Must be comfortable with cloud platforms, containerization, and CI/CD pipelines.",
        "required_skills": "React, JavaScript, Node.js, Python, HTML, CSS, Bootstrap, AWS, Docker, MongoDB, Git",
        "company_name": "PixelStack Labs",
        "location": "Remote",
        "job_type": "Full-time",
        "work_mode": "Remote",
        "salary_range": "7-13 LPA",
        "experience_level": "2-4 Years",
        "category": "Full Stack"
    },
    {
        "title": "DevOps Engineer",
        "description": "We need an experienced DevOps Engineer to manage CI/CD pipelines, Kubernetes clusters, cloud infrastructure, and infrastructure as code. Strong Linux and scripting skills are mandatory for this role.",
        "required_skills": "Docker, Kubernetes, Jenkins, AWS, Terraform, Linux, Python, Bash, Git, Monitoring",
        "company_name": "InfraNest Technologies",
        "location": "Pune",
        "job_type": "Full-time",
        "work_mode": "Hybrid",
        "salary_range": "9-16 LPA",
        "experience_level": "3-7 Years",
        "category": "DevOps"
    },
    {
        "title": "NLP / ML Engineer",
        "description": "Looking for an NLP Engineer with experience building natural language processing systems, text classification, named entity recognition, and working with large language models, transformers, and Hugging Face ecosystem.",
        "required_skills": "Python, NLP, NLTK, spaCy, Transformers, BERT, TensorFlow, Hugging Face, Scikit-learn, Machine Learning",
        "company_name": "LanguageAI Studio",
        "location": "Chennai",
        "job_type": "Full-time",
        "work_mode": "Remote",
        "salary_range": "12-22 LPA",
        "experience_level": "3-6 Years",
        "category": "Machine Learning"
    }
]

SAMPLE_CANDIDATES = [
    {
        "name": "Arjun Sharma", "email": "arjun@example.com", "experience_years": 3, "job_index": 0,
        "resume_text": "Python Backend Developer with 3 years of experience. Skills: Python, Flask, Django, REST API, SQL, PostgreSQL, Docker, Git, Linux, Redis. Built microservices for e-commerce platforms and fintech applications. Strong in database design and optimization. B.Tech Computer Science from JNTU Hyderabad."
    },
    {
        "name": "Priya Patel", "email": "priya@example.com", "experience_years": 5, "job_index": 1,
        "resume_text": "Data Scientist with 5 years in machine learning and statistical modeling. Proficient in Python, TensorFlow, PyTorch, Pandas, NumPy, Scikit-learn, SQL, Tableau. Published research in NLP and computer vision. Built recommendation systems and fraud detection models. Ph.D. in Computer Science from IIT Hyderabad."
    },
    {
        "name": "Rahul Verma", "email": "rahul@example.com", "experience_years": 2, "job_index": 2,
        "resume_text": "Full Stack Developer with 2 years of experience. Technologies: React, JavaScript, Node.js, Python, HTML, CSS, Bootstrap, MongoDB, Git, AWS. Built several e-commerce and SaaS applications. Good at responsive UI design and REST API integration. B.Tech IT from Osmania University."
    },
    {
        "name": "Sneha Reddy", "email": "sneha@example.com", "experience_years": 4, "job_index": 3,
        "resume_text": "DevOps Engineer with 4 years of experience in CI/CD, Docker, Kubernetes, AWS, Terraform, Linux, Python, Bash, Jenkins pipelines. Managed cloud infrastructure for 50+ microservices. Expertise in monitoring with Prometheus and Grafana. B.E. ECE from BITS Hyderabad."
    },
    {
        "name": "Kiran Kumar", "email": "kiran@example.com", "experience_years": 3, "job_index": 4,
        "resume_text": "NLP Engineer with 3 years building text classification and named entity recognition systems. Expert in Python, NLTK, spaCy, Transformers, BERT, Hugging Face, TensorFlow, Scikit-learn. Built chatbots, sentiment analysis, and document extraction systems for legal tech domain. M.Tech AI from IIIT Hyderabad."
    },
    {
        "name": "Ananya Singh", "email": "ananya@example.com", "experience_years": 1, "job_index": 0,
        "resume_text": "Junior Python developer with 1 year experience. Knows Python basics, Flask, SQL, and Git. Completed online courses in web development and REST API design. Built a personal portfolio website and a basic CRUD app. B.Tech fresher from Malla Reddy Engineering College Hyderabad."
    },
    {
        "name": "Vikram Nair", "email": "vikram@example.com", "experience_years": 6, "job_index": 1,
        "resume_text": "Senior Data Scientist with 6 years experience at top product companies. Expert in Python, Machine Learning, Deep Learning, Scikit-learn, Pandas, NumPy, SQL, Statistics, Tableau, TensorFlow. Led data science teams of 8 people. Delivered ML models reducing customer churn by 30%."
    },
    {
        "name": "Meera Krishnan", "email": "meera@example.com", "experience_years": 2, "job_index": 2,
        "resume_text": "Frontend developer transitioning to full stack. Strong in HTML, CSS, JavaScript, React, Bootstrap. Currently learning Node.js and Python Flask. Comfortable with Git, basic AWS EC2. Built 10+ responsive web projects for clients. Available for full stack roles."
    },
    {
        "name": "Suresh Babu", "email": "suresh@example.com", "experience_years": 5, "job_index": 3,
        "resume_text": "Cloud and DevOps specialist with 5 years experience. Expertise: Docker, Kubernetes, AWS, Azure, GCP, Terraform, Jenkins, Bash, Python, Linux. Certified AWS Solutions Architect and Kubernetes Administrator. Reduced infrastructure costs by 40% at previous company."
    },
    {
        "name": "Deepika Rao", "email": "deepika@example.com", "experience_years": 2, "job_index": 4,
        "resume_text": "Machine learning engineer with NLP focus. 2 years experience in Python, NLTK, spaCy, text classification, sentiment analysis, Scikit-learn, basic Transformers. M.Tech in Artificial Intelligence from NIT Warangal. Built resume screening and customer feedback analysis tools."
    },
    {
        "name": "Arun Menon", "email": "arun@example.com", "experience_years": 4, "job_index": 0,
        "resume_text": "Python developer with 4 years backend experience. Flask, FastAPI, Django REST Framework, PostgreSQL, Redis, Docker, Kubernetes, AWS, Git, Linux. Built scalable REST APIs serving 2 million daily requests. Strong in Python performance optimization and database query tuning."
    },
    {
        "name": "Pooja Gupta", "email": "pooja@example.com", "experience_years": 0, "job_index": 1,
        "resume_text": "Fresh graduate interested in data science and analytics. Completed final year project in Python with basic machine learning using Scikit-learn and Pandas. Good at mathematics and statistics. Seeking entry level data analyst or junior data scientist role. B.Tech Computer Science 2025."
    },
    {
        "name": "Ravi Teja", "email": "ravi@example.com", "experience_years": 3, "job_index": 2,
        "resume_text": "Full stack developer with 3 years experience. Technologies: React, Node.js, Express, MongoDB, Python, Django, HTML, CSS, Bootstrap, AWS EC2, Git. Built web apps and dashboards for startups. Strong UI/UX skills and REST API development. Experience with Agile and Scrum methodology."
    },
    {
        "name": "Lakshmi Devi", "email": "lakshmi@example.com", "experience_years": 7, "job_index": 3,
        "resume_text": "Senior DevOps and Site Reliability Engineer with 7 years experience. Expert in Docker, Kubernetes, Helm, Terraform, AWS, GCP, Jenkins, GitLab CI/CD, Python, Go, Linux. Built monitoring systems with Prometheus and Grafana. Led DevOps transformation at a 200-person engineering org."
    },
    {
        "name": "Harish Goud", "email": "harish@example.com", "experience_years": 1, "job_index": 4,
        "resume_text": "Recent B.Tech graduate with NLP internship experience. Worked with Python, NLTK, basic spaCy, text preprocessing, TF-IDF vectorization, and sentiment analysis. Completed Coursera NLP specialization. Eager to learn BERT, Transformers, and Hugging Face ecosystem."
    },
    {
        "name": "Swathi Nair", "email": "swathi@example.com", "experience_years": 3, "job_index": 0,
        "resume_text": "Backend developer specializing in Python ecosystem. 3 years experience with Flask, SQLAlchemy, PostgreSQL, REST APIs, unit testing with pytest, CI/CD with GitHub Actions, Docker. Built multi-tenant SaaS backend serving B2B clients. Strong code quality and documentation habits."
    },
    {
        "name": "Naveen Kumar", "email": "naveen@example.com", "experience_years": 2, "job_index": 1,
        "resume_text": "Data analyst with Python and SQL skills. Pandas, NumPy, Matplotlib, Seaborn, basic Scikit-learn machine learning. Good at data cleaning, exploratory data analysis, and visualization dashboards. 2 years in business analytics role at retail company. Tableau certified."
    },
    {
        "name": "Bhavana Reddy", "email": "bhavana@example.com", "experience_years": 4, "job_index": 2,
        "resume_text": "Full stack engineer with 4 years experience building SaaS products. React, TypeScript, Node.js, Express, Python, FastAPI, PostgreSQL, MongoDB, Docker, AWS, Git, CI/CD. Led frontend architecture for a product with 50K monthly users. Strong in performance optimization."
    },
    {
        "name": "Chetan Sharma", "email": "chetan@example.com", "experience_years": 5, "job_index": 3,
        "resume_text": "DevOps and SRE engineer with 5 years experience at product startups. Docker, Kubernetes, AWS EKS, Terraform, Ansible, Jenkins, Python, Bash. Designed and maintained CI/CD pipelines for 30+ microservices. Expertise in incident management, on-call rotations, and post-mortem analysis."
    },
    {
        "name": "Divya Menon", "email": "divya@example.com", "experience_years": 3, "job_index": 4,
        "resume_text": "NLP researcher with 3 years industry experience in text processing systems. Python, Transformers, BERT, GPT fine-tuning, spaCy, Hugging Face, text classification, NER, question answering, TensorFlow, PyTorch, Scikit-learn. Published 2 papers in NLP conferences. M.Tech AI from IIIT Bangalore."
    }
]


def init_db(app, ml_engine):
    db.create_all()
    _upgrade_schema()
    _seed_demo_users()

    if not ml_engine.models_exist():
        print("[HireML] Training ML models from scratch...")
        from utils.data_generator import DataGenerator
        generator = DataGenerator()
        df = generator.generate(1000)
        accuracy = ml_engine.train(df)
        print(f"[HireML] ML models trained! Accuracy: {accuracy:.2%}")
    else:
        ml_engine.load_models()
        print("[HireML] ML models loaded successfully.")

    if Job.query.count() == 0:
        print("[HireML] Seeding sample jobs and candidates...")
        from utils.nlp_processor import NLPProcessor
        nlp = NLPProcessor()
        jobs = []

        for job_data in SAMPLE_JOBS:
            job = Job(**job_data)
            db.session.add(job)
            jobs.append(job)
        db.session.commit()

        for c_data in SAMPLE_CANDIDATES:
            job = jobs[c_data['job_index']]
            extracted_skills = nlp.extract_skills(c_data['resume_text'])

            candidate = Candidate(
                name=c_data['name'],
                email=c_data['email'],
                resume_text=c_data['resume_text'],
                extracted_skills=json.dumps(extracted_skills),
                experience_years=c_data['experience_years'],
                applied_job_id=job.id
            )
            db.session.add(candidate)
            db.session.flush()

            score, status = ml_engine.match_candidate(
                c_data['resume_text'],
                job.description,
                job.required_skills,
                c_data['experience_years']
            )

            match_result = MatchResult(
                candidate_id=candidate.id,
                job_id=job.id,
                match_score=score,
                status=status,
                ai_decision=status,
                pipeline_status=status,
                model_used='Logistic Regression + TF-IDF'
            )
            db.session.add(match_result)

        db.session.commit()
        print("[HireML] Sample data seeded! 5 jobs + 20 candidates ready.")


def _ensure_column(table_name, column_name, column_sql):
    existing = {
        row[1] for row in db.session.execute(text(f"PRAGMA table_info({table_name})"))
    }
    if column_name in existing:
        return False

    db.session.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_sql}"))
    return True


def _upgrade_schema():
    _ensure_column(
        'jobs',
        'company_name',
        "company_name VARCHAR(200) DEFAULT 'HireML Demo Company'"
    )
    _ensure_column(
        'jobs',
        'location',
        "location VARCHAR(120) DEFAULT 'Remote'"
    )
    _ensure_column(
        'jobs',
        'job_type',
        "job_type VARCHAR(50) DEFAULT 'Full-time'"
    )
    _ensure_column(
        'jobs',
        'work_mode',
        "work_mode VARCHAR(50) DEFAULT 'Remote'"
    )
    _ensure_column(
        'jobs',
        'salary_range',
        "salary_range VARCHAR(120) DEFAULT 'Not disclosed'"
    )
    _ensure_column(
        'jobs',
        'experience_level',
        "experience_level VARCHAR(80) DEFAULT 'Mid Level'"
    )
    _ensure_column(
        'jobs',
        'category',
        "category VARCHAR(120) DEFAULT 'Technology'"
    )
    _ensure_column(
        'jobs',
        'recruiter_id',
        "recruiter_id INTEGER"
    )
    job_status_added = _ensure_column(
        'jobs',
        'status',
        "status VARCHAR(30) DEFAULT 'Open'"
    )
    _ensure_column(
        'candidates',
        'user_id',
        "user_id INTEGER"
    )
    _ensure_column(
        'candidates',
        'phone',
        "phone VARCHAR(50) DEFAULT ''"
    )
    _ensure_column(
        'candidates',
        'education',
        "education TEXT DEFAULT ''"
    )
    _ensure_column(
        'candidates',
        'resume_filename',
        "resume_filename VARCHAR(255) DEFAULT ''"
    )
    ai_decision_added = _ensure_column(
        'match_results',
        'ai_decision',
        "ai_decision VARCHAR(50)"
    )
    pipeline_status_added = _ensure_column(
        'match_results',
        'pipeline_status',
        "pipeline_status VARCHAR(50) DEFAULT 'Applied'"
    )
    _ensure_column(
        'match_results',
        'recruiter_notes',
        "recruiter_notes TEXT DEFAULT ''"
    )
    _ensure_column(
        'match_results',
        'explanation_json',
        "explanation_json TEXT DEFAULT '{}'"
    )

    if job_status_added:
        db.session.execute(text(
            "UPDATE jobs SET status = 'Open' WHERE status IS NULL OR status = ''"
        ))

    if ai_decision_added:
        db.session.execute(text(
            "UPDATE match_results SET ai_decision = status "
            "WHERE ai_decision IS NULL OR ai_decision = ''"
        ))

    if pipeline_status_added:
        db.session.execute(text(
            "UPDATE match_results SET pipeline_status = status "
            "WHERE status IN ('Shortlisted', 'Rejected')"
        ))

    db.session.commit()


def _seed_demo_users():
    demo_users = [
        {
            'name': 'Admin User',
            'email': 'admin@hireml.local',
            'password': 'admin123',
            'role': 'admin',
            'company_name': 'HireML Platform',
            'headline': 'Platform administrator',
            'location': 'Hyderabad'
        },
        {
            'name': 'Demo Recruiter',
            'email': 'recruiter@hireml.local',
            'password': 'recruiter123',
            'role': 'recruiter',
            'company_name': 'HireML Demo Company',
            'headline': 'Technical recruiter',
            'location': 'Hyderabad'
        },
        {
            'name': 'Demo Candidate',
            'email': 'candidate@hireml.local',
            'password': 'candidate123',
            'role': 'candidate',
            'company_name': '',
            'headline': 'Python backend developer',
            'location': 'Hyderabad',
            'skills': 'Python, Flask, SQL, Docker, Git',
            'experience_summary': 'Backend developer with experience in Flask APIs and SQL systems.',
            'education': 'B.Tech Computer Science',
            'resume_text': 'Python backend developer with Flask, SQL, Docker, Git and REST API experience.'
        }
    ]

    for item in demo_users:
        if User.query.filter_by(email=item['email']).first():
            continue
        user = User(
            name=item['name'],
            email=item['email'],
            password_hash=generate_password_hash(item['password']),
            role=item['role'],
            company_name=item.get('company_name', ''),
            headline=item.get('headline', ''),
            location=item.get('location', ''),
            skills=item.get('skills', ''),
            education=item.get('education', ''),
            experience_summary=item.get('experience_summary', ''),
            resume_text=item.get('resume_text', '')
        )
        db.session.add(user)

    db.session.commit()
