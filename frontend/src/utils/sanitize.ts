/**
 * Secret Sanitizer for UI error components, toasts, and API client messages.
 * Automatically redacts secret tokens, API keys, and connection credentials
 * by pattern before display.
 */

interface SecretRule {
  pattern: RegExp;
  replacement: string | ((substring: string, ...args: any[]) => string);
}

const SECRET_RULES: SecretRule[] = [
  // PostgreSQL URL: keep user and host, remove password
  {
    pattern: /(postgres(?:ql)?:\/\/[^\s:@/]*):([^\s@/]+)@([^\s/]+)/gi,
    replacement: '$1:****@$3',
  },
  // Google AI / Maps API keys
  {
    pattern: /AIza[0-9A-Za-z_\-]{35}/g,
    replacement: '[REDACTED_KEY]',
  },
  // GitHub tokens (classic and fine-grained)
  {
    pattern: /ghp_[0-9A-Za-z]{20,}/g,
    replacement: '[REDACTED_GH_TOKEN]',
  },
  {
    pattern: /github_pat_[0-9A-Za-z_]{20,}/g,
    replacement: '[REDACTED_GH_TOKEN]',
  },
  // OpenAI / Anthropic / sk- API keys
  {
    pattern: /sk-[a-zA-Z0-9_\-]{20,}/g,
    replacement: '[REDACTED_SK_KEY]',
  },
  // Parameter style assignments
  {
    pattern: /(key|api_key|token|secret|password)=['"]?([a-zA-Z0-9_\-]{16,})['"]?/gi,
    replacement: '$1=[REDACTED]',
  },
  // Authorization Bearer tokens
  {
    pattern: /Bearer\s+([a-zA-Z0-9_\-\.]{20,})/gi,
    replacement: 'Bearer [REDACTED]',
  },
];

/**
 * Strips secret tokens and credentials from any text rendered in the UI.
 */
export function sanitizeSecrets(text: string | null | undefined): string {
  if (!text) return '';
  let sanitized = String(text);
  for (const rule of SECRET_RULES) {
    sanitized = sanitized.replace(rule.pattern, rule.replacement as any);
  }
  return sanitized;
}

