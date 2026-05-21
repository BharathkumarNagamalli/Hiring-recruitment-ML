import os
import json
import csv
import io
import re
from functools import wraps
from flask import Flask, render_template, request, jsonify, redirect, url_for, send_file, abort, session, flash
from werkzeug.security import check_password_hash, generate_password_hash
from models.database import db, Job, Candidate, MatchResult, User, SavedJob, Interview, Message, init_db
from models.ml_engine import MLEngine
from utils.nlp_processor import NLPProcessor
import json as json_module

app = Flask(__name__)
@app.template_filter('fromjson')
def fromjson_filter(value):
    try:
        return json_module.loads(value) if value else []
    except:
        return []
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'hireml-secret-key-2025')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///hiring.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

db.init_app(app)
ml_engine = MLEngine()
nlp_processor = NLPProcessor()
PIPELINE_STATUSES = ['Applied', 'Shortlisted', 'Interview', 'Rejected', 'Hired']
JOB_STATUSES = ['Open', 'Paused', 'Closed']
USER_ROLES = ['candidate', 'recruiter', 'admin']
JOB_TYPES = ['Full-time', 'Part-time', 'Internship', 'Contract', 'Freelance']
WORK_MODES = ['Remote', 'Hybrid', 'On-site']
_app_initialized = False


def ensure_initialized():
    global _app_initialized
    if _app_initialized:
        return
    with app.app_context():
        init_db(app, ml_engine)
    _app_initialized = True


@app.before_request
def initialize_on_first_request():
    ensure_initialized()


def current_user():
    user_id = session.get('user_id')
    if not user_id:
        return None
    return db.session.get(User, user_id)


@app.context_processor
def inject_current_user():
    return {
        'current_user': current_user(),
        'job_types': JOB_TYPES,
        'work_modes': WORK_MODES,
    }


def wants_json_response():
    return request.is_json or request.path.startswith('/api/')


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if current_user():
            return view(*args, **kwargs)
        if wants_json_response():
            return jsonify({'error': 'Login required'}), 401
        return redirect(url_for('login', next=request.full_path))
    return wrapped


def role_required(*roles):
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            user = current_user()
            if not user:
                if wants_json_response():
                    return jsonify({'error': 'Login required'}), 401
                return redirect(url_for('login', next=request.full_path))
            if user.role not in roles:
                if wants_json_response():
                    return jsonify({'error': 'Permission denied'}), 403
                flash('You do not have permission to open that page.', 'danger')
                return redirect(url_for('index'))
            return view(*args, **kwargs)
        return wrapped
    return decorator


def candidate_or_owner_required(result):
    user = current_user()
    if not user:
        return False
    if user.role in ('recruiter', 'admin'):
        return True
    return result.candidate.user_id == user.id or result.candidate.email.lower() == user.email.lower()


def split_skills(value):
    return [skill.strip() for skill in (value or '').split(',') if skill.strip()]


SKILL_ALIASES = {
    'js': 'javascript',
    'node': 'nodejs',
    'node js': 'nodejs',
    'node.js': 'nodejs',
    'postgres': 'postgresql',
    'postgre sql': 'postgresql',
    'k8s': 'kubernetes',
    'sklearn': 'scikit learn',
    'scikit-learn': 'scikit learn',
    'ml': 'machine learning',
    'ai': 'artificial intelligence',
    'ci cd': 'ci cd',
    'ci/cd': 'ci cd',
}


def skill_key(value):
    cleaned = (value or '').lower().strip()
    cleaned = cleaned.replace('&', ' and ')
    cleaned = re.sub(r'[^a-z0-9+#]+', ' ', cleaned)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return SKILL_ALIASES.get(cleaned, cleaned)


def parse_resume_file(file):
    if not file or not file.filename:
        return '', None

    filename = file.filename.lower()
    try:
        if filename.endswith('.pdf'):
            import pdfplumber
            with pdfplumber.open(file) as pdf:
                pages_text = [page.extract_text() or '' for page in pdf.pages]
            return ' '.join(pages_text).strip(), None

        if filename.endswith('.docx'):
            try:
                from docx import Document
            except ImportError:
                return '', 'DOCX upload needs python-docx installed. Run: pip install python-docx'

            file.stream.seek(0)
            document = Document(file.stream)
            text = ' '.join(paragraph.text for paragraph in document.paragraphs)
            return text.strip(), None

        if filename.endswith('.txt'):
            raw = file.read()
            return raw.decode('utf-8', errors='ignore').strip(), None

        return '', 'Unsupported resume file type. Please upload PDF, DOCX, TXT, or paste text.'
    except Exception as exc:
        return '', f'Could not read resume file: {exc}'


def build_match_explanation(resume_text, job, extracted_skills, experience_years, score):
    required_skills = split_skills(job.required_skills)
    candidate_skill_keys = {skill_key(skill) for skill in extracted_skills}
    normalized_resume = skill_key(resume_text)
    matched = []
    missing = []

    for skill in required_skills:
        key = skill_key(skill)
        if key in candidate_skill_keys or key in normalized_resume:
            matched.append(skill)
        else:
            missing.append(skill)

    skill_match_percent = round((len(matched) / max(len(required_skills), 1)) * 100, 1)
    job_keywords = nlp_processor.get_top_keywords(job.description, top_n=12)
    resume_keywords = set(nlp_processor.get_top_keywords(resume_text, top_n=30))
    keyword_overlap = [word for word in job_keywords if word in resume_keywords][:8]

    return {
        'matched_skills': matched,
        'missing_skills': missing,
        'skill_match_percent': skill_match_percent,
        'experience_years': experience_years,
        'experience_signal': 'Strong' if experience_years >= 3 else 'Entry-level' if experience_years <= 1 else 'Moderate',
        'keyword_overlap': keyword_overlap,
        'recommendation': 'Strong match' if score >= 70 else 'Good match' if score >= 50 else 'Needs review',
    }


