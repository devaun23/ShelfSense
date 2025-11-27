# ShelfSense Scripts

Automation scripts for maintaining code quality and project health.

---

## 🤖 Claude Slash Commands

Custom slash commands for Claude Code located in `.claude/commands/`.

### `/issues [description]`
Create well-structured GitHub issues for feature requests, bug reports, or improvements.

**Usage:**
```bash
/issues Add dark mode toggle to settings page
/issues Fix bug where score prediction shows NaN
/issues Refactor the analytics dashboard for better performance
```

### `/project:issues [description]`
Same as `/issues` but with ShelfSense-specific labels (agent:content, agent:adaptive, frontend, backend, etc.).

**Usage:**
```bash
/project:issues Add spaced repetition stats to analytics dashboard
```

### `/entrepreneur`
Activate the Entrepreneur Agent to research competitors, analyze market opportunities, and propose strategic features.

**Usage:**
```bash
/entrepreneur
```

The agent will:
1. Analyze current ShelfSense features
2. Research competitor offerings (UWorld, AMBOSS, Anki)
3. Identify gaps and opportunities
4. Propose 1-3 prioritized features with research backing

---

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

## 🧠 Fine-Tuning Scripts (backend/scripts/)

Scripts for training and managing OpenAI fine-tuned models for USMLE question generation.

### `prepare_fine_tuning_data.py`
Extracts questions from the database and converts them to OpenAI's JSONL fine-tuning format.

**Usage:**
```bash
cd backend
python scripts/prepare_fine_tuning_data.py                    # Export all questions
python scripts/prepare_fine_tuning_data.py --validate         # Validate before export
python scripts/prepare_fine_tuning_data.py --limit 500        # Limit for budget control
python scripts/prepare_fine_tuning_data.py --min-quality      # Only high-quality explanations
```

**Output:**
- `training_data.jsonl` (90% of questions)
- `validation_data.jsonl` (10% of questions)

---

### `upload_and_train.py`
Uploads training data to OpenAI and manages the fine-tuning workflow.

**Usage:**
```bash
cd backend
python scripts/upload_and_train.py                  # Upload and start training
python scripts/upload_and_train.py --status <job>   # Check job status
python scripts/upload_and_train.py --monitor <job>  # Monitor until completion
python scripts/upload_and_train.py --list           # List all fine-tuning jobs
```

**Requirements:**
- `OPENAI_API_KEY` environment variable set
- `training_data.jsonl` in backend directory

---

### `validate_fine_tuned_model.py`
Tests the fine-tuned model quality by generating sample questions and checking compliance.

**Usage:**
```bash
cd backend
python scripts/validate_fine_tuned_model.py                    # Validate saved model
python scripts/validate_fine_tuned_model.py --model <model_id> # Validate specific model
python scripts/validate_fine_tuned_model.py --count 20         # Generate 20 test questions
python scripts/validate_fine_tuned_model.py --output results.json
```

**Checks:**
- Structure compliance (all required fields)
- Arrow notation (→) in reasoning
- Explicit thresholds with units
- Enhanced fields (quick_answer, deep_dive, memory_hooks)

---

### `upgrade_explanations.py`
Batch upgrades existing question explanations to meet the full ShelfSense quality framework.

**Usage:**
```bash
cd backend
python scripts/upgrade_explanations.py --dry-run   # Preview changes without saving
python scripts/upgrade_explanations.py --batch 50  # Process 50 questions
python scripts/upgrade_explanations.py --all       # Process all questions
python scripts/upgrade_explanations.py --model gpt-4o  # Specify model
```

**Adds:**
- `quick_answer` (30-word summary)
- `deep_dive` (pathophysiology, differential, pearls)
- `memory_hooks` (analogy, mnemonic, clinical story)
- `step_by_step` (numbered decision steps)
- `common_traps` (what students get wrong)
- Arrow notation (→) in reasoning

---

**Last Updated:** 2025-11-26
