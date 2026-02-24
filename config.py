"""
Configuration & Constants for Resume-Job Matching Engine
"""

import os

# ──────────────────────────────────────────────
# Paths
# ──────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
DATA_DIR = os.path.join(BASE_DIR, "data")
JOBS_JSON_PATH = os.path.join(DATA_DIR, "jobs.json")
MODEL_PATH = os.path.join(OUTPUT_DIR, "ats_model.joblib")
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

# ──────────────────────────────────────────────
# Hardware & Processing
# ──────────────────────────────────────────────
import multiprocessing
CPU_COUNT = multiprocessing.cpu_count()                # e.g. 20
MAX_WORKERS = max(1, CPU_COUNT - 1)                    # Push to hardware limit (leave 1 core for OS)
CHUNK_SIZE = 2000                                       # for ProcessPoolExecutor.map
MAX_RAM_GB = 30                                         # hard RAM limit

# ──────────────────────────────────────────────
# Oracle Database Defaults
# ──────────────────────────────────────────────
ORACLE_DEFAULTS = {
    "host": "localhost",
    "port": 1521,
    "service_name": "XE",
    "user": "system",
    "password": "system",
    "table_name": "JOBDETAILS",
}

# ──────────────────────────────────────────────
# TF-IDF Parameters
# ──────────────────────────────────────────────
TFIDF_PARAMS = {
    "ngram_range": (1, 3),
    "max_features": 10000,
    "min_df": 2,
    "max_df": 0.95,
    "sublinear_tf": True,
}

# ──────────────────────────────────────────────
# Synonym Map — alias → canonical form
# ──────────────────────────────────────────────
SYNONYM_MAP = {
    "js": "javascript",
    "ts": "typescript",
    "py": "python",
    "ml": "machine learning",
    "ai": "artificial intelligence",
    "dl": "deep learning",
    "nlp": "natural language processing",
    "cv": "computer vision",
    "k8s": "kubernetes",
    "aws": "amazon web services",
    "gcp": "google cloud platform",
    "azure": "microsoft azure",
    "react.js": "react",
    "reactjs": "react",
    "node.js": "nodejs",
    "vue.js": "vuejs",
    "angular.js": "angularjs",
    "mongo": "mongodb",
    "postgres": "postgresql",
    "tf": "tensorflow",
    "sklearn": "scikit-learn",
    "sci-kit learn": "scikit-learn",
    "d3.js": "d3",
    "c#": "csharp",
    "c++": "cplusplus",
    ".net": "dotnet",
    "ci/cd": "cicd",
    "devops": "devops",
    "html5": "html",
    "css3": "css",
    "sass": "scss",
    "rest api": "rest",
    "restful": "rest",
    "graphql api": "graphql",
    "docker container": "docker",
    "amazon s3": "s3",
    "ec2": "amazon ec2",
    "rds": "amazon rds",
    "sagemaker": "amazon sagemaker",
    "bigquery": "google bigquery",
    "power bi": "powerbi",
    "ms excel": "excel",
    "microsoft excel": "excel",
    "tableau desktop": "tableau",
}

# ──────────────────────────────────────────────
# Curated Skill Dictionary (canonical forms)
# ──────────────────────────────────────────────
SKILL_DICTIONARY = [
    # Programming Languages
    "python", "java", "javascript", "typescript", "csharp", "cplusplus",
    "go", "rust", "ruby", "php", "swift", "kotlin", "scala", "r",
    "matlab", "perl", "lua", "dart", "sql", "bash", "shell",

    # Web Frameworks & Libraries
    "react", "angular", "vuejs", "nextjs", "nuxtjs", "svelte",
    "django", "flask", "fastapi", "spring", "spring boot",
    "express", "nodejs", "rails", "laravel", "dotnet", "blazor",
    "jquery", "bootstrap", "tailwind", "webpack", "vite",

    # Data Science & ML
    "machine learning", "deep learning", "natural language processing",
    "computer vision", "tensorflow", "pytorch", "keras", "scikit-learn",
    "pandas", "numpy", "scipy", "matplotlib", "seaborn", "plotly",
    "xgboost", "lightgbm", "catboost", "hugging face", "transformers",
    "bert", "gpt", "llm", "rag", "langchain", "openai",
    "data science", "data analysis", "data engineering",
    "feature engineering", "model deployment", "mlops",
    "statistics", "linear regression", "logistic regression",
    "random forest", "neural network", "cnn", "rnn", "lstm",
    "reinforcement learning", "generative ai",

    # Cloud & DevOps
    "amazon web services", "google cloud platform", "microsoft azure",
    "docker", "kubernetes", "terraform", "ansible", "jenkins",
    "cicd", "github actions", "gitlab ci", "circleci",
    "linux", "nginx", "apache", "serverless", "lambda",
    "s3", "amazon ec2", "amazon rds", "amazon sagemaker",
    "google bigquery", "dataflow", "cloud functions",
    "devops", "sre", "monitoring", "prometheus", "grafana",

    # Databases
    "mysql", "postgresql", "mongodb", "redis", "elasticsearch",
    "cassandra", "dynamodb", "sqlite", "oracle", "sql server",
    "neo4j", "firebase", "supabase", "snowflake", "databricks",

    # Data Engineering
    "apache spark", "hadoop", "kafka", "airflow", "dbt",
    "etl", "data warehouse", "data lake", "data pipeline",
    "hive", "presto", "flink",

    # BI & Visualization
    "tableau", "powerbi", "looker", "excel", "google sheets",
    "d3", "superset",

    # Soft Skills & Methodologies
    "agile", "scrum", "kanban", "jira", "confluence",
    "git", "github", "gitlab", "bitbucket",
    "rest", "graphql", "microservices", "api design",
    "system design", "design patterns", "solid principles",
    "test driven development", "unit testing", "integration testing",
    "communication", "leadership", "problem solving", "teamwork",
    "project management", "stakeholder management",
]

