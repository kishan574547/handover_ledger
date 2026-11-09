import re
from typing import Tuple

# Regex definitions for sensitive data patterns
PATTERNS = [
    # 1. Private keys
    (re.compile(r"-----BEGIN [A-Z\s]+PRIVATE KEY-----[\s\S]*?-----END [A-Z\s]+PRIVATE KEY-----", re.MULTILINE), "[MASKED:private_key]"),
    
    # 2. Known API Keys (Google AIza, GitHub ghp/gho/etc, OpenAI sk-)
    (re.compile(r"\bAIza[0-9A-Za-z_\-]{30,}\b"), "[MASKED:api_key]"),
    (re.compile(r"\b(ghp|gho|ghu|ghs|ghr)_[0-9A-Za-z]{30,}\b"), "[MASKED:api_key]"),
    (re.compile(r"\bsk-[0-9A-Za-z_\-]{20,}\b"), "[MASKED:api_key]"),
    
    # 3. Explicit credential assignments (password, passwd, token, api_token, secret)
    (
        re.compile(r"""(?i)\b(password|passwd|token|api_token|secret)\s*([:=])\s*(['"][^'"]+['"]|[^\s,;]+)"""),
        lambda m: f"{m.group(1)}{m.group(2)}[MASKED:password]" if "pass" in m.group(1).lower() else f"{m.group(1)}{m.group(2)}[MASKED:token]"
    ),

    # 4. Email addresses
    (re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"), "[MASKED:email]"),

    # 5. Indian phone numbers (10 digits starting with 6-9, with optional +91 and spaces/dashes)
    (re.compile(r"(?:\+91[\s\-]?)?[6-9]\d{4}[\s\-]?\d{5}\b"), "[MASKED:phone]"),

    # 6. International phone numbers (e.g. +1 (555) 123-4567 or +44 20 7946 0919)
    (re.compile(r"\+(?:1|44|33|49|81|86)[\s\-]?(?:\(\d{1,4}\)|\d{1,4})[\s\-]?\d{3,4}[\s\-]?\d{3,4}\b"), "[MASKED:phone]"),
]

def mask_sensitive_text(text: str) -> Tuple[str, int]:
    """
    Masks API keys, passwords, tokens, private keys, emails, and phone numbers in raw text.
    Returns the sanitized text and the total count of sensitive tokens masked.
    """
    if not text:
        return text, 0

    masked_text = text
    total_masked = 0

    for pattern, replacement in PATTERNS:
        matches = list(pattern.finditer(masked_text))
        if matches:
            total_masked += len(matches)
            if callable(replacement):
                masked_text = pattern.sub(replacement, masked_text)
            else:
                masked_text = pattern.sub(replacement, masked_text)

    return masked_text, total_masked
