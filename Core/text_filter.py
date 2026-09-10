import re
import pandas as pd

# Expanded blocklist for Senior, Mid-Level, and Lead roles
EXPERT_KEYWORDS = [
    "senior", "sr", "sr.", "lead", "principal", "architect", "staff", 
    "director", "manager", "chief", "vp", "head", "ii", "iii", 
    "iv", "level 2", "level 3", "experienced", "mid", "mid-level", "middle"
]
EXPERT_REGEX = re.compile(r'\b(' + '|'.join([re.escape(k) for k in EXPERT_KEYWORDS]) + r')\b', re.IGNORECASE)

# Strictly require explicit junior or entry-level keywords
JUNIOR_KEYWORDS = [
    "junior", "jr", "entry", "entry-level", "intern", "internship", 
    "trainee", "fresher", "new grad", "graduate"
]
JUNIOR_REGEX = re.compile(r'\b(' + '|'.join([re.escape(k) for k in JUNIOR_KEYWORDS]) + r')\b', re.IGNORECASE)

def safe_str(value, default: str = "") -> str:
    if value is None or pd.isna(value):
        return default
    return str(value)

def check_remote(row) -> bool:
    """Scans the full description to strictly block hybrid/onsite and ensure 100% remote status."""
    location = safe_str(row.get("location")).lower()
    title = safe_str(row.get("title")).lower()
    desc = safe_str(row.get("description")).lower() # Scans full un-truncated description
    
    # INSTANT BLOCK: Catch hidden hybrid or onsite terms anywhere in the full text
    forbidden_hybrid_keywords = [
        "hybrid", "on-site", "onsite", "in-office", "in office", 
        "days a week in", "days per week in", "office-based", "relocation"
    ]
    
    if any(kw in location for kw in forbidden_hybrid_keywords):
        return False
    if any(kw in title for kw in forbidden_hybrid_keywords):
        return False
    if any(kw in desc for kw in forbidden_hybrid_keywords):
        return False

    # Check for true remote keywords
    remote_keywords = ["remote", "work from home", "wfh", "anywhere", "telecommute"]
    has_remote = (
        any(kw in location for kw in remote_keywords) or 
        any(kw in title for kw in remote_keywords) or 
        any(kw in desc for kw in remote_keywords)
    )
    
    return has_remote

def evaluate_job(row) -> bool:
    """
    Executes the strict filter pipeline.
    Returns True to Store, False to Discard.
    """
    # 1. Full-Text Strict Remote & Hybrid Check
    if not check_remote(row):
        return False

    title = safe_str(row.get("title"))
    desc = safe_str(row.get("description"))
    text_to_search = f"{title} {desc}"

    # 2. Expertise & Seniority Check (Drops if any senior/mid-level keyword is found)
    if bool(EXPERT_REGEX.search(text_to_search)):
        return False

    # 3. Junior / Entry / Intern Requirement Check (Must have at least one junior keyword)
    if not bool(JUNIOR_REGEX.search(text_to_search)):
        return False

    # Passed all strict filters
    return True