def get_result_explanation(result):
    try:
        explanation = json.loads(result.explanation_json or '{}')
        if explanation:
            return explanation
    except Exception:
        pass

    skills = json.loads(result.candidate.extracted_skills) if result.candidate.extracted_skills else []
    return build_match_explanation(
        result.candidate.resume_text,
        result.job,
        skills,
        result.candidate.experience_years,
        result.match_score
    )


def attach_explanations(results):
    for result in results:
        result.explanation = get_result_explanation(result)
    return results


def serialize_job(job):
    return {
        'id': job.id,
        'title': job.title,
        'description': job.description,
        'required_skills': job.required_skills,
        'status': getattr(job, 'status', 'Open') or 'Open',
        'company_name': job.company_name or 'Company',
        'location': job.location or 'Not specified',
        'job_type': job.job_type or 'Full-time',
        'work_mode': job.work_mode or 'Remote',
        'salary_range': job.salary_range or 'Not disclosed',
        'experience_level': job.experience_level or 'Not specified',
        'category': job.category or 'Technology',
        'created_at': job.created_at.isoformat() if job.created_at else None,
    }


def is_saved_job(job_id, user=None):
    user = user or current_user()
    if not user or user.role != 'candidate':
        return False
    return SavedJob.query.filter_by(user_id=user.id, job_id=job_id).first() is not None


def job_matches_search(job, search_term):
    if not search_term:
        return True
    haystack = ' '.join([
        job.title or '',
        job.description or '',
        job.required_skills or '',
        job.company_name or '',
        job.location or '',
        job.category or '',
    ]).lower()
    return search_term.lower() in haystack


def extract_phone(text):
    match = re.search(r'(\+?\d[\d\s\-()]{8,}\d)', text or '')
    return match.group(1).strip() if match else ''


def extract_profile_from_resume(text):
    return {
        'email': nlp_processor.extract_email(text) or '',
        'phone': extract_phone(text),
        'skills': ', '.join(nlp_processor.extract_skills(text)),
        'experience_years': nlp_processor.extract_experience_years(text),
        'keywords': nlp_processor.get_top_keywords(text, top_n=12),
    }


def generate_interview_pack(job, resume_text='', candidate_name='Candidate'):
    skills = split_skills(job.required_skills)
    extracted_skills = nlp_processor.extract_skills(resume_text)
    explanation = build_match_explanation(resume_text or '', job, extracted_skills, 0, 0)
    matched = explanation.get('matched_skills', [])
    missing = explanation.get('missing_skills', skills)
    priority_skills = skills[:6]

    technical_questions = [
        f"Explain your practical experience with {skill} in a recent project."
        for skill in priority_skills[:5]
    ]
    if not technical_questions:
        technical_questions = [
            f"Walk me through how you would solve a real problem related to {job.title}."
        ]

    behavioral_questions = [
        "Tell me about a time you had to learn a new technology quickly.",
        "Describe a project where you improved quality, speed, or reliability.",
        "How do you handle unclear requirements from a stakeholder?",
        "Tell me about a mistake in a project and how you recovered.",
    ]
    practice_plan = [
        "Prepare a 60-second introduction linked to the job description.",
        "Write two STAR-format stories: one technical win and one conflict/challenge.",
        f"Revise the basics of {', '.join(priority_skills[:3]) if priority_skills else job.title}.",
        "Practice explaining one project with problem, approach, impact, and metrics.",
        "Prepare two questions to ask the interviewer about team, product, and expectations.",
    ]

    answer_tips = [
        f"Connect every answer back to {job.company_name or 'the company'} and the {job.title} role.",
        "Use numbers when possible: users served, latency improved, cost reduced, tests added.",
        "If you lack a skill, explain the closest related experience and how you would ramp up.",
    ]

    return {
        'candidate_name': candidate_name,
        'job_title': job.title,
        'company_name': job.company_name or 'Company',
        'matched_skills': matched,
        'missing_skills': missing,
        'technical_questions': technical_questions,
        'behavioral_questions': behavioral_questions,
        'practice_plan': practice_plan,
        'answer_tips': answer_tips,
    }


@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    next_url = request.args.get('next') or request.form.get('next') or ''

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        user = User.query.filter_by(email=email).first()

        if not user or not check_password_hash(user.password_hash, password):
            error = 'Invalid email or password.'
        else:
            session.clear()
            session['user_id'] = user.id
            session['role'] = user.role
            if next_url and next_url.startswith('/'):
                return redirect(next_url)
            if user.role == 'candidate':
                return redirect(url_for('candidate_dashboard'))
            if user.role == 'admin':
                return redirect(url_for('admin_dashboard'))
            return redirect(url_for('recruiter'))

    return render_template('login.html', error=error, next_url=next_url)


