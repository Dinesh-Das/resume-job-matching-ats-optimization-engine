"""
ai_reviewer.py
--------------
AI-powered resume bullet rewriter using Google Gemini 2.0 Flash.

Public API:
  extract_weak_bullets(resume_text, missing_keywords, recommendations) -> list
  generate_rewrites(resume_text, jd_text, jd_title, missing_keywords, recommendations, bullets) -> dict
"""

import json
import re
import logging

logger = logging.getLogger(__name__)

# ── Action verbs that signal a strong bullet ──────────────────────────────────
_ACTION_VERBS = {
    "led", "built", "designed", "engineered", "developed", "architected", "created",
    "managed", "improved", "reduced", "increased", "launched", "deployed", "delivered",
    "owned", "scaled", "migrated", "automated", "implemented", "spearheaded",
    "optimized", "optimised", "established", "coordinated", "directed", "resolved",
    "introduced", "streamlined", "mentored", "authored", "evaluated", "executed",
}


def extract_weak_bullets(
    resume_text: str,
    missing_keywords: list,
    recommendations: list,
) -> list:
    """
    Identify up to 4 resume bullets most likely to benefit from rewriting.
    Filters out headers, metadata, and location lines.
    """
    bullets = []
    
    # Common headers and metadata patterns to ignore
    _IGNORE_PATTERNS = [
        r"(?i)^(languages|frontend|backend|database|tools|cloud|testing|soft skills|concurrency)\s*[-:]",
        r"(?i)\d{4}\s*[-–]\s*(present|\d{4})", # Date ranges
        r"(?i)^[A-Z\s]+(Limited|Inc|Corp|Pty|Ltd|University|College|Institute)\b", # Company/Education headers
        r"(?i),[A-Z\s]{2,}$", # Likely ending in a State (US style) or a City
        r"(?i)^(Master|Bachelor|Education|Summary|Experience|Projects|Achievements)\s*$", # Section headers
    ]
    
    for line in resume_text.split("\n"):
        stripped = line.strip()
        if not stripped:
            continue
            
        # Basic character filter
        cleaned = stripped.lstrip("-•*– ").strip()
        if len(cleaned) < 20 or len(cleaned) > 300:
            continue

        # Skip if it matches any ignore pattern
        if any(re.search(p, cleaned) for p in _IGNORE_PATTERNS):
            continue

        # Accept if it starts with a bullet character OR has an action verb early on
        # OR if it's long enough to be a descriptive sentence but not a header
        is_bullet_char = stripped[0] in ("-", "•", "*", "–")
        words = cleaned.lower().split()
        has_action_verb = any(w in _ACTION_VERBS for w in words[:3])
        
        if is_bullet_char or (has_action_verb and len(cleaned) > 40):
            bullets.append(cleaned)

    if not bullets:
        # Fallback: if we filtered everything, be more lenient but still avoid very short lines
        for line in resume_text.split("\n"):
            cleaned = line.strip().lstrip("-•*– ").strip()
            if len(cleaned) > 50 and cleaned[0].isupper():
                bullets.append(cleaned)

    def _weakness(bullet):
        score = 0
        if len(bullet) < 60:
            score += 2
        if not any(c.isdigit() for c in bullet):
            score += 2
        words = bullet.lower().split()
        if not any(w in _ACTION_VERBS for w in words[:3]):
            score += 1
        for kw in missing_keywords:
            if kw.lower() in bullet.lower():
                score -= 1
        return score

    # Clean duplicates and rank
    unique_bullets = list(set(bullets))
    ranked = sorted(unique_bullets, key=_weakness, reverse=True)[:4]

    return [
        {"bullet": b, "section": "Summary/Work", "issue": "Candidate for strengthening"}
        for b in ranked
    ]


