import pandas as pd
import numpy as np
import random

RESUME_TEMPLATES = [
    "{exp} years of experience as {role}. Skills: {skills}. Projects: {projects}. Education: {edu}.",
    "Experienced {role} with {exp} years. Expert in {skills}. Built {projects}. {edu} graduate.",
    "{role} professional with {exp}+ years of hands-on experience. Technologies: {skills}. Developed {projects}.",
    "Dedicated {role} - {exp} years experience with {skills}. Delivered {projects}. Background: {edu}.",
    "Senior {role} bringing {exp} years expertise. Core skills: {skills}. Notable projects: {projects}.",
]

JOB_TEMPLATES = [
    "We are looking for a {role} with {exp}+ years experience in {skills}. Role involves {projects}.",
    "Hiring {role}. Required skills: {skills}. Responsibilities include {projects}. {exp}+ years required.",
    "Seeking an experienced {role}. Must know {skills}. Will work on {projects}. {exp}+ years preferred.",
    "Join our team as {role}. Key requirements: {skills}. {exp}+ years experience needed for {projects}.",
]

ROLES = [
    'Software Engineer', 'Python Developer', 'Data Scientist', 'Full Stack Developer',
    'Backend Developer', 'ML Engineer', 'DevOps Engineer', 'Frontend Developer',
    'Data Analyst', 'Cloud Engineer', 'NLP Engineer', 'AI Researcher'
]

ALL_SKILLS = [
    'Python', 'Java', 'JavaScript', 'TypeScript', 'React', 'Flask', 'Django',
    'FastAPI', 'TensorFlow', 'PyTorch', 'Scikit-learn', 'Pandas', 'NumPy',
    'SQL', 'PostgreSQL', 'MongoDB', 'Docker', 'Kubernetes', 'AWS', 'Azure',
    'Git', 'Node.js', 'Go', 'Redis', 'Elasticsearch', 'NLTK', 'spaCy',
    'BERT', 'Transformers', 'Linux', 'Terraform', 'Jenkins', 'HTML', 'CSS',
    'Bootstrap', 'Tableau', 'Spark', 'Kafka', 'REST API', 'GraphQL',
    'Microservices', 'CI/CD', 'Agile', 'Scrum', 'Ansible', 'Bash'
]

PROJECTS = [
    'e-commerce platforms', 'scalable REST APIs', 'ML prediction pipelines',
    'real-time analytics dashboards', 'recommendation systems', 'chatbots',
    'automation tools', 'microservices architecture', 'NLP text classifiers',
    'image recognition systems', 'data ETL pipelines', 'cloud infrastructure',
    'CI/CD automation', 'fraud detection systems', 'search engines'
]

EDUCATION = [
    'B.Tech Computer Science', 'B.E. Information Technology',
    'M.Tech AI/ML', 'B.Sc Computer Science', 'MCA',
    'B.Tech ECE', 'M.Sc Data Science', 'B.Tech Software Engineering',
    'B.E. Computer Engineering', 'Ph.D. Computer Science'
]


class DataGenerator:
    def generate(self, n=1000):
        records = []
        random.seed(42)
        np.random.seed(42)

        for _ in range(n):
            job_skills_count = random.randint(4, 9)
            job_skills = random.sample(ALL_SKILLS, job_skills_count)
            job_role = random.choice(ROLES)
            job_exp_required = random.randint(0, 8)

            job_desc = random.choice(JOB_TEMPLATES).format(
                role=job_role,
                skills=', '.join(job_skills),
                exp=job_exp_required,
                projects=random.choice(PROJECTS)
            )

            candidate_exp = random.randint(0, 12)
            is_good_match = random.random() > 0.45

            if is_good_match:
                overlap_count = random.randint(
                    max(1, job_skills_count - 2), job_skills_count
                )
                candidate_skills = random.sample(
                    job_skills, min(overlap_count, len(job_skills))
                )
                other_pool = [s for s in ALL_SKILLS if s not in job_skills]
                extra = random.sample(other_pool, random.randint(0, 4))
                candidate_skills = list(set(candidate_skills + extra))
            else:
                overlap_count = random.randint(0, max(1, job_skills_count // 4))
                candidate_skills = random.sample(
                    job_skills, min(overlap_count, len(job_skills))
                )
                other_pool = [s for s in ALL_SKILLS if s not in job_skills]
                extra = random.sample(other_pool, random.randint(3, 7))
                candidate_skills = list(set(candidate_skills + extra))

            resume_text = random.choice(RESUME_TEMPLATES).format(
                exp=candidate_exp,
                role=random.choice(ROLES),
                skills=', '.join(candidate_skills),
                projects=random.choice(PROJECTS),
                edu=random.choice(EDUCATION)
            )

            job_skills_lower = set(s.lower() for s in job_skills)
            candidate_skills_lower = set(s.lower() for s in candidate_skills)
            skill_overlap = (
                len(job_skills_lower & candidate_skills_lower) /
                max(len(job_skills_lower), 1)
            )

            experience_match = 1.0 if abs(candidate_exp - job_exp_required) <= 2 else 0.0

            job_words = set(job_desc.lower().split())
            resume_words = resume_text.lower().split()
            keyword_density = (
                sum(1 for w in resume_words if w in job_words) /
                max(len(resume_words), 1)
            )

            label = 1 if (is_good_match and skill_overlap >= 0.35) else 0
            if random.random() < 0.04:
                label = 1 - label

            records.append({
                'resume_text': resume_text,
                'job_description': job_desc,
                'skill_overlap': round(skill_overlap, 4),
                'experience_match': experience_match,
                'keyword_density': round(keyword_density, 4),
                'label': label
            })

        return pd.DataFrame(records)