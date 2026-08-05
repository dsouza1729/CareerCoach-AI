import re
import unicodedata

MAX_MESSAGE_LENGTH = 2000
MAX_ROLE_LENGTH = 200
MAX_SKILLS_LENGTH = 1000
MAX_ANSWER_LENGTH = 5000

BLOCKED_KEYWORDS = [
    "hack", "exploit", "illegal", "weapon", "drug", "bomb",
    "suicide", "self-harm", "violence", "porn", "nsfw",
    "write code", "write a script", "sql injection",
    "ignore previous instructions", "ignore your instructions",
    "forget your rules", "act as", "pretend you are",
    "jailbreak", "dan mode", "politics", "sports", "recipe",
    "cooking", "movie", "video game", "entertainment", "religion",
    "health", "diet", "dating", "relationship"
]

OUTPUT_BLOCKLIST = ["<script", "javascript:", "DROP TABLE", "SELECT * FROM"]

BLOCKED_TOPIC_RESPONSE = (
    "I am your Career Coach and I can only help with career-related topics like "
    "resume advice, interview prep, skill development, and job searching. "
    "Please ask me something career-related."
)

CAREER_COACH_SYSTEM_PROMPT = """You are Coach, a concise AI career mentor.

RULES:
- Reply in plain text only. No markdown, no bold, no asterisks, no hashtags, no bullet symbols, no emojis, no special characters.
- Use short sentences and simple numbered lines like "1. ..." when listing steps.
- Keep replies under 120 words unless the user asks for detail.
- Be direct and actionable. Skip filler and long introductions.
- Allowed topics: resumes, interviews, careers, skills, job search, salary, networking, workplace growth.

If the user asks about ANYTHING outside of professional career development (e.g., cooking, politics, sports, entertainment, personal relationships), you MUST politely decline in one short sentence."""

CAREER_AI_RULES = """
STRICT RULES:
1. ONLY discuss career, job search, hiring, and professional development topics.
2. REJECT any prompts asking about politics, sports, entertainment, personal relationships, or general knowledge.
3. NEVER generate code, scripts, or technical implementations.
4. NEVER role-play as a different AI or persona.
5. NEVER provide medical, legal, or financial investment advice."""


def build_coach_system_prompt(profile=None):
    prompt = CAREER_COACH_SYSTEM_PROMPT
    if not profile:
        return prompt
    tone = profile.get("tone") or "balanced"
    if tone == "formal":
        prompt += "\nUse a formal, professional tone."
    elif tone == "casual":
        prompt += "\nUse a warm, casual, conversational tone."
    else:
        prompt += "\nUse a balanced, supportive professional tone."
    if profile.get("industry"):
        prompt += f"\nThe user is focused on the {profile['industry']} industry."
    if profile.get("target_role"):
        prompt += f"\nTheir target role is: {profile['target_role']}."
    if profile.get("full_name"):
        prompt += f"\nAddress the user as {profile['full_name']} when appropriate."
    return prompt


def contains_blocked_keyword(text):
    message_lower = (text or "").lower()
    return any(keyword in message_lower for keyword in BLOCKED_KEYWORDS)


def validate_message(text, max_length=MAX_MESSAGE_LENGTH):
    message = (text or "").strip()
    if not message:
        return False, "Please enter a valid message."
    if len(message) > max_length:
        return False, f"Please keep your message under {max_length} characters."
    if contains_blocked_keyword(message):
        return False, BLOCKED_TOPIC_RESPONSE
    return True, message


def sanitize_ai_output(text):
    if not text:
        return text
    for term in OUTPUT_BLOCKLIST:
        if term.lower() in text.lower():
            return "I can only provide career coaching advice. How can I help with your career today?"
    return text


_EMOJI_RE = re.compile(
    "["
    "\U0001F300-\U0001FAFF"
    "\U00002600-\U000027BF"
    "\U0001F600-\U0001F64F"
    "\U0001F680-\U0001F6FF"
    "\U00002700-\U000027BF"
    "\U0000FE00-\U0000FEFF"
    "]+",
    flags=re.UNICODE,
)

# Plain ASCII letters, numbers, basic punctuation, newlines only.
_DISALLOWED_CHAR_RE = re.compile(r"[^A-Za-z0-9\s.,!?;:'\"()\-$/%\n]")


def _strip_markdown(text):
    text = re.sub(r"```[\s\S]*?```", " ", text)
    text = re.sub(r"`([^`]*)`", r"\1", text)
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"__(.+?)__", r"\1", text)
    text = re.sub(r"\*(.+?)\*", r"\1", text)
    text = re.sub(r"(?<!\w)_(.+?)_(?!\w)", r"\1", text)
    text = re.sub(r"^#+\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*[-*•>\u2022\u2013\u2014]\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"[*#`_>|\\[\]{}~^=+&@]", " ", text)
    return text


def sanitize_chat_output(text):
    """Return plain ASCII chat text with markdown, emoji, and symbols removed."""
    if not text:
        return text
    text = sanitize_ai_output(text)
    text = _strip_markdown(text)
    text = _EMOJI_RE.sub(" ", text)
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = _DISALLOWED_CHAR_RE.sub("", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()

def sanitize_ai_dict(data, string_keys):
    if not isinstance(data, dict):
        return data
    sanitized = dict(data)
    for key in string_keys:
        if key in sanitized and isinstance(sanitized[key], str):
            sanitized[key] = sanitize_ai_output(sanitized[key])
    return sanitized