def generate_rewrites(
    resume_text: str,
    jd_text: str,
    jd_title: str,
    missing_keywords: list,
    recommendations: list,
    bullets_to_rewrite: list,
) -> dict:
    """
    Call Gemini 2.0 Flash to rewrite weak bullets in context of the JD.

    Returns:
    {
      "available": bool,
      "rewrites": [
        {
          "original":       str,
          "rewritten":      str,
          "rationale":      str,
          "keywords_added": list[str]
        }
      ],
      "error": str | None
    }
    """
    try:
        from config import GEMINI_API_KEY, GEMINI_MODEL, GEMINI_ENABLED
    except Exception:
        return {"available": False, "rewrites": [], "error": "Configuration unavailable"}

    if not GEMINI_ENABLED:
        return {
            "available": False,
            "rewrites": [],
            "error": "AI reviewer not configured — add GEMINI_API_KEY to your .env file",
        }

    if not bullets_to_rewrite:
        return {"available": True, "rewrites": [], "error": None}

    try:
        import google.generativeai as genai

        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel(GEMINI_MODEL)

        bullets_text = "\n".join(
            f"{i + 1}. {b['bullet']}" for i, b in enumerate(bullets_to_rewrite)
        )
        missing_str = ", ".join(missing_keywords[:10]) if missing_keywords else "none identified"

        prompt = f"""You are a precise professional resume editor. Rewrite each resume bullet to better match the job description — making them stronger, more specific, and more relevant — without fabricating experience.

## Context
<target_role>{jd_title or "Not specified"}</target_role>
<job_description_excerpt>
{jd_text[:1500]}
</job_description_excerpt>
<skills_missing_from_resume>
{missing_str}
</skills_missing_from_resume>
<bullets_to_rewrite>
{bullets_text}
</bullets_to_rewrite>

## Rules
1. One to two sentences maximum per bullet
2. Start with a strong action verb (Led, Engineered, Architected, Launched, Delivered, Scaled, Automated, Implemented, Designed, Optimised)
3. Add at least one specific metric when the original has none — use realistic placeholders like [X%] or [N users] that the candidate fills in
4. Naturally incorporate 1–2 missing skills only where contextually appropriate — never force them
5. Do NOT invent job titles, companies, technologies, or dates not implied by the original
6. Maintain the same general role and context as the original bullet
7. Professional, specific tone — avoid vague phrases like "improved performance"
8. Return ONLY the JSON requested by the schema.

## Output Format
Return a JSON array of objects following the provided schema."""

        # Define the expected JSON schema
        schema = {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "original": {"type": "string"},
                    "rewritten": {"type": "string"},
                    "rationale": {"type": "string"},
                    "keywords_added": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["original", "rewritten", "rationale", "keywords_added"],
            }
        }

        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.0,  # Zero temperature for absolute consistency
                max_output_tokens=4096,
                top_p=0.95,
                response_mime_type="application/json",
                response_schema=schema,
            ),
        )

        raw = response.text.strip()
        
        # Robust cleaning: handle markdown fences if they appear despite JSON mode
        if raw.startswith("```"):
            raw = re.sub(r"^```(?:json)?\s*", "", raw)
            raw = re.sub(r"\s*```$", "", raw)
        
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            # Fallback: try to find the start of the array if there's lead-in text
            match = re.search(r"(\[.*\])", raw, re.DOTALL)
            if match:
                parsed = json.loads(match.group(1))
            else:
                raise

        validated = []
        for item in parsed:
            if isinstance(item, dict) and "original" in item and "rewritten" in item:
                validated.append({
                    "original":       str(item.get("original", "")),
                    "rewritten":      str(item.get("rewritten", "")),
                    "rationale":      str(item.get("rationale", "")),
                    "keywords_added": list(item.get("keywords_added", [])),
                })

        return {"available": True, "rewrites": validated, "error": None}

    except json.JSONDecodeError as e:
        raw_snippet = raw[:200] + "..." if len(raw) > 200 else raw
        logger.error(f"Gemini returned unparseable JSON: {e}. Raw content (start): {raw_snippet}")
        
        # Check if it looks truncated
        if len(raw) > 0 and raw[-1] not in (']', '}'):
             logger.warning("Gemini response appears truncated.")
             
        return {
            "available": True,
            "rewrites": [],
            "error": "Reviewer response format error — please try again",
        }

    except Exception as e:
        err_msg = str(e)
        logger.error(f"Gemini API error: {err_msg}")
        
        # Specifically highlight quota issues if present in the error string
        if "429" in err_msg or "quota" in err_msg.lower():
            return {
                "available": False,
                "rewrites": [],
                "error": "Gemini API Quota Exceeded. Please check your plan or try again later.",
            }
            
        return {
            "available": False,
            "rewrites": [],
            "error": "Reviewer temporarily unavailable",
        }
