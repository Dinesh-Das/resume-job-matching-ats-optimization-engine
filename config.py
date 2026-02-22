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
MAX_WORKERS = max(1, min(16, CPU_COUNT - 2))           # e.g. 18
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
