import json
import os

import requests
from dotenv import load_dotenv

from guardrails import CAREER_AI_RULES, sanitize_ai_output, sanitize_chat_output

load_dotenv()

API_KEY = os.getenv("AWS_BEARER_TOKEN_BEDROCK")
REGION = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
MODEL_ID = os.getenv("BEDROCK_MODEL_ID", "us.anthropic.claude-haiku-4-5-20251001-v1:0")

if not API_KEY:
    print("WARNING: AWS_BEARER_TOKEN_BEDROCK not found in .env. AI features will not work.")

BEDROCK_URL = (
    f"https://bedrock-runtime.{REGION}.amazonaws.com"
    f"/model/{MODEL_ID}/converse"
)

headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {API_KEY or ''}",
}

AI_UNAVAILABLE_MESSAGE = (
    "I'm sorry, I'm currently unable to connect to my AI brain. Please try again later."
)

INTERVIEW_MODES = {
    "behavioral": "behavioral and situational (STAR method friendly)",
    "technical": "technical and role-specific skills",
    "leadership": "leadership, management, and executive presence",
}

SUPPORTED_CURRENCIES = {
    "USD": {"symbol": "$", "name": "US Dollar"},
    "EUR": {"symbol": "€", "name": "Euro"},
    "GBP": {"symbol": "£", "name": "British Pound"},
    "INR": {"symbol": "₹", "name": "Indian Rupee"},
    "CAD": {"symbol": "C$", "name": "Canadian Dollar"},
    "AUD": {"symbol": "A$", "name": "Australian Dollar"},
    "SGD": {"symbol": "S$", "name": "Singapore Dollar"},
    "JPY": {"symbol": "¥", "name": "Japanese Yen"},
}

PAY_PERIODS = {
    "annual": {"label": "Per year", "divisor": 1},
    "monthly": {"label": "Per month", "divisor": 12},
    "hourly": {"label": "Per hour", "divisor": 2080},
}

EXPERIENCE_LEVELS = [
    {"value": "0-1 years", "label": "Entry level (0–1 years)"},
    {"value": "2-4 years", "label": "Early career (2–4 years)"},
    {"value": "5-9 years", "label": "Mid-level (5–9 years)"},
    {"value": "10-14 years", "label": "Senior (10–14 years)"},
    {"value": "15+ years", "label": "Executive (15+ years)"},
]

SALARY_LOCATIONS = [
    {
        "group": "Remote & hybrid",
        "options": [
            {"value": "Remote (global)", "label": "Remote (global)", "currency": "USD"},
            {"value": "Hybrid / flexible", "label": "Hybrid / flexible", "currency": "USD"},
        ],
    },
    {
        "group": "United States",
        "options": [
            {"value": "San Francisco, CA", "label": "San Francisco, CA", "currency": "USD"},
            {"value": "New York, NY", "label": "New York, NY", "currency": "USD"},
            {"value": "Seattle, WA", "label": "Seattle, WA", "currency": "USD"},
            {"value": "Austin, TX", "label": "Austin, TX", "currency": "USD"},
            {"value": "Chicago, IL", "label": "Chicago, IL", "currency": "USD"},
            {"value": "Boston, MA", "label": "Boston, MA", "currency": "USD"},
            {"value": "Los Angeles, CA", "label": "Los Angeles, CA", "currency": "USD"},
            {"value": "Denver, CO", "label": "Denver, CO", "currency": "USD"},
            {"value": "Remote (US)", "label": "Remote (US)", "currency": "USD"},
        ],
    },
    {
        "group": "United Kingdom",
        "options": [
            {"value": "London, UK", "label": "London, UK", "currency": "GBP"},
            {"value": "Manchester, UK", "label": "Manchester, UK", "currency": "GBP"},
            {"value": "Remote (UK)", "label": "Remote (UK)", "currency": "GBP"},
        ],
    },
    {
        "group": "India",
        "options": [
            {"value": "Bangalore, India", "label": "Bangalore, India", "currency": "INR"},
            {"value": "Hyderabad, India", "label": "Hyderabad, India", "currency": "INR"},
            {"value": "Mumbai, India", "label": "Mumbai, India", "currency": "INR"},
            {"value": "Delhi NCR, India", "label": "Delhi NCR, India", "currency": "INR"},
            {"value": "Pune, India", "label": "Pune, India", "currency": "INR"},
            {"value": "Remote (India)", "label": "Remote (India)", "currency": "INR"},
        ],
    },
    {
        "group": "Canada",
        "options": [
            {"value": "Toronto, Canada", "label": "Toronto, Canada", "currency": "CAD"},
            {"value": "Vancouver, Canada", "label": "Vancouver, Canada", "currency": "CAD"},
            {"value": "Remote (Canada)", "label": "Remote (Canada)", "currency": "CAD"},
        ],
    },
    {
        "group": "Europe",
        "options": [
            {"value": "Berlin, Germany", "label": "Berlin, Germany", "currency": "EUR"},
            {"value": "Amsterdam, Netherlands", "label": "Amsterdam, Netherlands", "currency": "EUR"},
            {"value": "Paris, France", "label": "Paris, France", "currency": "EUR"},
            {"value": "Dublin, Ireland", "label": "Dublin, Ireland", "currency": "EUR"},
        ],
    },
    {
        "group": "Asia-Pacific",
        "options": [
            {"value": "Singapore", "label": "Singapore", "currency": "SGD"},
            {"value": "Sydney, Australia", "label": "Sydney, Australia", "currency": "AUD"},
            {"value": "Melbourne, Australia", "label": "Melbourne, Australia", "currency": "AUD"},
            {"value": "Tokyo, Japan", "label": "Tokyo, Japan", "currency": "JPY"},
        ],
    },
]

