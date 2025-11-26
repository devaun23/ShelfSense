#!/bin/bash

# ShelfSense Errors Agent - Automated Code Quality Audit
# This script runs comprehensive quality checks and generates a report

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
REPORT_DIR="$PROJECT_ROOT/audit-results"
REPORT_FILE="$REPORT_DIR/audit-$(date +%Y%m%d-%H%M%S).txt"

# Create report directory
mkdir -p "$REPORT_DIR"

echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}   ShelfSense Errors Agent - Code Quality Audit${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo ""

# Initialize report
{
    echo "ShelfSense Code Quality Audit Report"
    echo "Generated: $(date)"
    echo "========================================"
    echo ""
} > "$REPORT_FILE"

# Track overall status
ERRORS_FOUND=0

# Helper function to log results
log_section() {
    echo -e "\n${BLUE}▶ $1${NC}"
    echo -e "\n## $1" >> "$REPORT_FILE"
    echo "---" >> "$REPORT_FILE"
}

log_success() {
    echo -e "${GREEN}✓ $1${NC}"
    echo "✓ $1" >> "$REPORT_FILE"
}

log_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
    echo "⚠ $1" >> "$REPORT_FILE"
}

log_error() {
    echo -e "${RED}✗ $1${NC}"
    echo "✗ $1" >> "$REPORT_FILE"
    ERRORS_FOUND=$((ERRORS_FOUND + 1))
}

# =============================================================================
# 1. SECURITY CHECKS
# =============================================================================
log_section "Security Audit"

# Check for exposed secrets
echo "Checking for exposed secrets..."
if grep -r "sk-" --include="*.py" --include="*.ts" --include="*.tsx" "$PROJECT_ROOT" 2>/dev/null | grep -v node_modules | grep -v ".git" | grep -v venv | grep -v ".env.example" | grep -q .; then
    log_error "Found potential API keys in code!"
    grep -r "sk-" --include="*.py" --include="*.ts" --include="*.tsx" "$PROJECT_ROOT" 2>/dev/null | grep -v node_modules | grep -v ".git" | grep -v venv | grep -v ".env.example" >> "$REPORT_FILE"
else
    log_success "No exposed API keys found"
fi

# Check for debug endpoints in production
echo "Checking for debug endpoints..."
if grep -n "/debug/" "$PROJECT_ROOT/backend/app/main.py" 2>/dev/null | grep -q "@app.get"; then
    log_error "Debug endpoints found in main.py (remove for production!)"
    grep -n "/debug/" "$PROJECT_ROOT/backend/app/main.py" >> "$REPORT_FILE"
else
    log_success "No debug endpoints in production code"
fi

# Check for console.log statements
echo "Checking for console.log statements..."
CONSOLE_LOGS=$(find "$PROJECT_ROOT/frontend" -name "*.tsx" -o -name "*.ts" 2>/dev/null | xargs grep -l "console\.log" | grep -v node_modules | wc -l)
if [ "$CONSOLE_LOGS" -gt 0 ]; then
    log_warning "Found $CONSOLE_LOGS files with console.log statements"
    find "$PROJECT_ROOT/frontend" -name "*.tsx" -o -name "*.ts" 2>/dev/null | xargs grep -n "console\.log" | grep -v node_modules >> "$REPORT_FILE"
else
    log_success "No console.log statements found"
fi

# Check for .env files in git
echo "Checking for committed .env files..."
if git ls-files "$PROJECT_ROOT" | grep -q "\.env$"; then
    log_error ".env file is tracked by git! (DANGEROUS)"
else
    log_success "No .env files tracked by git"
fi

# =============================================================================
# 2. CODE QUALITY CHECKS
# =============================================================================
log_section "Code Quality"

