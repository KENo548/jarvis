---
name: jarvis-security
description: Security analysis, secret detection, vulnerability scanning, and secure coding practices.
license: MIT
metadata:
  domain: security
  complexity: high
---

# Security

## What I do

- Secret detection in codebases
- Vulnerability scanning
- Secure coding review
- OWASP Top 10 analysis
- Dependency audit

## When to use me

Use this skill for security audits, secret detection, vulnerability scanning, or secure code review.

## Patterns

### Secret Detection
```bash
# Scan for secrets
grep -rn "password\|secret\|api_key\|token" --include="*.{ts,tsx,js,jsx,json}" .
```

### Dependency Audit
```bash
npm audit
npm audit fix
```

### OWASP Top 10 Check
1. Injection (SQL, NoSQL, Command)
2. Broken Authentication
3. Sensitive Data Exposure
4. XML External Entities
5. Broken Access Control
6. Security Misconfiguration
7. Cross-Site Scripting (XSS)
8. Insecure Deserialization
9. Using Components with Known Vulnerabilities
10. Insufficient Logging

## Anti-patterns

- Don't commit secrets to Git
- Don't skip input validation
- Don't use weak passwords or tokens
- Don't ignore security advisories

---
*Source: Extracted from wshobson security-scanning, security-compliance agents*
