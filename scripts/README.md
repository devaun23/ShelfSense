# ShelfSense Scripts

Automation scripts for maintaining code quality and project health.

## 📋 Available Scripts

### `errors-agent-audit.sh`

Comprehensive code quality audit that checks:
- Security issues (exposed secrets, debug endpoints)
- Code quality (TypeScript, ESLint, Python formatting)
- Testing (runs all test suites)
- Dependencies (vulnerabilities)
- File organization
- Git repository health
- Deployment configuration

**Usage:**
```bash
./scripts/errors-agent-audit.sh
```

**Output:**
- Colored terminal output showing pass/fail for each check
- Detailed report saved to `audit-results/audit-TIMESTAMP.txt`
- Exit code 0 if successful, 1 if errors found

**When to run:**
- Before committing major changes
- Before deploying to production
- Weekly as part of maintenance
- When onboarding new developers

---

## 🚀 Planned Scripts

### `errors-agent-fix.sh` (Coming Soon)
Auto-fixes common issues:
- Run code formatters (Black, Prettier)
- Fix ESLint auto-fixable issues
- Update dependencies (minor versions)
- Organize imports

### `errors-agent-monitor.sh` (Coming Soon)
Production monitoring:
- Check API health endpoints
- Monitor error rates (Sentry)
- Check database size
- Monitor OpenAI quota
- Send alerts if thresholds exceeded

### `setup-dev.sh` (Coming Soon)
One-command development setup:
- Install all dependencies
- Set up pre-commit hooks
- Create .env from .env.example
- Run database migrations
- Verify setup with test run

---

## 📦 Requirements

### For Full Audit Functionality:

**Frontend:**
- Node.js 18+
- npm dependencies installed (`npm install`)

**Backend:**
- Python 3.11+
- pip packages: `flake8`, `black`, `pytest`, `safety`

**Git:**
- Git installed and repository initialized

---

## 🔧 Customization

Edit `errors-agent-audit.sh` to:
- Add custom checks
- Adjust error thresholds
- Configure output format
- Add notifications (Slack, email)

---

## 📊 Interpreting Results

### Exit Codes
- `0` - All checks passed
- `1` - Errors found (review report)

### Output Colors
- 🟢 **Green (✓)** - Check passed
- 🟡 **Yellow (⚠)** - Warning (non-critical)
- 🔴 **Red (✗)** - Error (needs fixing)

### Report Location
All reports saved to `audit-results/` with timestamp:
```
audit-results/
├── audit-20251126-143022.txt
├── audit-20251127-090515.txt
└── audit-20251127-165403.txt
```

---

## 🤖 Integration with CI/CD

Add to GitHub Actions workflow:

```yaml
# .github/workflows/quality.yml
name: Code Quality Audit

on: [push, pull_request]

jobs:
  audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run Errors Agent Audit
        run: ./scripts/errors-agent-audit.sh
      - name: Upload Report
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: audit-report
          path: audit-results/
```

---

## 📝 Adding New Checks

To add a new check to the audit script:

```bash
# 1. Add a new section
log_section "Your Check Category"

# 2. Run your check
echo "Checking for XYZ..."
if your_check_command; then
    log_success "Check passed"
else
    log_error "Check failed"
fi

# 3. Optionally add details to report
echo "Additional details" >> "$REPORT_FILE"
```

---

## 🆘 Troubleshooting

### "Permission denied" error
```bash
chmod +x scripts/errors-agent-audit.sh
```

### Script fails immediately
- Check that you're in the project root
- Verify dependencies are installed
- Run with `-x` flag for debugging:
  ```bash
  bash -x scripts/errors-agent-audit.sh
  ```

### False positives
- Review `audit-results/` report for details
- Adjust thresholds in script if needed
- Add exceptions for legitimate use cases

---

**Last Updated:** 2025-11-26