ANNUAL_WORK_HOURS = 2080


def resolve_experience_level(profile_value=None):
    if not profile_value:
        return "2-4 years"
    normalized = str(profile_value).strip().lower()
    
    import re
    match = re.search(r"(\d+)\s*year", normalized)
    if match:
        y = int(match.group(1))
        if y <= 1:
            return "0-1 years"
        elif y <= 4:
            return "2-4 years"
        elif y <= 9:
            return "5-9 years"
        elif y <= 14:
            return "10-14 years"
        else:
            return "15+ years"

    aliases = {
        "0-1": "0-1 years",
        "0-1 years": "0-1 years",
        "2-4": "2-4 years",
        "2-4 years": "2-4 years",
        "5-9": "5-9 years",
        "5-9 years": "5-9 years",
        "10+": "10-14 years",
        "10+ years": "10-14 years",
        "10-14 years": "10-14 years",
        "15+": "15+ years",
        "15+ years": "15+ years",
    }
    return aliases.get(normalized, "2-4 years")


def resolve_location_value(value):
    allowed = {
        opt["value"]
        for group in SALARY_LOCATIONS
        for opt in group["options"]
    }
    return value if value in allowed else "Remote (global)"


def parse_json_response(raw_response, fallback=None):
    fallback = fallback if fallback is not None else {}
    try:
        start = raw_response.find("{")
        end = raw_response.rfind("}") + 1
        if start == -1 or end <= start:
            return dict(fallback)
        data = json.loads(raw_response[start:end])
        if not isinstance(data, dict):
            return dict(fallback)
        return data
    except (json.JSONDecodeError, TypeError, ValueError):
        return dict(fallback)


def _as_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _as_string_list(value):
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if item is not None]


def _as_string(value, default=""):
    if value is None:
        return default
    if isinstance(value, str):
        return value
    if isinstance(value, (dict, list)):
        return json.dumps(value)
    return str(value)


def normalize_resume_analysis(data):
    return {
        "ats_score": max(0, min(100, _as_int(data.get("ats_score"), 0))),
        "extracted_skills": _as_string_list(data.get("extracted_skills")),
        "improvements": sanitize_ai_output(
            _as_string(data.get("improvements"), "Failed to parse response.")
        ),
    }


def normalize_interview_feedback(data):
    return {
        "score": max(0, min(10, _as_int(data.get("score"), 0))),
        "feedback": sanitize_ai_output(
            _as_string(data.get("feedback"), "Failed to parse feedback.")
        ),
        "ideal_answer_points": sanitize_ai_output(
            _as_string(data.get("ideal_answer_points"), "")
        ),
        "follow_up_question": sanitize_ai_output(
            _as_string(data.get("follow_up_question"), "")
        ),
    }


