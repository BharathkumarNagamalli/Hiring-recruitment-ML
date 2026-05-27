import os
import pickle
import numpy as np
import scipy.sparse as sp
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.model_selection import train_test_split

MODEL_DIR = os.path.join(os.path.dirname(__file__), 'saved')
LR_MODEL_PATH = os.path.join(MODEL_DIR, 'logistic_regression_model.pkl')
DT_MODEL_PATH = os.path.join(MODEL_DIR, 'decision_tree_model.pkl')
TFIDF_PATH = os.path.join(MODEL_DIR, 'tfidf_vectorizer.pkl')


class MLEngine:
    def __init__(self):
        self.lr_model = None
        self.dt_model = None
        self.tfidf = None
        os.makedirs(MODEL_DIR, exist_ok=True)

    def models_exist(self):
        return (os.path.exists(LR_MODEL_PATH) and
                os.path.exists(DT_MODEL_PATH) and
                os.path.exists(TFIDF_PATH))

    def load_models(self):
        with open(LR_MODEL_PATH, 'rb') as f:
            self.lr_model = pickle.load(f)
        with open(DT_MODEL_PATH, 'rb') as f:
            self.dt_model = pickle.load(f)
        with open(TFIDF_PATH, 'rb') as f:
            self.tfidf = pickle.load(f)

    def save_models(self):
        with open(LR_MODEL_PATH, 'wb') as f:
            pickle.dump(self.lr_model, f)
        with open(DT_MODEL_PATH, 'wb') as f:
            pickle.dump(self.dt_model, f)
        with open(TFIDF_PATH, 'wb') as f:
            pickle.dump(self.tfidf, f)

    def _build_features(self, resume_text, job_description, required_skills, experience_years):
        combined = resume_text + ' ' + job_description
        tfidf_vec = self.tfidf.transform([combined])

        resume_lower = resume_text.lower()
        skills_list = [s.strip().lower() for s in required_skills.split(',') if s.strip()]
        skill_overlap = (
            sum(1 for s in skills_list if s in resume_lower) / max(len(skills_list), 1)
        )
        experience_match = min(experience_years / 5.0, 1.0)

        job_words = set(job_description.lower().split())
        resume_words = resume_text.lower().split()
        keyword_density = (
            sum(1 for w in resume_words if w in job_words) / max(len(resume_words), 1)
        )

        additional = sp.csr_matrix([[skill_overlap, experience_match, keyword_density]])
        X = sp.hstack([tfidf_vec, additional])
        return X, skill_overlap, experience_match

    def train(self, df):
        texts = (df['resume_text'] + ' ' + df['job_description']).tolist()
        self.tfidf = TfidfVectorizer(
            max_features=500,
            stop_words='english',
            ngram_range=(1, 2)
        )
        tfidf_matrix = self.tfidf.fit_transform(texts)

        additional = sp.csr_matrix(
            df[['skill_overlap', 'experience_match', 'keyword_density']].values
        )
        X = sp.hstack([tfidf_matrix, additional])
        y = df['label'].values

        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )

        self.lr_model = LogisticRegression(max_iter=1000, random_state=42, C=1.0)
        self.lr_model.fit(X_train, y_train)
        lr_accuracy = self.lr_model.score(X_test, y_test)

        self.dt_model = DecisionTreeClassifier(
            max_depth=10, min_samples_split=5, random_state=42
        )
        self.dt_model.fit(X_train, y_train)

        self.save_models()
        return lr_accuracy

    def match_candidate(self, resume_text, job_description, required_skills, experience_years):
        if self.lr_model is None:
            self.load_models()

        X, skill_overlap, experience_match = self._build_features(
            resume_text, job_description, required_skills, experience_years
        )

        resume_vec = self.tfidf.transform([resume_text])
        job_vec = self.tfidf.transform([job_description])
        cosine_score = float(cosine_similarity(resume_vec, job_vec)[0][0])

        lr_proba = float(self.lr_model.predict_proba(X)[0][1])

        final_score = round(
            (cosine_score * 0.35 +
             skill_overlap * 0.40 +
             lr_proba * 0.15 +
             experience_match * 0.10) * 100,
            1
        )
        final_score = min(max(final_score, 0.0), 100.0)
        status = 'Shortlisted' if final_score >= 50 else 'Rejected'

        return final_score, status

    def predict_with_dt(self, resume_text, job_description, required_skills, experience_years):
        if self.dt_model is None:
            self.load_models()
        X, _, _ = self._build_features(resume_text, job_description, required_skills, experience_years)
        prediction = int(self.dt_model.predict(X)[0])
        return 'Shortlisted' if prediction == 1 else 'Rejected'