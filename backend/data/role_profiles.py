"""Role fundamentals shared by the role picker and interview planner."""

ROLE_PROFILES = {
    "python-full-stack": {"label": "Python Full Stack", "core_topics": [
        "Python fundamentals and OOP", "Django/FastAPI and REST APIs", "SQL and ORM design",
        "HTML, CSS and JavaScript", "React and frontend integration", "Authentication, testing and deployment",
    ]},
    "java-full-stack": {"label": "Java Full Stack", "core_topics": [
        "Java, OOP and collections", "Spring Boot and REST APIs", "SQL and JPA/Hibernate",
        "HTML, CSS and JavaScript", "React/Angular and frontend integration", "Security, testing and deployment",
    ]},
    "data-analytics": {"label": "Data Analytics", "core_topics": [
        "SQL querying and joins", "Data cleaning with Python/pandas", "Excel analysis",
        "Descriptive statistics", "Power BI/Tableau and visualization", "Metrics and analytical insights",
    ]},
    "data-science": {"label": "Data Science", "core_topics": [
        "Python/pandas and exploratory analysis", "Probability and statistics", "SQL and data preparation",
        "Feature engineering", "Predictive modeling and validation", "Experiment design and communicating results",
    ]},
    "data-engineer": {"label": "Data Engineer", "core_topics": [
        "SQL and data modeling", "ETL/ELT pipelines", "Spark and distributed processing",
        "Airflow and orchestration", "Cloud warehouses and data lakes", "Data quality and streaming",
    ]},
    "ai-ml-engineer": {"label": "AI/ML Engineer", "core_topics": [
        "Python and ML fundamentals", "Deep learning and neural networks", "NLP and computer vision",
        "LLMs, embeddings and RAG", "AI evaluation and responsible AI", "Model serving and MLOps",
    ]},
    "machine-learning-engineer": {"label": "Machine Learning Engineer", "core_topics": [
        "Supervised and unsupervised learning", "Feature pipelines and data leakage", "Model evaluation and tuning",
        "Python and ML frameworks", "Model deployment and inference optimization", "Monitoring, drift and retraining",
    ]},
    "business-analytics": {"label": "Business Analytics", "core_topics": [
        "Business requirements and KPIs", "SQL and Excel analysis", "Dashboards and storytelling",
        "Statistical analysis and experiments", "Forecasting and business cases", "Stakeholder communication and recommendations",
    ]},
    "mern-stack": {"label": "MERN Stack", "core_topics": [
        "JavaScript and asynchronous programming", "MongoDB and schema design", "Express and REST APIs",
        "React state and hooks", "Node.js and backend architecture", "Authentication, testing and deployment",
    ]},
}


def list_roles():
    return [{"key": key, **profile} for key, profile in ROLE_PROFILES.items()]


def get_role_profile(key):
    fresher = key.startswith("fresher:")
    role_key = key.removeprefix("fresher:")
    if role_key not in ROLE_PROFILES:
        raise ValueError("Unknown interview role. Choose a role from the list.")
    profile = ROLE_PROFILES[role_key]
    return {**profile, "label": f"Fresher {profile['label']}", "level": "fresher"} if fresher else {**profile, "level": "intermediate"}
