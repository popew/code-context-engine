# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability, please report it responsibly.

**Email:** fazle.elahee@gmail.com

Please include:
- Description of the vulnerability
- Steps to reproduce
- Potential impact

We will acknowledge receipt within 48 hours and aim to release a fix within 7 days for critical issues.

## How CCE Protects Your Code

### Your code never leaves your machine

CCE runs entirely locally. No cloud APIs, no telemetry, no phone-home. Embeddings are generated on-device via ONNX Runtime.

### Secret detection

These file patterns are never indexed:
`.env`, `.env.*`, `*.pem`, `*.key`, `*.p12`, `*.pfx`, `credentials.json`, `secrets.yml`, `id_rsa`, `id_ed25519`

### Content redaction

Indexed content is scanned and redacted for:
- AWS access keys and secret keys
- GitHub personal access tokens
- Slack tokens
- Stripe API keys
- JWTs
- Generic API keys and passwords in assignment patterns

Redaction is enabled by default (`indexer_redact_secrets: true` in config).

### PII scrubbing

Memory writes (`record_decision`, `record_code_area`) are scrubbed for:
- Email addresses
- IP addresses
- Credit card numbers (Luhn-validated)
- Social Security Numbers
- Phone numbers

Enabled by default (`memory_redact_pii: true` in config).

### Path traversal protection

All MCP tool file path arguments are validated to stay within the project directory. Attempts to access files outside the project root are rejected.

### HTTP mode security

When running `cce serve` bound to a non-loopback address, bearer token authentication is required. Tokens are compared using `hmac.compare_digest` to prevent timing attacks. Request body size is capped at 10 MB.

## Supported Versions

| Version | Supported |
|---------|-----------|
| 0.4.x   | Yes       |
| < 0.4   | No        |