# Frontend checks
if [ -d "$PROJECT_ROOT/frontend" ]; then
    cd "$PROJECT_ROOT/frontend"

    # Check if dependencies are installed
    if [ ! -d "node_modules" ]; then
        log_warning "Frontend dependencies not installed (run npm install)"
    else
        log_success "Frontend dependencies installed"

        # TypeScript check
        echo "Running TypeScript type check..."
        if npm run type-check 2>&1 | tee -a "$REPORT_FILE"; then
            log_success "TypeScript: No type errors"
        else
            log_error "TypeScript: Type errors found"
        fi

        # ESLint check
        echo "Running ESLint..."
        if npm run lint 2>&1 | tee -a "$REPORT_FILE"; then
            log_success "ESLint: No linting errors"
        else
            log_error "ESLint: Linting errors found"
        fi

        # Build check
        echo "Testing production build..."
        if npm run build 2>&1 | tee -a "$REPORT_FILE"; then
            log_success "Build: Successful"
        else
            log_error "Build: Failed"
        fi
    fi
fi

# Backend checks
if [ -d "$PROJECT_ROOT/backend" ]; then
    cd "$PROJECT_ROOT/backend"

    # Check if Python is available
    if command -v python3 &> /dev/null; then
        log_success "Python 3 is available"

        # Check for requirements.txt
        if [ -f "requirements.txt" ]; then
            log_success "requirements.txt found"

            # Flake8 check (if installed)
            if command -v flake8 &> /dev/null; then
                echo "Running Flake8..."
                if flake8 app/ 2>&1 | tee -a "$REPORT_FILE"; then
                    log_success "Flake8: No linting errors"
                else
                    log_warning "Flake8: Linting errors found"
                fi
            else
                log_warning "Flake8 not installed (pip install flake8)"
            fi

            # Black check (if installed)
            if command -v black &> /dev/null; then
                echo "Running Black formatter check..."
                if black --check app/ 2>&1 | tee -a "$REPORT_FILE"; then
                    log_success "Black: Code is formatted"
                else
                    log_warning "Black: Code needs formatting (run: black .)"
                fi
            else
                log_warning "Black not installed (pip install black)"
            fi
        else
            log_error "requirements.txt not found"
        fi
    else
        log_error "Python 3 not available"
    fi
fi

# =============================================================================
# 3. TESTING CHECKS
# =============================================================================
log_section "Testing"

# Frontend tests
cd "$PROJECT_ROOT/frontend"
if [ -d "tests" ] || [ -d "__tests__" ]; then
    echo "Running frontend tests..."
    if npm test 2>&1 | tee -a "$REPORT_FILE"; then
        log_success "Frontend tests: Passed"
    else
        log_error "Frontend tests: Failed"
    fi
else
    log_error "No frontend tests found (create tests/ directory)"
fi

# Backend tests
cd "$PROJECT_ROOT/backend"
if [ -d "app/tests" ] || [ -d "tests" ]; then
    echo "Running backend tests..."
    if command -v pytest &> /dev/null; then
        if pytest 2>&1 | tee -a "$REPORT_FILE"; then
            log_success "Backend tests: Passed"
        else
            log_error "Backend tests: Failed"
        fi
    else
        log_warning "Pytest not installed (pip install pytest)"
    fi
else
    log_error "No backend tests found (create app/tests/ directory)"
fi

# =============================================================================
# 4. DEPENDENCY CHECKS
# =============================================================================
log_section "Dependencies"

# NPM audit
cd "$PROJECT_ROOT/frontend"
if [ -d "node_modules" ]; then
    echo "Running npm audit..."
    if npm audit --audit-level=high 2>&1 | tee -a "$REPORT_FILE"; then
        log_success "npm audit: No high-severity vulnerabilities"
    else
        log_warning "npm audit: Vulnerabilities found (run: npm audit fix)"
    fi
else
    log_warning "Frontend dependencies not installed"
fi