def _bedrock_converse(system_prompt, messages, max_tokens=1000, temperature=0.7):
    if not API_KEY:
        return AI_UNAVAILABLE_MESSAGE

    payload = {
        "messages": messages,
        "system": [{"text": system_prompt}],
        "inferenceConfig": {"maxTokens": max_tokens, "temperature": temperature},
    }
    try:
        response = requests.post(BEDROCK_URL, headers=headers, json=payload, timeout=90)
        if response.status_code != 200:
            print(f"Bedrock API Error: {response.status_code} - {response.text}")
            return AI_UNAVAILABLE_MESSAGE
        result = response.json()
        text = result["output"]["message"]["content"][0]["text"]
        return sanitize_ai_output(text)
    except Exception as e:
        print(f"Error calling Bedrock: {e}")
        return AI_UNAVAILABLE_MESSAGE


def generate_ai_response(system_prompt: str, user_message: str) -> str:
    messages = [{"role": "user", "content": [{"text": user_message}]}]
    return _bedrock_converse(system_prompt, messages)


def generate_ai_response_with_history(system_prompt: str, history, user_message: str) -> str:
    messages = []
    for item in history[-6:]:
        role = "assistant" if item.get("role") == "ai" else "user"
        content = sanitize_chat_output(item.get("content", ""))
        if content:
            if messages and messages[-1]["role"] == role:
                messages[-1]["content"][0]["text"] += f"\n\n{content}"
            else:
                messages.append({"role": role, "content": [{"text": content}]})
    
    if messages and messages[-1]["role"] == "user":
        messages[-1]["content"][0]["text"] += f"\n\n{user_message}"
    else:
        messages.append({"role": "user", "content": [{"text": user_message}]})
        
    raw = _bedrock_converse(system_prompt, messages, max_tokens=350, temperature=0.5)
    return sanitize_chat_output(raw)


def normalize_career_assessment(data):
    return {
        "career_fit_score": max(0, min(100, _as_int(data.get("career_fit_score"), 0))),
        "strengths": [sanitize_ai_output(s) for s in _as_string_list(data.get("strengths"))],
        "weaknesses": [sanitize_ai_output(s) for s in _as_string_list(data.get("weaknesses"))],
        "recommendations": [sanitize_ai_output(s) for s in _as_string_list(data.get("recommendations"))],
    }


def generate_career_assessment(profile_data: dict) -> dict:
    system_prompt = (
        "You are an expert career coach. Return ONLY JSON with keys: "
        "'strengths' (list), 'weaknesses' (list), 'recommendations' (list), "
        "'career_fit_score' (1-100 integer)."
        + CAREER_AI_RULES
    )
    raw = generate_ai_response(system_prompt, f"Assess this profile: {json.dumps(profile_data)}")
    parsed = parse_json_response(raw, {"error": "Invalid response format"})
    if "error" in parsed and len(parsed) == 1:
        return parsed
    return normalize_career_assessment(parsed)


def analyze_resume(resume_text: str, target_job: str = None) -> dict:
    system_prompt = """Analyze the resume. Return ONLY JSON with:
- "ats_score": integer 1-100
- "extracted_skills": list of strings
- "improvements": string paragraph"""
    if target_job:
        system_prompt += f"\nEvaluate the resume specifically for this target role or job description: {target_job}."
    system_prompt += CAREER_AI_RULES
    user_prompt = f"Resume:\n\n{resume_text}"
    if target_job:
        user_prompt += f"\n\nTarget Job/Description:\n{target_job}"
    raw = generate_ai_response(system_prompt, user_prompt)
    parsed = parse_json_response(
        raw, {"ats_score": 0, "extracted_skills": [], "improvements": "Failed to parse."}
    )
    return normalize_resume_analysis(parsed)