# ──────────────────────────────────────────────
# Skill Taxonomy — skill → category
# ──────────────────────────────────────────────
SKILL_TAXONOMY = {
    # Programming Languages
    **{s: "Programming Languages" for s in [
        "python", "java", "javascript", "typescript", "csharp", "cplusplus",
        "go", "rust", "ruby", "php", "swift", "kotlin", "scala", "r",
        "matlab", "perl", "lua", "dart", "sql", "bash", "shell",
    ]},
    # Web Frameworks & Libraries
    **{s: "Web Frameworks & Libraries" for s in [
        "react", "angular", "vuejs", "nextjs", "nuxtjs", "svelte",
        "django", "flask", "fastapi", "spring", "spring boot",
        "express", "nodejs", "rails", "laravel", "dotnet", "blazor",
        "jquery", "bootstrap", "tailwind", "webpack", "vite", "html", "css", "scss",
    ]},
    # Data Science & ML
    **{s: "Data Science & ML" for s in [
        "machine learning", "deep learning", "natural language processing",
        "computer vision", "tensorflow", "pytorch", "keras", "scikit-learn",
        "pandas", "numpy", "scipy", "matplotlib", "seaborn", "plotly",
        "xgboost", "lightgbm", "catboost", "hugging face", "transformers",
        "bert", "gpt", "llm", "rag", "langchain", "openai",
        "data science", "data analysis", "data engineering",
        "feature engineering", "model deployment", "mlops",
        "statistics", "linear regression", "logistic regression",
        "random forest", "neural network", "cnn", "rnn", "lstm",
        "reinforcement learning", "generative ai",
    ]},
    # Cloud & DevOps
    **{s: "Cloud & DevOps" for s in [
        "amazon web services", "google cloud platform", "microsoft azure",
        "docker", "kubernetes", "terraform", "ansible", "jenkins",
        "cicd", "github actions", "gitlab ci", "circleci",
        "linux", "nginx", "apache", "serverless", "lambda",
        "s3", "amazon ec2", "amazon rds", "amazon sagemaker",
        "google bigquery", "dataflow", "cloud functions",
        "devops", "sre", "monitoring", "prometheus", "grafana",
    ]},
    # Databases
    **{s: "Databases" for s in [
        "mysql", "postgresql", "mongodb", "redis", "elasticsearch",
        "cassandra", "dynamodb", "sqlite", "oracle", "sql server",
        "neo4j", "firebase", "supabase", "snowflake", "databricks",
    ]},
    # Data Engineering
    **{s: "Data Engineering" for s in [
        "apache spark", "hadoop", "kafka", "airflow", "dbt",
        "etl", "data warehouse", "data lake", "data pipeline",
        "hive", "presto", "flink",
    ]},
    # BI & Visualization
    **{s: "BI & Visualization" for s in [
        "tableau", "powerbi", "looker", "excel", "google sheets", "d3", "superset",
    ]},
    # Methodologies & Tools
    **{s: "Methodologies & Tools" for s in [
        "agile", "scrum", "kanban", "jira", "confluence",
        "git", "github", "gitlab", "bitbucket",
        "rest", "graphql", "microservices", "api design",
        "system design", "design patterns", "solid principles",
        "test driven development", "unit testing", "integration testing",
    ]},
    # Soft Skills
    **{s: "Soft Skills" for s in [
        "communication", "leadership", "problem solving", "teamwork",
        "project management", "stakeholder management",
    ]},
}