@app.route('/register', methods=['GET', 'POST'])
def register():
    error = None
    selected_role = request.args.get('role', 'candidate')
    if selected_role not in ('candidate', 'recruiter'):
        selected_role = 'candidate'

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        role = request.form.get('role', 'candidate')
        company_name = request.form.get('company_name', '').strip()
        location = request.form.get('location', '').strip()

        if role not in ('candidate', 'recruiter'):
            role = 'candidate'
        if not name or not email or not password:
            error = 'Name, email, and password are required.'
        elif len(password) < 6:
            error = 'Password must be at least 6 characters.'
        elif User.query.filter_by(email=email).first():
            error = 'An account already exists with this email.'
        elif role == 'recruiter' and not company_name:
            error = 'Company name is required for recruiter accounts.'
        else:
            user = User(
                name=name,
                email=email,
                password_hash=generate_password_hash(password),
                role=role,
                company_name=company_name,
                location=location
            )
            db.session.add(user)
            db.session.commit()
            session.clear()
            session['user_id'] = user.id
            session['role'] = user.role
            return redirect(url_for('candidate_profile' if role == 'candidate' else 'recruiter'))

        selected_role = role

    return render_template('register.html', error=error, selected_role=selected_role)


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))


@app.route('/')
def index():
    jobs = Job.query.filter_by(status='Open').order_by(Job.created_at.desc()).all()
    total_candidates = Candidate.query.count()
    total_jobs = Job.query.count()
    shortlisted = MatchResult.query.filter(
        MatchResult.pipeline_status.in_(['Shortlisted', 'Hired'])
    ).count()
    return render_template('index.html', jobs=jobs,
                           total_candidates=total_candidates,
                           total_jobs=total_jobs,
                           shortlisted=shortlisted)


@app.route('/jobs')
def jobs_page():
    q = request.args.get('q', '').strip()
    location = request.args.get('location', '').strip()
    job_type = request.args.get('job_type', '').strip()
    work_mode = request.args.get('work_mode', '').strip()
    category = request.args.get('category', '').strip()

    query = Job.query.filter_by(status='Open')
    if location:
        query = query.filter(Job.location.ilike(f'%{location}%'))
    if job_type:
        query = query.filter_by(job_type=job_type)
    if work_mode:
        query = query.filter_by(work_mode=work_mode)
    if category:
        query = query.filter(Job.category.ilike(f'%{category}%'))

    jobs = query.order_by(Job.created_at.desc()).all()
    jobs = [job for job in jobs if job_matches_search(job, q)]
    user = current_user()
    saved_ids = set()
    profile_skills = []

    if user and user.role == 'candidate':
        saved_ids = {
            saved.job_id for saved in SavedJob.query.filter_by(user_id=user.id).all()
        }
        profile_text = ' '.join([user.resume_text or '', user.skills or '', user.experience_summary or ''])
        profile_skills = nlp_processor.extract_skills(profile_text)

    categories = sorted({
        job.category for job in Job.query.filter_by(status='Open').all()
        if job.category
    })
    locations = sorted({
        job.location for job in Job.query.filter_by(status='Open').all()
        if job.location
    })

    return render_template(
        'jobs.html',
        jobs=jobs,
        q=q,
        location=location,
        job_type=job_type,
        work_mode=work_mode,
        category=category,
        categories=categories,
        locations=locations,
        saved_ids=saved_ids,
        profile_skills=profile_skills
    )


@app.route('/jobs/<int:job_id>')
def job_detail_public(job_id):
    job = Job.query.get_or_404(job_id)
    user = current_user()
    preview = None
    saved = is_saved_job(job.id, user)

    if user and user.role == 'candidate' and user.resume_text:
        extracted_skills = nlp_processor.extract_skills(user.resume_text)
        exp_years = nlp_processor.extract_experience_years(user.resume_text)
        score, status = ml_engine.match_candidate(
            user.resume_text, job.description, job.required_skills, exp_years
        )
        preview = {
            'score': score,
            'status': status,
            'explanation': build_match_explanation(
                user.resume_text, job, extracted_skills, exp_years, score
            )
        }

    similar_jobs = [
        item for item in Job.query.filter_by(status='Open').all()
        if item.id != job.id and (
            item.category == job.category
            or any(skill_key(skill) in skill_key(item.required_skills) for skill in split_skills(job.required_skills)[:3])
        )
    ][:4]

    return render_template(
        'job_public.html',
        job=job,
        preview=preview,
        saved=saved,
        similar_jobs=similar_jobs
    )


@app.route('/jobs/<int:job_id>/save', methods=['POST'])
@login_required
def toggle_saved_job(job_id):
    user = current_user()
    if user.role != 'candidate':
        abort(403)

    job = Job.query.get_or_404(job_id)
    saved = SavedJob.query.filter_by(user_id=user.id, job_id=job.id).first()
    if saved:
        db.session.delete(saved)
        action = 'removed'
    else:
        db.session.add(SavedJob(user_id=user.id, job_id=job.id))
        action = 'saved'
    db.session.commit()

    if wants_json_response():
        return jsonify({'success': True, 'action': action})
    return redirect(request.referrer or url_for('jobs_page'))