# Python safety check (if installed)
cd "$PROJECT_ROOT/backend"
if command -v safety &> /dev/null; then
    echo "Running safety check..."
    if safety check 2>&1 | tee -a "$REPORT_FILE"; then
        log_success "safety: No known vulnerabilities"
    else
        log_warning "safety: Vulnerabilities found"
    fi
else
    log_warning "Safety not installed (pip install safety)"
fi

# =============================================================================
# 5. FILE ORGANIZATION CHECKS
# =============================================================================
log_section "File Organization"

cd "$PROJECT_ROOT"

# Check for .env.example
if [ -f "backend/.env.example" ]; then
    log_success ".env.example exists for backend"
else
    log_error "Missing backend/.env.example"
fi

if [ -f "frontend/.env.example" ]; then
    log_success ".env.example exists for frontend"
else
    log_warning "Missing frontend/.env.example"
fi

# Check README
if [ -f "README.md" ]; then
    log_success "README.md exists"
    # Check if README is up to date
    if grep -q "Next steps: Build frontend interface" "README.md"; then
        log_error "README.md is outdated (mentions 'Next steps: Build frontend')"
    else
        log_success "README appears up to date"
    fi
else
    log_error "README.md missing"
fi

# Check for excessive root-level markdown files
MD_COUNT=$(find . -maxdepth 1 -name "*.md" | wc -l)
if [ "$MD_COUNT" -gt 5 ]; then
    log_warning "Too many markdown files in root ($MD_COUNT files). Consider organizing into docs/ directory"
else
    log_success "Root directory is relatively clean ($MD_COUNT .md files)"
fi

# =============================================================================
# 6. GIT CHECKS
# =============================================================================
log_section "Git Repository"

# Check git status
if [ -d ".git" ]; then
    log_success "Git repository initialized"

    # Check for uncommitted changes
    if git diff-index --quiet HEAD --; then
        log_success "Working directory is clean"
    else
        log_warning "Uncommitted changes present"
        git status --short >> "$REPORT_FILE"
    fi

    # Check branch
    CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
    echo "Current branch: $CURRENT_BRANCH" >> "$REPORT_FILE"
    log_success "On branch: $CURRENT_BRANCH"
else
    log_error "Not a git repository"
fi

# =============================================================================
# 7. DEPLOYMENT CHECKS
# =============================================================================
log_section "Deployment Configuration"

# Check for Railway config
if [ -f "railway.json" ] || [ -f "railway.toml" ]; then
    log_success "Railway configuration found"
else
    log_warning "No Railway configuration file"
fi

# Check for Netlify config
if [ -f "netlify.toml" ] || [ -f "frontend/netlify.toml" ]; then
    log_success "Netlify configuration found"
else
    log_warning "No Netlify configuration file"
fi

# Check for CI/CD
if [ -d ".github/workflows" ]; then
    WORKFLOW_COUNT=$(find .github/workflows -name "*.yml" | wc -l)
    log_success "GitHub Actions configured ($WORKFLOW_COUNT workflows)"
else
    log_error "No GitHub Actions workflows found"
fi

# =============================================================================
# SUMMARY
# =============================================================================
echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}   Audit Summary${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo ""

{
    echo ""
    echo "========================================"
    echo "Summary"
    echo "========================================"
    echo "Total errors found: $ERRORS_FOUND"
    echo "Report saved to: $REPORT_FILE"
    echo ""
} >> "$REPORT_FILE"

if [ $ERRORS_FOUND -eq 0 ]; then
    echo -e "${GREEN}✓ Audit completed successfully! No critical errors found.${NC}"
    echo "✓ Audit completed successfully!" >> "$REPORT_FILE"
    exit 0
else
    echo -e "${RED}✗ Audit found $ERRORS_FOUND error(s). Please review the report.${NC}"
    echo "✗ Audit found $ERRORS_FOUND error(s)" >> "$REPORT_FILE"
    exit 1
fi

echo ""
echo -e "${BLUE}Full report saved to: $REPORT_FILE${NC}"
echo ""
