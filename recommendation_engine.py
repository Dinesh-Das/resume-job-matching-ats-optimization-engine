"""
Recommendation Engine Module
Generates actionable resume improvement suggestions for each skill gap.
"""

import pandas as pd
import logging

logger = logging.getLogger(__name__)

# ── Placement rules ──────────────────────────
# Maps skill categories to recommended resume sections
SECTION_RULES = {
    # Programming languages → Skills section
    "python": "Skills Section",
    "java": "Skills Section",
    "javascript": "Skills Section",
    "typescript": "Skills Section",
    "sql": "Skills Section",
    "r": "Skills Section",
    "go": "Skills Section",
    "rust": "Skills Section",
    "csharp": "Skills Section",
    "cplusplus": "Skills Section",

    # Frameworks → Projects / Experience
    "react": "Projects Section",
    "angular": "Projects Section",
    "django": "Projects Section",
    "flask": "Projects Section",
    "spring boot": "Projects Section",
    "fastapi": "Projects Section",
    "nextjs": "Projects Section",

    # Cloud / DevOps → Experience
    "amazon web services": "Experience Section",
    "google cloud platform": "Experience Section",
    "microsoft azure": "Experience Section",
    "docker": "Experience Section",
    "kubernetes": "Experience Section",
    "cicd": "Experience Section",
    "terraform": "Experience Section",

    # Soft skills → Experience / Summary
    "agile": "Experience Section",
    "scrum": "Experience Section",
    "leadership": "Summary / Experience",
    "communication": "Summary / Experience",
    "project management": "Experience Section",
    "stakeholder management": "Experience Section",
}

DEFAULT_SECTION = "Skills Section"

# ── Achievement phrasing templates ────────────
PHRASING_TEMPLATES = {
    "Skills Section": "Add '{skill}' to your technical skills list.",
    "Projects Section": (
        "Highlight a project where you used {skill}. Example: "
        "\"Built a {skill}-based application that improved X by Y%.\""
    ),
    "Experience Section": (
        "Add a bullet point under a relevant role. Example: "
        "\"Leveraged {skill} to deliver/manage/optimise [specific outcome].\""
    ),
    "Summary / Experience": (
        "Mention {skill} in your professional summary or demonstrate it "
        "through leadership/collaboration achievements."
    ),
}


def _get_section(skill: str) -> str:
    """Determine the best resume section for a skill."""
    return SECTION_RULES.get(skill.lower(), DEFAULT_SECTION)


def _get_phrasing(skill: str, section: str) -> str:
    """Generate suggested phrasing for a skill."""
    template = PHRASING_TEMPLATES.get(section, PHRASING_TEMPLATES[DEFAULT_SECTION])
    return template.format(skill=skill)


def generate_recommendations(gap_df: pd.DataFrame,
                             resume_text: str = "") -> pd.DataFrame:
    """
    Generate actionable recommendations for each missing skill.

    Parameters
    ----------
    gap_df : DataFrame
        Output of gap_analyzer.analyze_gaps (with 'priority' column).
    resume_text : str
        Original resume text (used for keyword density suggestions).

    Returns
    -------
    DataFrame with columns: skill, priority, section, suggestion, action
    """
    missing = gap_df[gap_df["priority"] != "present"].copy()

    records = []
    for _, row in missing.iterrows():
        skill = row["skill"]
        priority = row["priority"]
        section = _get_section(skill)
        phrasing = _get_phrasing(skill, section)

        records.append({
            "skill": skill,
            "priority": priority,
            "importance_weight": round(row.get("importance_weight", 0), 4),
            "section": section,
            "suggestion": phrasing,
            "action": f"Add {skill}" if section == "Skills Section"
                      else f"Demonstrate {skill} with a measurable achievement",
        })

    rec_df = pd.DataFrame(records)
    if not rec_df.empty:
        # Sort: critical first, then recommended, then optional; within each by importance
        priority_order = {"critical": 0, "recommended": 1, "optional": 2}
        rec_df["_sort"] = rec_df["priority"].map(priority_order)
        rec_df = rec_df.sort_values(
            ["_sort", "importance_weight"], ascending=[True, False]
        ).drop(columns="_sort").reset_index(drop=True)

    logger.info(f"Generated {len(rec_df)} recommendations")
    return rec_df


def generate_general_tips(resume_text: str, resume_skills: list,
                          industry_top_skills: list) -> list:
    """
    Generate general resume improvement tips beyond individual skill gaps.
    """
    tips = []

    # 1. Length check
    word_count = len(resume_text.split())
    if word_count < 200:
        tips.append({
            "category": "Content Length",
            "tip": "Your resume appears very short. Aim for at least 400-600 words "
                   "to provide sufficient detail for ATS systems.",
            "priority": "high",
        })
    elif word_count > 1500:
        tips.append({
            "category": "Content Length",
            "tip": "Your resume is quite long. Consider condensing to 1-2 pages "
                   "for better ATS readability.",
            "priority": "medium",
        })

    # 2. Skill coverage
    if industry_top_skills:
        top_20 = set(s.lower() for s in industry_top_skills[:20])
        resume_set = set(s.lower() for s in resume_skills)
        coverage = len(top_20 & resume_set) / max(len(top_20), 1) * 100

        if coverage < 30:
            tips.append({
                "category": "Skill Coverage",
                "tip": f"You match only {coverage:.0f}% of the top 20 industry skills. "
                       "Focus on adding the most critical missing skills.",
                "priority": "high",
            })
        elif coverage < 60:
            tips.append({
                "category": "Skill Coverage",
                "tip": f"You match {coverage:.0f}% of the top 20 industry skills. "
                       "Good start — adding a few more high-demand skills will boost your ATS score.",
                "priority": "medium",
            })
        else:
            tips.append({
                "category": "Skill Coverage",
                "tip": f"Strong coverage at {coverage:.0f}% of top 20 skills. "
                       "Focus on demonstrating depth through achievements.",
                "priority": "low",
            })

    # 3. Quantifiable achievements
    import re
    numbers = re.findall(r"\d+%|\$\d+|\d+\+", resume_text)
    if len(numbers) < 3:
        tips.append({
            "category": "Quantifiable Achievements",
            "tip": "Add more numbers and metrics to your resume. "
                   "ATS and recruiters favour quantified accomplishments "
                   "(e.g., 'Improved performance by 40%').",
            "priority": "high",
        })

    # 4. Action verbs
    action_verbs = ["led", "built", "developed", "designed", "implemented",
                    "managed", "created", "delivered", "optimized", "automated",
                    "improved", "reduced", "increased", "launched", "architected"]
    text_lower = resume_text.lower()
    used_verbs = [v for v in action_verbs if v in text_lower]
    if len(used_verbs) < 3:
        tips.append({
            "category": "Action Verbs",
            "tip": "Use more strong action verbs (Led, Built, Designed, Optimized, etc.) "
                   "to start your bullet points.",
            "priority": "medium",
        })

    return tips
