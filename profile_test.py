import time
import re
from skill_extractor import extract_skills_from_text
from config import SKILL_DICTIONARY

test_text = "I am a software engineer with 5 years of experience in python, java, javascript, machine learning, and artificial intelligence. I have worked on big data systems using hadoop and spark."

# Old way
def old_old_way():
    return extract_skills_from_text(test_text)

# New way
_SKILL_PATTERN = None
def _get_skill_pattern(skill_dict):
    global _SKILL_PATTERN
    if _SKILL_PATTERN is None:
        sorted_skills = sorted(skill_dict, key=len, reverse=True)
        escaped = [re.escape(s) for s in sorted_skills]
        pattern = r"\b(" + "|".join(escaped) + r")\b"
        _SKILL_PATTERN = re.compile(pattern, re.IGNORECASE)
    return _SKILL_PATTERN

def new_way():
    pattern = _get_skill_pattern(SKILL_DICTIONARY)
    matches = pattern.findall(test_text)
    return sorted(list(set(m.lower() for m in matches)))

if __name__ == "__main__":
    trials = 10000
    
    start = time.time()
    for _ in range(trials):
        old_old_way()
    print("Old time:", time.time() - start)
    
    start = time.time()
    for _ in range(trials):
        new_way()
    print("New time:", time.time() - start)
