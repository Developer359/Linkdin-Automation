# Core/Job-search/job-quries.py

CATEGORY_ROLE_KEYWORDS = {
    "Frontend, Full Stack & Backend": [
        "frontend", "front-end", "front end", "backend", "back-end", "back end",
        "full stack", "fullstack", "full-stack", "web developer","web engineer",
         "react", "next.js", "nextjs", "node", "javascript", "typescript"
    ],
    "AI & Data Engineer": [
        "ai", "artificial intelligence", "machine learning", "ml engineer", "data scientist",
        "data analyst", "data engineer", "llm", "langchain", "automation engineer", "python developer"
    ],
    "Mobile Developer": [
        "mobile", "ios", "android", "swift", "kotlin", "react native", "flutter", "expo",
        "app developer", "mobile developer", "mobile engineer"
    ],
    "UI/UX & Graphic Designer": [
        "ui", "ux", "ui/ux", "product design", "product designer", "graphic design",
        "graphic designer", "figma", "wireframe", "visual designer", "designer"
    ],
    "Software & DevOps Engineer": [
        "devops", "dev ops", "cloud engineer", "site reliability", "sre", "platform engineer",
        "infrastructure", "software engineer", "software developer", "docker", "kubernetes", "aws"
    ],
}

# Formatted search terms for JobSpy engines
SEARCH_QUERIES = {
    "Frontend, Full Stack & Backend": "Mern stack OR Full Stack OR Frontend OR Backend OR React OR Web developer OR JavaScript ",
    "AI & Data Engineer": "AI Engineer OR Data Engineer OR Machine Learning OR Python",
    "Mobile Developer": "React Native OR Flutter OR Mobile Developer OR iOS OR Android",
    "UI/UX & Graphic Designer": "UI UX Designer OR Product Designer OR Graphic Designer",
    "Software & DevOps Engineer": "Software Engineer OR DevOps Engineer OR Cloud Engineer OR Systems Engineer OR AWS"
}