@app.route('/apply', methods=['GET', 'POST'])
def apply():
    jobs = Job.query.filter_by(status='Open').order_by(Job.created_at.desc()).all()
    preselected_job = request.args.get('job_id', '')

    if request.method == 'POST':
        user = current_user()
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()
        education = request.form.get('education', '').strip()
        job_id = request.form.get('job_id', '')
        experience_years = request.form.get('experience_years', '0')
        resume_text = request.form.get('resume_text', '').strip()
        resume_filename = ''

        if user and user.role == 'candidate':
            name = name or user.name
            email = email or user.email
            phone = phone or user.phone
            education = education or user.education
            resume_text = resume_text or user.resume_text

        if 'resume_file' in request.files:
            file = request.files['resume_file']
            if file and file.filename:
                resume_filename = file.filename
                parsed_text, parse_error = parse_resume_file(file)
                if parse_error:
                    return jsonify({'error': parse_error}), 400
                if parsed_text:
                    resume_text = parsed_text

        if not name or not email or not job_id or not resume_text:
            return jsonify({'error': 'Please fill all required fields including resume text.'}), 400

        try:
            job_id_int = int(job_id)
            exp_int = int(experience_years) if experience_years else 0
        except ValueError:
            return jsonify({'error': 'Invalid job or experience value.'}), 400

        job = Job.query.get(job_id_int)
        if not job:
            return jsonify({'error': 'Job not found.'}), 404
        if (job.status or 'Open') != 'Open':
            return jsonify({'error': 'This job is not accepting applications right now.'}), 400

        existing_candidate = Candidate.query.filter_by(
            email=email,
            applied_job_id=job_id_int
        ).first()
        if existing_candidate:
            return jsonify({'error': 'You have already applied for this job.'}), 409

        extracted_skills = nlp_processor.extract_skills(resume_text)
        if exp_int == 0:
            exp_int = nlp_processor.extract_experience_years(resume_text)

        candidate = Candidate(
            user_id=user.id if user and user.role == 'candidate' else None,
            name=name,
            email=email,
            phone=phone or extract_phone(resume_text),
            education=education,
            resume_text=resume_text,
            resume_filename=resume_filename,
            extracted_skills=json.dumps(extracted_skills),
            experience_years=exp_int,
            applied_job_id=job_id_int
        )
        db.session.add(candidate)
        db.session.commit()

        if user and user.role == 'candidate':
            user.resume_text = user.resume_text or resume_text
            user.skills = user.skills or ', '.join(extracted_skills)
            user.phone = user.phone or candidate.phone
            user.education = user.education or education
            db.session.commit()

        score, status = ml_engine.match_candidate(
            resume_text, job.description, job.required_skills, exp_int
        )
        explanation = build_match_explanation(
            resume_text, job, extracted_skills, exp_int, score
        )

        match_result = MatchResult(
            candidate_id=candidate.id,
            job_id=job_id_int,
            match_score=score,
            status=status,
            ai_decision=status,
            pipeline_status='Applied',
            explanation_json=json.dumps(explanation),
            model_used='Logistic Regression + TF-IDF'
        )
        db.session.add(match_result)
        db.session.commit()

        return jsonify({
            'success': True,
            'candidate_id': candidate.id,
            'score': score,
            'status': status,
            'skills': extracted_skills,
            'name': name,
            'job_title': job.title,
            'explanation': explanation
        })

    return render_template('apply.html', jobs=jobs, preselected_job=preselected_job)


@app.route('/recruiter', methods=['GET', 'POST'])
@role_required('recruiter', 'admin')
def recruiter():
    error = None

    if request.method == 'POST':
        user = current_user()
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        required_skills = request.form.get('required_skills', '').strip()
        status = request.form.get('status', 'Open').strip()
        company_name = request.form.get('company_name', '').strip() or user.company_name or 'Company'
        location = request.form.get('location', '').strip() or 'Remote'
        job_type = request.form.get('job_type', '').strip() or 'Full-time'
        work_mode = request.form.get('work_mode', '').strip() or 'Remote'
        salary_range = request.form.get('salary_range', '').strip() or 'Not disclosed'
        experience_level = request.form.get('experience_level', '').strip() or 'Not specified'
        category = request.form.get('category', '').strip() or 'Technology'

        if not title or not description or not required_skills:
            error = 'Please fill job title, job description, and required skills.'
        elif status not in JOB_STATUSES:
            error = 'Invalid job status.'
        else:
            job = Job(
                title=title,
                description=description,
                required_skills=required_skills,
                status=status,
                company_name=company_name,
                location=location,
                job_type=job_type,
                work_mode=work_mode,
                salary_range=salary_range,
                experience_level=experience_level,
                category=category,
                recruiter_id=user.id
            )
            db.session.add(job)
            db.session.commit()
            return redirect(url_for('recruiter', posted=job.id))

    jobs = Job.query.order_by(Job.created_at.desc()).all()
    posted_job_id = request.args.get('posted', '')
    action = request.args.get('action', '')
    return render_template(
        'recruiter.html',
        jobs=jobs,
        error=error,
        posted_job_id=posted_job_id,
        action=action,
        job_statuses=JOB_STATUSES
    )


@app.route('/recruiter/jobs/<int:job_id>')
@role_required('recruiter', 'admin')
def recruiter_job_detail(job_id):
    job = Job.query.get_or_404(job_id)
    results = MatchResult.query.filter_by(job_id=job_id).order_by(
        MatchResult.match_score.desc()
    ).all()
    attach_explanations(results)

    stage_counts = {
        status: sum(1 for result in results if result.pipeline_status == status)
        for status in PIPELINE_STATUSES
    }
    avg_score = round(sum(r.match_score for r in results) / len(results), 1) if results else 0

    return render_template(
        'job_detail.html',
        job=job,
        results=results,
        pipeline_statuses=PIPELINE_STATUSES,
        stage_counts=stage_counts,
        avg_score=avg_score
    )