# ──────────────────────────────────────────────
# Title Taxonomy — title pattern → seniority (0-5)
# ──────────────────────────────────────────────
TITLE_TAXONOMY = {
    # 0 = Intern/Trainee
    "intern": 0, "trainee": 0, "apprentice": 0, "student": 0, "co-op": 0,
    # 1 = Junior / Entry
    "junior": 1, "associate": 1, "entry level": 1, "graduate": 1, "analyst": 1,
    # 2 = Mid
    "mid": 2, "intermediate": 2, "developer": 2, "engineer": 2, "specialist": 2,
    "consultant": 2, "administrator": 2,
    # 3 = Senior / Lead
    "senior": 3, "lead": 3, "staff": 3, "principal": 3, "architect": 3,
    # 4 = Manager / Director
    "manager": 4, "director": 4, "head": 4, "supervisor": 4,
    # 5 = Executive
    "vp": 5, "vice president": 5, "cto": 5, "ceo": 5, "cio": 5,
    "cfo": 5, "chief": 5, "president": 5, "partner": 5, "founder": 5,
}

# ──────────────────────────────────────────────
# Certification Patterns (regex)
# ──────────────────────────────────────────────
CERTIFICATION_PATTERNS = [
    r"\bAWS\s+Certified\s+[\w\s\-]+(?:Associate|Professional|Specialty)\b",
    r"\bAzure\s+(?:Fundamentals|Administrator|Developer|Solutions\s+Architect|Data\s+Engineer)(?:\s+(?:Associate|Expert))?\b",
    r"\bGoogle\s+Cloud\s+(?:Professional|Associate)\s+[\w\s]+\b",
    r"\bPMP\b", r"\bPMI-ACP\b", r"\bCSM\b", r"\bCSPO\b",
    r"\bCCNA\b", r"\bCCNP\b", r"\bCCIE\b",
    r"\bCISC?SP\b", r"\bCISA\b", r"\bCISM\b", r"\bCEH\b",
    r"\bCKA\b", r"\bCKAD\b", r"\bCKS\b",
    r"\b(?:CompTIA\s+)?(?:Security\+|Network\+|A\+|Cloud\+|Data\+)\b",
    r"\bScrumMaster\b", r"\bSAFe\s+\w+\b",
    r"\bISTQB\b", r"\bITIL\b",
    r"\bOracle\s+Certified\s+[\w\s]+\b",
    r"\bTensorFlow\s+Developer\s+Certificate\b",
    r"\bMicrosoft\s+Certified\s*:?\s*[\w\s\-]+\b",
    r"\bCertified\s+(?:Kubernetes|Scrum|Data|Cloud|Ethical)\s+[\w\s]+\b",
]

# ──────────────────────────────────────────────
# Standard Resume Section Headings
# ──────────────────────────────────────────────
STANDARD_HEADINGS = [
    "summary", "professional summary", "executive summary", "profile",
    "objective", "career objective",
    "experience", "work experience", "professional experience", "employment",
    "employment history", "work history", "career history",
    "education", "academic background", "qualifications", "academic qualifications",
    "skills", "technical skills", "core competencies", "key skills", "areas of expertise",
    "certifications", "licenses", "credentials", "professional certifications",
    "projects", "key projects", "personal projects", "academic projects",
    "publications", "research", "papers", "presentations",
    "awards", "honors", "achievements", "accomplishments",
    "volunteer", "volunteering", "community involvement",
    "interests", "hobbies", "extracurricular",
    "references", "professional references",
    "languages", "language proficiency",
    "training", "professional development", "courses", "coursework",
]

# ──────────────────────────────────────────────
# Domain-Specific Stop Words (removed ON TOP of
# standard English stop words during TF-IDF)
# ──────────────────────────────────────────────
DOMAIN_STOP_WORDS = [
    "job", "position", "role", "candidate", "applicant", "company",
    "organization", "team", "experience", "years", "year", "work",
    "working", "ability", "strong", "good", "excellent", "required",
    "preferred", "must", "including", "includes", "responsibilities",
    "qualifications", "requirements", "description", "looking",
    "opportunity", "join", "apply", "submit", "resume", "salary",
    "compensation", "benefits", "location", "remote", "hybrid",
    "onsite", "full", "part", "time", "contract", "permanent",
    "immediate", "urgently", "hiring", "opening", "vacancy",
]

# ──────────────────────────────────────────────
# Scoring
# ──────────────────────────────────────────────
SCORE_SCALE = 100  # cosine similarity * SCORE_SCALE

# Skill gap classification thresholds (percentile among industry skills)
GAP_CRITICAL_THRESHOLD = 0.70   # top 30% of skills by importance
GAP_RECOMMENDED_THRESHOLD = 0.40  # next 30%
# everything below → optional

# ──────────────────────────────────────────────
# Role Clustering
# ──────────────────────────────────────────────
DEFAULT_N_CLUSTERS = 8

# ──────────────────────────────────────────────
# Reporting
# ──────────────────────────────────────────────
TOP_SKILLS_REPORT_COUNT = 50
TOP_MATCHES_COUNT = 20
BOTTOM_MATCHES_COUNT = 10