def match_job_description(resume_text: str, job_description: str) -> dict:
    system_prompt = """Compare resume to job description. Return ONLY JSON with:
- "match_score": integer 1-100
- "matching_skills": list of strings
- "missing_skills": list of strings
- "recommendations": string paragraph of tailored advice"""
    system_prompt += CAREER_AI_RULES
    raw = generate_ai_response(
        system_prompt,
        f"Resume:\n{resume_text}\n\nJob Description:\n{job_description}",
    )
    parsed = parse_json_response(
        raw,
        {"match_score": 0, "matching_skills": [], "missing_skills": [], "recommendations": ""},
    )
    parsed["match_score"] = max(0, min(100, _as_int(parsed.get("match_score"), 0)))
    parsed["matching_skills"] = _as_string_list(parsed.get("matching_skills"))
    parsed["missing_skills"] = _as_string_list(parsed.get("missing_skills"))
    parsed["recommendations"] = sanitize_ai_output(_as_string(parsed.get("recommendations"), ""))
    return parsed


def generate_cover_letter(resume_text: str, job_description: str, tone: str = "professional") -> str:
    system_prompt = (
        f"Write a compelling cover letter ({tone} tone) based on the resume and job description. "
        "Return plain text only, no JSON."
        + CAREER_AI_RULES
    )
    return generate_ai_response(
        system_prompt,
        f"Resume:\n{resume_text}\n\nJob:\n{job_description}",
    )


def generate_linkedin_summary(resume_text: str, target_role: str) -> str:
    system_prompt = (
        "Write a polished LinkedIn About section (max 260 words) from the resume. Plain text only."
        + CAREER_AI_RULES
    )
    return generate_ai_response(
        system_prompt,
        f"Target role: {target_role}\n\nResume:\n{resume_text}",
    )


def _as_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def format_salary_amount(amount, currency="USD", pay_period="annual"):
    if amount is None or amount <= 0:
        return "—"
    currency = currency if currency in SUPPORTED_CURRENCIES else "USD"
    pay_period = pay_period if pay_period in PAY_PERIODS else "annual"
    symbol = SUPPORTED_CURRENCIES[currency]["symbol"]
    value = convert_pay_period_amount(amount, pay_period)
    if pay_period == "hourly":
        return f"{symbol}{value:,.2f}/hr"
    if currency == "INR" and value >= 100000:
        lakh = value / 100000
        return f"{symbol}{lakh:.1f}L {PAY_PERIODS[pay_period]['label'].lower()}"
    if currency == "JPY":
        return f"{symbol}{int(value):,} {PAY_PERIODS[pay_period]['label'].lower()}"
    if value >= 1_000_000:
        return f"{symbol}{value / 1_000_000:.1f}M {PAY_PERIODS[pay_period]['label'].lower()}"
    if value >= 1000:
        compact = value / 1000
        compact_str = f"{compact:.0f}k" if compact == int(compact) else f"{compact:.1f}k"
        return f"{symbol}{compact_str} {PAY_PERIODS[pay_period]['label'].lower()}"
    return f"{symbol}{value:,.0f} {PAY_PERIODS[pay_period]['label'].lower()}"


def convert_pay_period_amount(amount_annual, pay_period):
    if pay_period == "monthly":
        return round(amount_annual / 12)
    if pay_period == "hourly":
        return round(amount_annual / ANNUAL_WORK_HOURS, 2)
    return round(amount_annual)