@app.route('/recruiter/jobs/<int:job_id>/edit', methods=['GET', 'POST'])
@role_required('recruiter', 'admin')
def edit_job(job_id):
    job = Job.query.get_or_404(job_id)
    error = None

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        required_skills = request.form.get('required_skills', '').strip()
        status = request.form.get('status', 'Open').strip()
        company_name = request.form.get('company_name', '').strip()
        location = request.form.get('location', '').strip()
        job_type = request.form.get('job_type', '').strip()
        work_mode = request.form.get('work_mode', '').strip()
        salary_range = request.form.get('salary_range', '').strip()
        experience_level = request.form.get('experience_level', '').strip()
        category = request.form.get('category', '').strip()

        if not title or not description or not required_skills:
            error = 'Please fill job title, job description, and required skills.'
        elif status not in JOB_STATUSES:
            error = 'Invalid job status.'
        else:
            job.title = title
            job.description = description
            job.required_skills = required_skills
            job.status = status
            job.company_name = company_name or job.company_name
            job.location = location or job.location
            job.job_type = job_type or job.job_type
            job.work_mode = work_mode or job.work_mode
            job.salary_range = salary_range or job.salary_range
            job.experience_level = experience_level or job.experience_level
            job.category = category or job.category
            db.session.commit()
            return redirect(url_for('recruiter_job_detail', job_id=job.id))

    return render_template(
        'job_edit.html',
        job=job,
        error=error,
        job_statuses=JOB_STATUSES
    )


@app.route('/recruiter/jobs/<int:job_id>/status', methods=['POST'])
@role_required('recruiter', 'admin')
def update_job_status(job_id):
    job = Job.query.get_or_404(job_id)
    status = request.form.get('status', '').strip()
    if status not in JOB_STATUSES:
        abort(400)

    job.status = status
    db.session.commit()
    return redirect(request.referrer or url_for('recruiter'))


@app.route('/recruiter/jobs/<int:job_id>/delete', methods=['POST'])
@role_required('recruiter', 'admin')
def delete_job(job_id):
    job = Job.query.get_or_404(job_id)
    has_applications = Candidate.query.filter_by(applied_job_id=job.id).first() is not None

    if has_applications or job.match_results:
        job.status = 'Closed'
        db.session.commit()
        return redirect(url_for('recruiter', action='closed_instead_of_deleted'))

    db.session.delete(job)
    db.session.commit()
    return redirect(url_for('recruiter', action='deleted'))


@app.route('/recruiter/matches/<int:match_id>/pipeline', methods=['POST'])
@role_required('recruiter', 'admin')
def update_match_pipeline(match_id):
    result = MatchResult.query.get_or_404(match_id)

    data = request.get_json(silent=True) if request.is_json else request.form
    pipeline_status = (data.get('pipeline_status') or '').strip()
    recruiter_notes = (data.get('recruiter_notes') or '').strip()

    if pipeline_status not in PIPELINE_STATUSES:
        if request.is_json:
            return jsonify({'error': 'Invalid pipeline status'}), 400
        abort(400)

    result.pipeline_status = pipeline_status
    result.recruiter_notes = recruiter_notes
    db.session.commit()

    if request.is_json:
        return jsonify({
            'success': True,
            'id': result.id,
            'pipeline_status': result.pipeline_status,
            'recruiter_notes': result.recruiter_notes
        })

    return redirect(request.referrer or url_for('results_page'))


