import re
from collections import Counter

try:
    import nltk
    try:
        nltk.data.find('tokenizers/punkt_tab')
    except LookupError:
        nltk.download('punkt_tab', quiet=True)
    try:
        nltk.data.find('corpora/stopwords')
    except LookupError:
        nltk.download('stopwords', quiet=True)
    from nltk.corpus import stopwords
    from nltk.tokenize import word_tokenize
    NLTK_AVAILABLE = True
except Exception:
    NLTK_AVAILABLE = False

TECH_SKILLS = [
    'python', 'java', 'javascript', 'typescript', 'c++', 'c#', 'ruby', 'go',
    'rust', 'swift', 'kotlin', 'scala', 'php', 'bash', 'shell', 'r',
    'flask', 'django', 'fastapi', 'react', 'angular', 'vue', 'node.js',
    'nodejs', 'express', 'spring', 'rails', 'laravel', 'next.js', 'nextjs',
    'tensorflow', 'pytorch', 'scikit-learn', 'keras', 'pandas', 'numpy',
    'matplotlib', 'seaborn', 'scipy', 'transformers', 'bert', 'gpt',
    'nlp', 'nltk', 'spacy', 'opencv', 'yolo', 'machine learning',
    'deep learning', 'neural networks', 'hugging face',
    'sql', 'mysql', 'postgresql', 'sqlite', 'mongodb', 'redis',
    'elasticsearch', 'cassandra', 'dynamodb', 'oracle', 'sqlalchemy',
    'aws', 'azure', 'gcp', 'google cloud', 'docker', 'kubernetes',
    'terraform', 'ansible', 'jenkins', 'github actions', 'circleci',
    'linux', 'nginx', 'apache', 'git', 'rest api', 'graphql',
    'microservices', 'agile', 'scrum', 'ci/cd', 'html', 'css',
    'bootstrap', 'tailwind', 'jquery', 'webpack', 'redux',
    'tableau', 'powerbi', 'excel', 'spark', 'hadoop', 'kafka'
]


class NLPProcessor:
    def __init__(self):
        if NLTK_AVAILABLE:
            try:
                self.stop_words = set(stopwords.words('english'))
            except Exception:
                self.stop_words = set()
        else:
            self.stop_words = {
                'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at',
                'to', 'for', 'of', 'with', 'by', 'from', 'is', 'are',
                'was', 'were', 'be', 'been', 'have', 'has', 'had', 'do',
                'does', 'did', 'will', 'would', 'could', 'should', 'may',
                'might', 'shall', 'can', 'this', 'that', 'these', 'those',
                'i', 'we', 'you', 'he', 'she', 'they', 'it', 'my', 'our',
                'your', 'his', 'her', 'their', 'its'
            }

    def extract_skills(self, text):
        if not text:
            return []
        text_lower = text.lower()
        found = []
        for skill in TECH_SKILLS:
            if skill in text_lower:
                display = skill.replace('.js', '.js').replace('nlp', 'NLP')
                found.append(skill.title() if '.' not in skill else skill)
        seen = set()
        unique = []
        for s in found:
            key = s.lower()
            if key not in seen:
                seen.add(key)
                unique.append(s)
        return unique[:20]

    def extract_experience_years(self, text):
        if not text:
            return 0
        patterns = [
            r'(\d+)\s*\+?\s*years?\s*of\s*experience',
            r'(\d+)\s*\+?\s*years?\s*experience',
            r'experience\s*of\s*(\d+)\s*\+?\s*years?',
            r'(\d+)\s*yr[s]?\s*exp',
            r'(\d+)\s*year[s]?\s*exp',
        ]
        for pattern in patterns:
            match = re.search(pattern, text.lower())
            if match:
                return min(int(match.group(1)), 30)
        return 0

    def extract_email(self, text):
        pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b'
        match = re.search(pattern, text)
        return match.group(0) if match else None

    def get_top_keywords(self, text, top_n=15):
        if not text:
            return []
        if NLTK_AVAILABLE:
            try:
                tokens = word_tokenize(text.lower())
            except Exception:
                tokens = text.lower().split()
        else:
            tokens = text.lower().split()

        tokens = [
            t for t in tokens
            if t.isalpha() and t not in self.stop_words and len(t) > 3
        ]
        freq = Counter(tokens)
        return [word for word, _ in freq.most_common(top_n)]