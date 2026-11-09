import os
import re
import logging
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import urlsplit

try:
    from backend.config import settings
except ImportError:
    from config import settings

logger = logging.getLogger(__name__)

# Pattern for postgresql:// and postgres:// URLs: keep user & host, redact password
# Matches postgresql://[user]:[password]@[host][:port][/path]
POSTGRES_URL_PATTERN = re.compile(
    r"(postgres(?:ql)?:\/\/[^\s:@/]*):([^\s@/]+)@([^\s/]+)",
    re.IGNORECASE
)

# Regex patterns to detect and scrub API keys and sensitive tokens
SECRET_PATTERNS = [
    # Google AI / Maps / Cloud API keys (AIza followed by 35 valid chars)
    re.compile(r"AIza[0-9A-Za-z_\-]{35}"),
    # GitHub personal access tokens: classic ghp_ and fine-grained github_pat_
    re.compile(r"ghp_[0-9A-Za-z]{20,}"),
    re.compile(r"github_pat_[0-9A-Za-z_]{20,}"),
    # OpenAI / Anthropic / standard sk- keys
    re.compile(r"sk-[a-zA-Z0-9_\-]{20,}"),
    # Generic key/secret query parameters or assignment strings
    re.compile(r"(key|api_key|token|secret|password)=['\"]?([a-zA-Z0-9_\-]{16,})['\"]?", re.IGNORECASE),
    # Bearer tokens in headers or logs
    re.compile(r"Bearer\s+([a-zA-Z0-9_\-\.]{20,})", re.IGNORECASE),
]

def get_configured_secret_values() -> List[str]:
    """
    Dynamically extracts all non-empty secret values loaded from .env/settings
    and the operating environment.
    Returns them sorted by length in descending order to avoid substring collision.
    """
    secrets: Set[str] = set()

    # 1. Direct configuration attributes
    named_attrs = [
        "GEMINI_API_KEY",
        "GITHUB_TOKEN",
        "SUPABASE_SERVICE_ROLE_KEY",
        "SUPABASE_PUBLISHABLE_KEY",
    ]
    for attr in named_attrs:
        val = getattr(settings, attr, None)
        if val and isinstance(val, str) and len(val.strip()) >= 4:
            secrets.add(val.strip())

    # 2. Database password from DATABASE_URL
    db_url = getattr(settings, "DATABASE_URL", None)
    if db_url and isinstance(db_url, str):
        try:
            parsed = urlsplit(db_url)
            if parsed.password and len(parsed.password) >= 4:
                secrets.add(parsed.password)
        except Exception:
            pass

    # 3. Dynamic scan of environment for Supabase keys, passwords, and tokens
    for env_k, env_v in os.environ.items():
        k_upper = env_k.upper()
        if (
            k_upper.startswith("SUPABASE_")
            or any(term in k_upper for term in ["API_KEY", "SECRET", "TOKEN", "PASSWORD", "PASSWD"])
        ):
            if env_v and isinstance(env_v, str) and len(env_v.strip()) >= 4:
                # Omit generic harmless system variables
                if k_upper not in ("APP_ENV", "PATH", "PYTHONPATH", "HOMEPATH", "USERNAME", "COMPUTERNAME"):
                    secrets.add(env_v.strip())

    return sorted(secrets, key=len, reverse=True)

def sanitize_text(text: Optional[str]) -> str:
    """
    Sanitizes secrets from a text string using both value-based redaction
    and pattern-based redaction.
    - Preserves postgres URL host while removing password.
    - Redacts exact values loaded from backend/.env.
    - Redacts token patterns (AIza..., ghp_..., github_pat_..., sk-...).
    """
    if text is None:
        return ""
    if not isinstance(text, str):
        text = str(text)

    # 1. PostgreSQL URL pattern: keep host, remove password
    sanitized = POSTGRES_URL_PATTERN.sub(r"\1:****@\3", text)

    # 2. Redact known secret values by value (ordered longest first)
    for secret_val in get_configured_secret_values():
        if secret_val in sanitized:
            sanitized = sanitized.replace(secret_val, "[REDACTED_SECRET]")

    # 3. Redact secret patterns
    for pat in SECRET_PATTERNS:
        sanitized = pat.sub("[REDACTED_KEY]", sanitized)

    return sanitized

def sanitize_obj(obj: Any) -> Any:
    """
    Recursively traverses dicts, lists, tuples, sets, strings, and Exception objects
    to sanitize all text fields.
    """
    if isinstance(obj, str):
        return sanitize_text(obj)
    elif isinstance(obj, dict):
        return {k: sanitize_obj(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [sanitize_obj(item) for item in obj]
    elif isinstance(obj, tuple):
        return tuple(sanitize_obj(item) for item in obj)
    elif isinstance(obj, set):
        return {sanitize_obj(item) for item in obj}
    elif isinstance(obj, Exception):
        return sanitize_text(str(obj))
    return obj

class SecretSanitizingFilter(logging.Filter):
    """
    Logging filter that sanitizes record.msg, record.args, and tracebacks in-flight.
    """
    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = sanitize_text(record.msg)
        if record.args:
            if isinstance(record.args, dict):
                record.args = {
                    k: sanitize_text(v) if isinstance(v, str) else v
                    for k, v in record.args.items()
                }
            elif isinstance(record.args, (tuple, list)):
                record.args = tuple(
                    sanitize_text(a) if isinstance(a, str) else a
                    for a in record.args
                )
        if hasattr(record, "exc_text") and record.exc_text:
            record.exc_text = sanitize_text(record.exc_text)
        return True

class SecretSanitizingFormatterWrapper:
    """
    Wraps any existing formatter (including Uvicorn's DefaultFormatter)
    so that custom attributes like %(levelprefix)s are preserved,
    while the final formatted string is strictly scrubbed of secrets.
    """
    def __init__(self, original_formatter: Any):
        self._orig = original_formatter

    def format(self, record: logging.LogRecord) -> str:
        res = self._orig.format(record)
        return sanitize_text(res)

    def formatException(self, ei: Any) -> str:
        if hasattr(self._orig, "formatException"):
            return sanitize_text(self._orig.formatException(ei))
        return ""

    def __getattr__(self, name: str) -> Any:
        return getattr(self._orig, name)

class SecretSanitizingFormatter(logging.Formatter):
    """
    Logging formatter that ensures the full formatted message and traceback
    is cleansed before output.
    """
    def format(self, record: logging.LogRecord) -> str:
        s = super().format(record)
        return sanitize_text(s)

def install_logging_sanitizer():
    """
    Installs the secret filter and formatter wrapper across root logger, handlers,
    and application/uvicorn loggers.
    """
    sanitizing_filter = SecretSanitizingFilter()
    root = logging.getLogger()
    root.addFilter(sanitizing_filter)

    for handler in root.handlers:
        handler.addFilter(sanitizing_filter)
        if handler.formatter and not isinstance(handler.formatter, SecretSanitizingFormatterWrapper):
            handler.formatter = SecretSanitizingFormatterWrapper(handler.formatter)

    for logger_name in ["handoverledger", "uvicorn", "uvicorn.error", "uvicorn.access", "fastapi"]:
        l = logging.getLogger(logger_name)
        l.addFilter(sanitizing_filter)
        for h in l.handlers:
            h.addFilter(sanitizing_filter)
            if h.formatter and not isinstance(h.formatter, SecretSanitizingFormatterWrapper):
                h.formatter = SecretSanitizingFormatterWrapper(h.formatter)
