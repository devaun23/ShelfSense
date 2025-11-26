---
description: Create well-structured GitHub issues for feature requests, bug reports, or improvements
---

# GitHub Issue Creator

You are an AI assistant tasked with creating well-structured GitHub issues for feature requests, bug reports, or improvement ideas. Your goal is to turn the provided feature description into a comprehensive GitHub issue that follows best practices and the target repository's conventions.

## Inputs

- **Feature description**: $ARGUMENTS (or ask for it if not provided)
- **Repository URL**: Use the current repository (ShelfSense at https://github.com/anthropics/shelfsense) or ask for a different one

## Process

### Step 1: Research the Repository
- Visit the provided repo_url
- Review the repository structure, existing issues, and documentation
- Look for `CONTRIBUTING.md`, `ISSUE_TEMPLATE.md`, or similar guidelines for submitting issues
- Identify coding style, naming conventions, or special requirements for issues

### Step 2: Research Best Practices
- Look up current best practices for writing GitHub issues (clarity, completeness, actionability)
- Review examples of high-quality issues in major open-source projects

### Step 3: Present a Plan
Based on your research, create a plan for drafting the GitHub issue. Present this plan inside `<plan>` tags including:
- Proposed issue structure
- Recommended labels and milestones
- How repository-specific conventions will be incorporated

**Wait for user approval before proceeding to Step 4.**

### Step 4: Create the GitHub Issue
After the plan is approved, draft the complete issue including:
- A clear and concise title
- A detailed description
- Acceptance criteria
- Additional context, diagrams, or relevant resources
- Apply appropriate GitHub labels such as `bug` or `enhancement` (based on the nature of the item)
- Follow any project-specific conventions identified earlier

### Step 5: Final Output
Present ONLY the complete GitHub issue inside `<github_issue>` tags:
- No explanation, no extra commentary — just the issue content ready to paste directly into GitHub
- Format it so it can be used directly with the GitHub CLI command: `gh issue create`
- Ensure readability and best-practice structure

## Output Format

```
<github_issue>
---
title: [Clear, concise title]
labels: [comma-separated labels]
assignees: [optional]
milestone: [optional]
---

## Description
[Detailed description of the feature/bug/improvement]

## Problem Statement
[What problem does this solve? Why is this needed?]

## Proposed Solution
[How should this be implemented? Technical approach if applicable]

## Acceptance Criteria
- [ ] Criterion 1
- [ ] Criterion 2
- [ ] Criterion 3

## Technical Notes
[Any technical considerations, affected files, or implementation hints]

## Additional Context
[Screenshots, diagrams, links, related issues, or other relevant information]
</github_issue>
```

## GitHub CLI Usage

After creating the issue, use GitHub CLI to submit:

```bash
# Basic usage
gh issue create --title "Issue Title" --body "Issue body" --label "enhancement"

# With file
gh issue create --title "Issue Title" --body-file issue.md --label "enhancement,priority:high"
```

## Labels Reference

Common labels for ShelfSense:
- `bug` - Something isn't working
- `enhancement` - New feature or request
- `documentation` - Improvements or additions to documentation
- `good first issue` - Good for newcomers
- `help wanted` - Extra attention is needed
- `priority:high` - High priority items
- `priority:low` - Low priority items
- `agent:content` - Related to Content Management Agent
- `agent:adaptive` - Related to Adaptive Learning Engine
- `agent:analytics` - Related to Analytics Agent
- `frontend` - Frontend/UI changes
- `backend` - Backend/API changes
- `database` - Database schema or query changes

---

**Now, please provide the feature description or bug report you'd like me to turn into a GitHub issue.**
