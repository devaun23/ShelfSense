# GitHub Issue Template for Claude Code

## Issue: ShelfSense Development Guidelines #1

**Pin this issue** - Claude Code should ALWAYS reference this before coding.

---

## 🎯 Core Principles to ALWAYS Follow

### Philosophy
- **Occam's Razor**: Choose the simplest solution that works
- **First Principles**: Build from fundamental learning science
- **Zero to One**: Create new value, don't copy existing solutions
- **99th Percentile Goal**: Every feature must contribute to mastery

### Technical Constraints
- **Minimalist Black UI**: Like ChatGPT - no decorations
- **Adaptive First**: Every question must serve a purpose
- **3-Second Feedback**: Immediate, actionable insights only
- **Behavioral Tracking**: Track everything, show nothing

---

## 📋 Development Workflow

### 1. PLAN
```bash
# Start every session with:
1. gh issue view 1  # Read these guidelines
2. Search scratchpads for: /shelfsense/*.md
3. Review project documentation: SHELFSENSE_COMPLETE_PROJECT.md
4. Check existing code structure
5. Create ultrathink plan in scratchpad: /scratchpads/shelfsense_[feature]_plan.md
```

### 2. ANALYZE
Before writing ANY code, ask:
- Does this help students reach 99th percentile faster?
- Is this the simplest solution? (Occam's Razor)
- Does this track behavioral data we need?
- Will this adapt to individual weaknesses?

### 3. CREATE CODE
```bash
# Create feature branch
git checkout -b feature/[issue-name]

# Follow these patterns:
- Database: Always track behavioral data (time, confidence, cross-outs)
- Frontend: Black background, white text, minimal design
- Algorithm: Adaptive selection based on weakest patterns
- Questions: NBME format with complete vignettes

# Commit structure:
git commit -m "feat: [component] - [what it does]"
git commit -m "fix: [component] - [what was fixed]"
git commit -m "test: [component] - [test coverage added]"
```

### 4. CODE STANDARDS

#### Python (Backend)
```python
# Every function must:
- Have docstring explaining purpose
- Track user behavior if applicable
- Return data for pattern analysis
- Use type hints

def analyze_answer(data: dict) -> dict:
    """
    Analyze user answer for reasoning patterns.
    Tracks: time, confidence, cross-outs, changes
    Returns: pattern identified, feedback
    """
    # Implementation
```

#### JavaScript (Frontend)
```javascript
// Every interaction must:
- Be tracked in behaviorData object
- Have minimal visual feedback
- Submit data for pattern analysis
- Use const/let, never var

const trackBehavior = (action, data) => {
    // Always timestamp
    // Always associate with question
    // Always prepare for backend analysis
};
```

#### Database
```sql
-- Every table must have:
- user_id for tracking
- timestamp for temporal analysis
- behavioral data columns
- pattern association

-- Data retention: mark inactive, don't delete
```

### 5. TEST
```bash
# Test requirements:
1. Behavioral tracking works (cross-outs, time, confidence)
2. Adaptive algorithm selects correct difficulty
3. Pattern detection identifies errors correctly
4. UI is minimal and black
5. Feedback appears in <3 seconds

# Run tests:
python -m pytest tests/
npm test

# Manual testing:
- Answer question correctly → should progress
- Answer incorrectly → should repeat pattern
- Cross out correct answer → should detect pattern
- Take >180 seconds → should flag overthinking
```

### 6. DOCUMENTATION
Every new feature needs:
```markdown
## Feature: [Name]
### Purpose
How this helps reach 99th percentile

### Behavioral Data Tracked
- What we track
- Why we track it
- How it identifies patterns

### Adaptive Logic
- How it adjusts to user
- When it serves this content
- Stop condition

### Code Location
- Backend: /path/to/file.py
- Frontend: /path/to/file.js
- Database: schema changes
```

---

## 🚫 DON'T DO THIS

1. **Don't add decorative UI elements** - Keep it black and minimal
2. **Don't show all questions sequentially** - Must be adaptive
3. **Don't give lengthy explanations** - 3-second rule
4. **Don't ignore behavioral data** - Track everything
5. **Don't add features that don't target weaknesses**
6. **Don't complicate when simple works** (Occam's Razor)
7. **Don't assume - use First Principles thinking**

---

## ✅ ALWAYS DO THIS

1. **Always track**: time, confidence, cross-outs, changes
2. **Always adapt**: serve questions based on weak patterns
3. **Always minimize**: black UI, white text, no frills
4. **Always analyze**: identify reasoning patterns
5. **Always focus**: on getting to 99th percentile
6. **Always test**: behavioral tracking and adaptation
7. **Always document**: why each decision helps mastery

---

## 📊 Success Metrics for Every Feature

Ask: Does this feature improve:
- **Questions to mastery** (target: <800)
- **Pattern identification** (target: 90% accuracy)
- **Time to feedback** (target: <3 seconds)
- **Adaptive accuracy** (correct difficulty selection)
- **User mastery rate** (target: 95%+)

---

## 🧠 Reasoning Patterns Reference

When coding pattern detection, always check against:
```
Information Processing: anchoring, tunnel_vision, missed_qualifiers
Clinical Reasoning: wrong_urgency, treating_before_diagnosing
Answer Selection: overthinking, eliminated_correct
NBME Tricks: buzzword_wrong_picture, one_step_too_far
Test Taking: poor_time_management, not_checking_vitals
```

---

## 📝 Scratchpad Structure

Always create scratchpads:
```
/scratchpads/
├── shelfsense_[feature]_plan.md     # Planning
├── shelfsense_[feature]_impl.md     # Implementation notes
├── shelfsense_[feature]_test.md     # Test cases
└── shelfsense_patterns_found.md     # New patterns discovered
```

---

## 🔄 Review Checklist

Before ANY commit:
- [ ] Tracks behavioral data?
- [ ] Adapts to weakness?
- [ ] UI remains minimal black?
- [ ] Feedback under 3 seconds?
- [ ] Helps reach 99th percentile?
- [ ] Simplest solution? (Occam's)
- [ ] Based on first principles?
- [ ] Documented reasoning?

---

## 💭 Periodic Reminders

Every 10 commits:
1. Review this issue
2. Check if we're still targeting 99th percentile
3. Verify adaptive algorithm is working
4. Ensure UI hasn't become cluttered
5. Run `/clear` if context getting large

---

## 🎯 Remember the Mission

**Every line of code should help a medical student go from 75% to 99% in less time with fewer questions through adaptive targeting of their specific weaknesses.**

If it doesn't serve this mission, don't build it.

---

**Last Updated**: November 19, 2025
**Project Doc**: SHELFSENSE_COMPLETE_PROJECT.md
**Owner**: @devaun23