def normalize_salary_advice(data, currency="USD", pay_period="annual"):
    currency = currency if currency in SUPPORTED_CURRENCIES else "USD"
    pay_period = pay_period if pay_period in PAY_PERIODS else "annual"

    salary_low = _as_float(data.get("salary_low"), 0)
    salary_median = _as_float(data.get("salary_median"), 0)
    salary_high = _as_float(data.get("salary_high"), 0)

    if not salary_median and salary_low and salary_high:
        salary_median = (salary_low + salary_high) / 2
    if not salary_low and salary_median:
        salary_low = salary_median * 0.9
    if not salary_high and salary_median:
        salary_high = salary_median * 1.1

    talking_points = [sanitize_ai_output(p) for p in _as_string_list(data.get("talking_points"))]
    negotiation_script = sanitize_ai_output(_as_string(data.get("negotiation_script"), ""))
    market_insights = sanitize_ai_output(_as_string(data.get("market_insights"), ""))

    return {
        "currency": currency,
        "pay_period": pay_period,
        "currency_name": SUPPORTED_CURRENCIES[currency]["name"],
        "pay_period_label": PAY_PERIODS[pay_period]["label"],
        "salary_low": salary_low,
        "salary_median": salary_median,
        "salary_high": salary_high,
        "formatted_low": format_salary_amount(salary_low, currency, pay_period),
        "formatted_median": format_salary_amount(salary_median, currency, pay_period),
        "formatted_high": format_salary_amount(salary_high, currency, pay_period),
        "estimated_range": (
            f"{format_salary_amount(salary_low, currency, pay_period)} – "
            f"{format_salary_amount(salary_high, currency, pay_period)}"
        ),
        "talking_points": talking_points,
        "negotiation_script": negotiation_script,
        "market_insights": market_insights,
    }


def generate_salary_advice(
    role: str,
    location: str,
    experience: str,
    currency: str = "USD",
    pay_period: str = "annual",
) -> dict:
    currency = currency if currency in SUPPORTED_CURRENCIES else "USD"
    pay_period = pay_period if pay_period in PAY_PERIODS else "annual"
    location = resolve_location_value(location)
    experience = resolve_experience_level(experience)
    currency_name = SUPPORTED_CURRENCIES[currency]["name"]

    system_prompt = f"""Provide salary negotiation advice for the {currency_name} ({currency}) market.
Return ONLY JSON with:
- "salary_low": number (25th percentile, annual {currency})
- "salary_median": number (50th percentile)
- "salary_high": number (75th percentile)
- "talking_points": list of strings (negotiation tips)
- "negotiation_script": string paragraph (what to say when negotiating)
- "market_insights": string paragraph (local market context for the location)

All salary numbers must be realistic annual amounts in {currency}. Use local market data for the location."""
    system_prompt += CAREER_AI_RULES

    user_prompt = (
        f"Role: {role}\n"
        f"Location: {location}\n"
        f"Experience: {experience}\n"
        f"Currency: {currency}\n"
        f"Preferred display period: {pay_period}"
    )
    raw = generate_ai_response(system_prompt, user_prompt)
    parsed = parse_json_response(
        raw,
        {
            "salary_low": 0,
            "salary_median": 0,
            "salary_high": 0,
            "talking_points": [],
            "negotiation_script": "",
            "market_insights": "",
        },
    )
    result = normalize_salary_advice(parsed, currency=currency, pay_period=pay_period)
    result["location"] = location
    result["experience"] = experience
    return result


def generate_interview_question(role: str, mode: str = "behavioral") -> str:
    mode_desc = INTERVIEW_MODES.get(mode, INTERVIEW_MODES["behavioral"])
    system_prompt = (
        f"Generate ONE {mode_desc} interview question for the role. Question only, no answer."
        + CAREER_AI_RULES
    )
    return generate_ai_response(system_prompt, f"Role: {role}")


def evaluate_interview_answer(question: str, answer: str, include_follow_up: bool = True) -> dict:
    system_prompt = """Evaluate the interview answer. Return ONLY JSON with:
- "score": integer 1-10
- "feedback": string
- "ideal_answer_points": string
- "follow_up_question": string (a probing follow-up question)"""
    system_prompt += CAREER_AI_RULES
    raw = generate_ai_response(system_prompt, f"Question: {question}\nAnswer: {answer}")
    result = normalize_interview_feedback(parse_json_response(
        raw,
        {"score": 0, "feedback": "Failed.", "ideal_answer_points": "", "follow_up_question": ""},
    ))
    if not include_follow_up:
        result.pop("follow_up_question", None)
    return result


def format_star_answer(situation: str, task: str, action: str, result_text: str) -> str:
    system_prompt = (
        "Polish the STAR interview answer into a concise, compelling spoken response. Plain text only."
        + CAREER_AI_RULES
    )
    return generate_ai_response(
        system_prompt,
        f"Situation: {situation}\nTask: {task}\nAction: {action}\nResult: {result_text}",
    )