@app.route('/dashboard')
@role_required('recruiter', 'admin')
def dashboard():
    jobs = Job.query.all()
    candidates = Candidate.query.all()
    results = MatchResult.query.order_by(MatchResult.match_score.desc()).all()

    total = len(results)
    stage_counts = {
        status: sum(1 for r in results if r.pipeline_status == status)
        for status in PIPELINE_STATUSES
    }
    shortlisted_count = stage_counts.get('Shortlisted', 0) + stage_counts.get('Hired', 0)
    rejected_count = stage_counts.get('Rejected', 0)
    avg_score = round(sum(r.match_score for r in results) / total, 1) if total else 0

    score_bins = [0] * 10
    for r in results:
        idx = min(int(r.match_score // 10), 9)
        score_bins[idx] += 1

    top5 = results[:5]

    return render_template('dashboard.html',
                           jobs=jobs,
                           candidates=candidates,
                           results=results,
                           total=total,
                           shortlisted=shortlisted_count,
                           rejected=rejected_count,
                           avg_score=avg_score,
                           score_bins=json.dumps(score_bins),
                           stage_counts=stage_counts,
                           top5=top5)


@app.route('/results')
@role_required('recruiter', 'admin')
def results_page():
    job_id = request.args.get('job_id', '')
    min_score = request.args.get('min_score', '0')
    status_filter = request.args.get('status', '')
    ai_filter = request.args.get('ai_decision', '')
    search = request.args.get('q', '').strip()

    try:
        min_score_float = float(min_score) if min_score else 0
    except ValueError:
        min_score_float = 0

    query = MatchResult.query
    if job_id:
        try:
            query = query.filter_by(job_id=int(job_id))
        except ValueError:
            job_id = ''
    if min_score_float > 0:
        query = query.filter(MatchResult.match_score >= min_score_float)
    if status_filter:
        query = query.filter_by(pipeline_status=status_filter)
    if ai_filter:
        query = query.filter_by(status=ai_filter)

    filtered_results = query.order_by(MatchResult.match_score.desc()).all()
    if search:
        search_lower = search.lower()
        filtered_results = [
            result for result in filtered_results
            if search_lower in result.candidate.name.lower()
            or search_lower in result.candidate.email.lower()
            or search_lower in result.job.title.lower()
            or search_lower in (result.candidate.extracted_skills or '').lower()
        ]
    attach_explanations(filtered_results)
    jobs = Job.query.all()

    return render_template('results.html',
                           results=filtered_results,
                           jobs=jobs,
                           job_id=job_id,
                           min_score=min_score,
                           status_filter=status_filter,
                           ai_filter=ai_filter,
                           search=search,
                           pipeline_statuses=PIPELINE_STATUSES)


@app.route('/candidate/dashboard')
@role_required('candidate')
def candidate_dashboard():
    user = current_user()
    results = MatchResult.query.join(Candidate).filter(
        (Candidate.user_id == user.id) | (Candidate.email == user.email)
    ).order_by(MatchResult.created_at.desc()).all()
    attach_explanations(results)

    saved_jobs = SavedJob.query.filter_by(user_id=user.id).order_by(
        SavedJob.created_at.desc()
    ).all()

    profile_text = ' '.join([user.resume_text or '', user.skills or '', user.experience_summary or ''])
    candidate_skills = nlp_processor.extract_skills(profile_text)
    recommended_jobs = []
    applied_job_ids = {result.job_id for result in results}
    for job in Job.query.filter_by(status='Open').all():
        if job.id in applied_job_ids:
            continue
        score = sum(
            1 for skill in split_skills(job.required_skills)
            if skill_key(skill) in skill_key(profile_text)
        )
        if score > 0:
            recommended_jobs.append((score, job))
    recommended_jobs = [job for _, job in sorted(recommended_jobs, key=lambda item: item[0], reverse=True)[:6]]

    return render_template(
        'candidate_dashboard.html',
        results=results,
        saved_jobs=saved_jobs,
        recommended_jobs=recommended_jobs,
        candidate_skills=candidate_skills
    )


@app.route('/candidate/profile', methods=['GET', 'POST'])
@role_required('candidate')
def candidate_profile():
    user = current_user()
    extracted = None
    error = None

    if request.method == 'POST':
        user.name = request.form.get('name', '').strip() or user.name
        user.phone = request.form.get('phone', '').strip()
        user.location = request.form.get('location', '').strip()
        user.headline = request.form.get('headline', '').strip()
        user.skills = request.form.get('skills', '').strip()
        user.education = request.form.get('education', '').strip()
        user.experience_summary = request.form.get('experience_summary', '').strip()
        resume_text = request.form.get('resume_text', '').strip()

        if 'resume_file' in request.files:
            file = request.files['resume_file']
            if file and file.filename:
                parsed_text, parse_error = parse_resume_file(file)
                if parse_error:
                    error = parse_error
                elif parsed_text:
                    resume_text = parsed_text

        if resume_text:
            user.resume_text = resume_text
            extracted = extract_profile_from_resume(resume_text)
            if not user.phone and extracted.get('phone'):
                user.phone = extracted['phone']
            if not user.skills and extracted.get('skills'):
                user.skills = extracted['skills']

        if not error:
            db.session.commit()
            return redirect(url_for('candidate_profile', saved='1'))

    if user.resume_text:
        extracted = extract_profile_from_resume(user.resume_text)

    return render_template(
        'candidate_profile.html',
        user=user,
        extracted=extracted,
        error=error,
        saved=request.args.get('saved') == '1'
    )


@app.route('/candidate/applications/<int:match_id>')
@login_required
def candidate_application_detail(match_id):
    result = MatchResult.query.get_or_404(match_id)
    if not candidate_or_owner_required(result):
        abort(403)
    result.explanation = get_result_explanation(result)
    prep_pack = generate_interview_pack(
        result.job,
        result.candidate.resume_text,
        result.candidate.name
    )
    return render_template(
        'application_detail.html',
        result=result,
        prep_pack=prep_pack
    )


@app.route('/interview-prep', methods=['GET', 'POST'])
def interview_prep():
    jobs = Job.query.filter_by(status='Open').order_by(Job.created_at.desc()).all()
    selected_job = None
    prep_pack = None
    resume_text = ''
    user = current_user()

    if user and user.role == 'candidate':
        resume_text = user.resume_text or ''

    if request.method == 'POST':
        job_id = request.form.get('job_id', '')
        resume_text = request.form.get('resume_text', '').strip() or resume_text
        if job_id:
            selected_job = Job.query.get(int(job_id))
        if selected_job:
            prep_pack = generate_interview_pack(
                selected_job,
                resume_text,
                user.name if user else 'Candidate'
            )

    return render_template(
        'interview_prep.html',
        jobs=jobs,
        selected_job=selected_job,
        prep_pack=prep_pack,
        resume_text=resume_text
    )


@app.route('/api/interview-prep', methods=['POST'])
def api_interview_prep():
    data = request.get_json() or {}
    job = Job.query.get(data.get('job_id'))
    if not job:
        return jsonify({'error': 'Job not found'}), 404
    user = current_user()
    resume_text = data.get('resume_text') or (user.resume_text if user else '')
    return jsonify({
        'success': True,
        'prep': generate_interview_pack(
            job,
            resume_text,
            user.name if user else 'Candidate'
        )
    })


@app.route('/api/interview-chat', methods=['POST'])
def api_interview_chat():
    data = request.get_json() or {}
    question = (data.get('question') or '').strip()
    job = Job.query.get(data.get('job_id')) if data.get('job_id') else None
    role_text = job.title if job else 'this role'
    skills_text = job.required_skills if job else 'the required skills'

    if not question:
        return jsonify({'error': 'Question is required'}), 400

    answer = (
        f"For {role_text}, answer with a short structure: situation, action, impact, and what you learned. "
        f"Connect your example to these skills: {skills_text}. If you do not know something, be honest, "
        "explain related experience, and describe how you would learn it quickly."
    )
    return jsonify({'success': True, 'answer': answer})


@app.route('/recruiter/matches/<int:match_id>/interviews', methods=['POST'])
@role_required('recruiter', 'admin')
def schedule_interview(match_id):
    result = MatchResult.query.get_or_404(match_id)
    interview = Interview(
        match_result_id=result.id,
        scheduled_at=request.form.get('scheduled_at', '').strip(),
        mode=request.form.get('mode', 'Video').strip(),
        interviewer=request.form.get('interviewer', '').strip(),
        meeting_link=request.form.get('meeting_link', '').strip(),
        notes=request.form.get('notes', '').strip(),
        status=request.form.get('status', 'Scheduled').strip()
    )
    result.pipeline_status = 'Interview'
    db.session.add(interview)
    db.session.commit()
    return redirect(request.referrer or url_for('recruiter_job_detail', job_id=result.job_id))


@app.route('/matches/<int:match_id>/messages', methods=['POST'])
@login_required
def send_application_message(match_id):
    result = MatchResult.query.get_or_404(match_id)
    if not candidate_or_owner_required(result):
        abort(403)

    body = request.form.get('body', '').strip()
    if not body:
        return redirect(request.referrer or url_for('candidate_application_detail', match_id=match_id))

    user = current_user()
    message = Message(
        match_result_id=result.id,
        sender_id=user.id,
        sender_role=user.role,
        body=body
    )
    db.session.add(message)
    db.session.commit()
    return redirect(request.referrer or url_for('candidate_application_detail', match_id=match_id))


@app.route('/admin')
@role_required('admin')
def admin_dashboard():
    users = User.query.order_by(User.created_at.desc()).all()
    jobs = Job.query.order_by(Job.created_at.desc()).all()
    results = MatchResult.query.order_by(MatchResult.created_at.desc()).limit(20).all()
    return render_template(
        'admin.html',
        users=users,
        jobs=jobs,
        results=results,
        total_candidates=Candidate.query.count(),
        total_recruiters=User.query.filter_by(role='recruiter').count(),
        total_jobs=Job.query.count(),
        total_applications=MatchResult.query.count(),
        job_statuses=JOB_STATUSES
    )


@app.route('/admin/jobs/<int:job_id>/status', methods=['POST'])
@role_required('admin')
def admin_update_job_status(job_id):
    job = Job.query.get_or_404(job_id)
    status = request.form.get('status', '').strip()
    if status not in JOB_STATUSES:
        abort(400)
    job.status = status
    db.session.commit()
    return redirect(url_for('admin_dashboard'))


@app.route('/api/jobs', methods=['GET', 'POST'])
def api_jobs():
    if request.method == 'POST':
        user = current_user()
        if not user or user.role not in ('recruiter', 'admin'):
            return jsonify({'error': 'Recruiter login required to post jobs'}), 401
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        title = data.get('title', '').strip()
        description = data.get('description', '').strip()
        required_skills = data.get('required_skills', '').strip()
        status = data.get('status', 'Open').strip()
        if not title or not description or not required_skills:
            return jsonify({'error': 'Title, description, and required skills are required'}), 400
        if status not in JOB_STATUSES:
            return jsonify({'error': 'Invalid job status'}), 400
        job = Job(
            title=title,
            description=description,
            required_skills=required_skills,
            status=status,
            company_name=(data.get('company_name') or user.company_name or 'Company').strip(),
            location=(data.get('location') or 'Remote').strip(),
            job_type=(data.get('job_type') or 'Full-time').strip(),
            work_mode=(data.get('work_mode') or 'Remote').strip(),
            salary_range=(data.get('salary_range') or 'Not disclosed').strip(),
            experience_level=(data.get('experience_level') or 'Not specified').strip(),
            category=(data.get('category') or 'Technology').strip(),
            recruiter_id=user.id
        )
        db.session.add(job)
        db.session.commit()
        return jsonify({'success': True, 'job': serialize_job(job)})

    include_closed = request.args.get('include_closed') == '1'
    query = Job.query
    if not include_closed:
        query = query.filter_by(status='Open')
    jobs = query.order_by(Job.created_at.desc()).all()
    return jsonify([serialize_job(j) for j in jobs])


@app.route('/api/jobs/<int:job_id>', methods=['GET', 'PUT', 'PATCH', 'DELETE'])
def api_job_detail(job_id):
    job = Job.query.get_or_404(job_id)

    if request.method == 'GET':
        return jsonify(serialize_job(job))

    user = current_user()
    if not user or user.role not in ('recruiter', 'admin'):
        return jsonify({'error': 'Recruiter login required'}), 401

    if request.method in ('PUT', 'PATCH'):
        data = request.get_json() or {}
        title = data.get('title', job.title).strip()
        description = data.get('description', job.description).strip()
        required_skills = data.get('required_skills', job.required_skills).strip()
        status = data.get('status', job.status or 'Open').strip()

        if not title or not description or not required_skills:
            return jsonify({'error': 'Title, description, and required skills are required'}), 400
        if status not in JOB_STATUSES:
            return jsonify({'error': 'Invalid job status'}), 400

        job.title = title
        job.description = description
        job.required_skills = required_skills
        job.status = status
        for field in ['company_name', 'location', 'job_type', 'work_mode', 'salary_range', 'experience_level', 'category']:
            if field in data:
                setattr(job, field, (data.get(field) or '').strip())
        db.session.commit()
        return jsonify({'success': True, 'job': serialize_job(job)})

    has_applications = Candidate.query.filter_by(applied_job_id=job.id).first() is not None
    if has_applications or job.match_results:
        job.status = 'Closed'
        db.session.commit()
        return jsonify({
            'success': True,
            'deleted': False,
            'message': 'Job has applications, so it was closed instead of deleted.',
            'job': serialize_job(job)
        })

    db.session.delete(job)
    db.session.commit()
    return jsonify({'success': True, 'deleted': True})


@app.route('/api/candidates')
@role_required('recruiter', 'admin')
def api_candidates():
    candidates = Candidate.query.all()
    result = []
    for c in candidates:
        match = MatchResult.query.filter_by(candidate_id=c.id).first()
        result.append({
            'id': c.id,
            'name': c.name,
            'email': c.email,
            'skills': json.loads(c.extracted_skills) if c.extracted_skills else [],
            'experience': c.experience_years,
            'score': match.match_score if match else 0,
            'ai_decision': match.status if match else 'Pending',
            'pipeline_status': match.pipeline_status if match else 'Pending',
            'status': match.pipeline_status if match else 'Pending'
        })
    return jsonify(result)


@app.route('/api/extract-keywords', methods=['POST'])
def extract_keywords():
    data = request.get_json()
    text = data.get('text', '') if data else ''
    skills = nlp_processor.extract_skills(text)
    keywords = nlp_processor.get_top_keywords(text)
    return jsonify({'skills': skills, 'keywords': keywords})


@app.route('/api/download-shortlisted')
@role_required('recruiter', 'admin')
def download_shortlisted():
    job_id = request.args.get('job_id', '')
    query = MatchResult.query.filter(
        MatchResult.pipeline_status.in_(['Shortlisted', 'Hired'])
    )
    if job_id:
        query = query.filter_by(job_id=int(job_id))
    results = query.order_by(MatchResult.match_score.desc()).all()
    attach_explanations(results)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Rank', 'Name', 'Email', 'Job Title', 'Match Score (%)',
                     'AI Decision', 'Recruiter Stage', 'Experience (Years)',
                     'Matched Skills', 'Missing Skills', 'Recruiter Notes', 'Applied Date'])

    for rank, r in enumerate(results, 1):
        c = Candidate.query.get(r.candidate_id)
        j = Job.query.get(r.job_id)
        skills = json.loads(c.extracted_skills) if c.extracted_skills else []
        writer.writerow([
            rank, c.name, c.email, j.title,
            f"{r.match_score}%", r.status, r.pipeline_status,
            c.experience_years,
            ', '.join(r.explanation.get('matched_skills', skills)),
            ', '.join(r.explanation.get('missing_skills', [])),
            r.recruiter_notes or '',
            r.created_at.strftime('%Y-%m-%d') if r.created_at else ''
        ])

    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode('utf-8')),
        mimetype='text/csv',
        as_attachment=True,
        download_name='shortlisted_candidates.csv'
    )


@app.route('/api/stats')
@role_required('recruiter', 'admin')
def api_stats():
    total = MatchResult.query.count()
    shortlisted = MatchResult.query.filter(
        MatchResult.pipeline_status.in_(['Shortlisted', 'Hired'])
    ).count()
    rejected = MatchResult.query.filter_by(pipeline_status='Rejected').count()
    results = MatchResult.query.all()
    avg_score = round(sum(r.match_score for r in results) / total, 1) if total else 0

    score_bins = [0] * 10
    for r in results:
        idx = min(int(r.match_score // 10), 9)
        score_bins[idx] += 1

    return jsonify({
        'total': total,
        'shortlisted': shortlisted,
        'rejected': rejected,
        'applied': MatchResult.query.filter_by(pipeline_status='Applied').count(),
        'interview': MatchResult.query.filter_by(pipeline_status='Interview').count(),
        'hired': MatchResult.query.filter_by(pipeline_status='Hired').count(),
        'avg_score': avg_score,
        'score_bins': score_bins
    })


@app.route('/api/retrain', methods=['POST'])
@role_required('recruiter', 'admin')
def retrain():
    try:
        from utils.data_generator import DataGenerator
        generator = DataGenerator()
        df = generator.generate(1000)
        accuracy = ml_engine.train(df)
        return jsonify({'success': True, 'accuracy': round(accuracy * 100, 2)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    ensure_initialized()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
