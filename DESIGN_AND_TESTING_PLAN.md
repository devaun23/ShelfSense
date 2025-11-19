# ShelfSense Design & Testing Plan

## Design System

### Color Palette
```
Primary Background: #000000 (Pure Black)
Text Color: #FFFFFF (Pure White)
Progress Bar: #1E3A8A (Dark Navy Blue)
Progress Bar Fill: #3B82F6 (Brighter Blue for contrast)
Accent/Hover: #60A5FA (Light Blue)
Borders/Dividers: #1F1F1F (Dark Gray)
Correct Answer: #10B981 (Green)
Incorrect Answer: #EF4444 (Red)
```

### Typography
```
Font Family:
  - Primary: Inter, SF Pro Display, -apple-system, system-ui
  - Monospace (for vitals/labs): JetBrains Mono, Monaco, Consolas

Font Sizes:
  - Question text: 16px / 1rem
  - Answer choices: 15px / 0.9375rem
  - Explanation text: 14px / 0.875rem
  - UI elements: 13px / 0.8125rem
  - Headers: 24px / 1.5rem

Line Height: 1.6 (for readability)
```

### Layout Principles
1. **Minimalism** - Zero unnecessary elements
2. **Focus** - One question at a time, full screen
3. **Clarity** - High contrast (white on black)
4. **Efficiency** - Keyboard shortcuts for everything
5. **Data** - Silent tracking, visible insights

---

## Interface Mockup

### Main Question Screen

```
┌─────────────────────────────────────────────────────────────────────┐
│ ShelfSense                                    [123/1000] [⚙️] [👤]  │ ← Header (black bg)
├─────────────────────────────────────────────────────────────────────┤
│ ████████████████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░     │ ← Navy progress bar
│                                                               12.3%  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  Question 123                                    [Surgery] [Tier 2]  │
│                                                                       │
│  A 68-year-old woman comes to the emergency department because       │
│  of severe right upper quadrant pain and fever for 6 hours. She      │
│  has a history of cholecystitis. Her temperature is 39°C (102.2°F),  │
│  pulse is 120/min, and blood pressure is 82/48 mm Hg.                │
│                                                                       │
│  Physical examination shows right upper quadrant tenderness and      │
│  a positive Murphy sign.                                             │
│                                                                       │
│  Which of the following is the most appropriate next step?           │
│                                                                       │
│  ○ A. CT scan of the abdomen                                         │
│  ○ B. ERCP                                                           │
│  ○ C. HIDA scan                                                      │
│  ○ D. IV antibiotics and urgent cholecystectomy                      │
│  ○ E. Percutaneous cholecystostomy                                   │
│                                                                       │
│                                                                       │
│                             [Submit Answer]                           │
│                                                                       │
│                         or press 1-5 or A-E                          │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘

BLACK BACKGROUND (#000000)
WHITE TEXT (#FFFFFF)
NAVY BLUE PROGRESS (#1E3A8A)
```

### After Answer Submission

```
┌─────────────────────────────────────────────────────────────────────┐
│ ShelfSense                                    [123/1000] [⚙️] [👤]  │
├─────────────────────────────────────────────────────────────────────┤
│ ████████████████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░     │
│                                                               12.3%  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ✓ Correct!                                                          │ ← Green check
│  The answer is D                                                     │
│                                                                       │
│  [Vignette shown above, choices grayed out with D highlighted]       │
│                                                                       │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │ Explanation                                                     │ │
│  │                                                                 │ │
│  │ Acute cholecystitis with hemodynamic instability requires      │ │
│  │ source control.                                                │ │
│  │                                                                 │ │
│  │ Clinical reasoning: BP 82/48 (systolic <90) indicates septic   │ │
│  │ shock from cholecystitis. Stable cholecystitis gets antibiotics│ │
│  │ and elective surgery within 72 hours. Unstable cholecystitis   │ │
│  │ needs antibiotics and urgent surgery. The hypotension changes  │ │
│  │ this from elective to urgent. Source control takes priority    │ │
│  │ over additional imaging when septic.                           │ │
│  │                                                                 │ │
│  │ ▼ Why not the other options?                                   │ │ ← Expandable
│  └────────────────────────────────────────────────────────────────┘ │
│                                                                       │
│  Reasoning pattern: Stable/Unstable Bifurcation                      │
│  Your performance on this pattern: 67% (below average)               │
│                                                                       │
│                          [Next Question →]                            │
│                                                                       │
│                         or press Space/Enter                          │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

### Session Stats Overlay (Press 'S')

```
┌─────────────────────────────────────────────────────────────────────┐
│                       Session Statistics                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  Questions Answered: 123/1000                                        │
│  Accuracy: 78% (96/123)                                              │
│  Time Elapsed: 1h 23m                                                │
│  Avg Time per Question: 40s                                          │
│                                                                       │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  Performance by Specialty                                     │  │
│  │                                                                │  │
│  │  Emergency Medicine  ████████████░░░░░  80% (24/30)          │  │
│  │  Internal Medicine   ███████░░░░░░░░░░  67% (20/30)          │  │
│  │  Neurology           ████████████████░  85% (26/30)          │  │
│  │  Pediatrics          ██████████░░░░░░░  72% (13/18)          │  │
│  │  Surgery             █████████████░░░░  78% (13/15)          │  │
│  │                                                                │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                       │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  Weakest Reasoning Patterns                                   │  │
│  │                                                                │  │
│  │  1. Timeline Errors              ████░░░░░░░  55% (11/20)    │  │
│  │  2. Stable/Unstable Bifurcation  ██████░░░░░  67% (14/21)    │  │
│  │  3. Treatment Hierarchy          ███████░░░░  71% (15/21)    │  │
│  │                                                                │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                       │
│                        [Resume] [End Session]                         │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Data Collection Plan

### What We Track (Silently)

#### 1. Question-Level Metrics
```javascript
{
  question_id: "surgery_003",
  user_id: "devaun_test_001",
  timestamp: "2025-11-19T16:30:45Z",

  // Answer data
  answer_selected: "D",
  is_correct: true,
  time_to_answer: 42000, // milliseconds
  confidence: "high", // detected from time + pattern

  // Interaction data
  times_vignette_reread: 1,
  hover_duration_on_choices: [2000, 1500, 3000, 5000, 2000], // ms per choice
  choices_eliminated: ["B", "E"], // based on hover patterns
  final_choice_hesitation: false, // did they hover on submit?
}
```

#### 2. Explanation-Level Metrics
```javascript
{
  explanation_id: "surgery_003_v2",
  user_id: "devaun_test_001",
  timestamp: "2025-11-19T16:31:30Z",

  // Immediate behavior
  time_spent_reading: 15000, // ms
  scrolled_back_to_reread: false,
  expanded_distractors: true,
  hover_on_clinical_reasoning: 8000, // ms

  // Delayed validation (24hrs later)
  retention_test_correct: null, // filled later
  similar_question_correct: null, // filled later
}
```

#### 3. Session-Level Metrics
```javascript
{
  session_id: "session_20251119_001",
  user_id: "devaun_test_001",
  start_time: "2025-11-19T15:00:00Z",
  end_time: "2025-11-19T17:30:00Z",

  // Performance
  questions_answered: 123,
  correct_count: 96,
  accuracy: 0.78,

  // Patterns
  weakest_patterns: ["timeline_errors", "stable_unstable"],
  strongest_patterns: ["diagnostic_sequence", "differential_narrowing"],

  // Specialty performance
  specialty_breakdown: {
    "Emergency Medicine": {answered: 30, correct: 24, accuracy: 0.80},
    "Internal Medicine": {answered: 30, correct: 20, accuracy: 0.67},
    // ...
  }
}
```

#### 4. Long-Term Tracking
```javascript
{
  user_id: "devaun_test_001",

  // Retention curves
  retention_by_day: {
    "day_1": 0.78,
    "day_3": 0.72,
    "day_7": 0.68,
    "day_14": 0.65,
    "day_30": 0.62
  },

  // Pattern mastery
  pattern_progress: {
    "timeline_errors": {
      "week_1": 0.55,
      "week_2": 0.61,
      "week_3": 0.68,
      "week_4": 0.74
    }
  },

  // Predicted score
  current_predicted_score: 245, // USMLE scale
  confidence_interval: [238, 252]
}
```

---

## Testing Protocol (You as Test Subject)

### Phase 1: Baseline Testing (Week 1)
**Goal:** Establish your current performance and learning patterns

**Protocol:**
1. Answer 50 questions per day (mix of all specialties)
2. No time limit - answer naturally
3. Read all explanations
4. No external resources

**What We'll Learn:**
- Your baseline accuracy by specialty
- Which reasoning patterns you struggle with
- How you interact with explanations
- Your natural study pace

### Phase 2: Retention Testing (Week 2)
**Goal:** Measure how well explanations stick

**Protocol:**
1. Day 8: Answer 50 NEW questions
2. Day 9: Re-answer 25 questions from Week 1 (mixed in with new)
3. Day 10-14: Continue with new questions
4. Track: Do you get similar questions right?

**What We'll Learn:**
- Which explanations actually taught you
- Which ones need improvement
- Your retention curve
- Pattern-specific retention rates

### Phase 3: A/B Testing (Week 3-4)
**Goal:** Test explanation improvements

**Protocol:**
1. We identify your 10 worst-performing explanations
2. Create improved versions (Version B)
3. You get 50/50 split: some Version A, some Version B
4. You don't know which is which
5. Test retention on both versions

**What We'll Learn:**
- Which explanation style works better for you
- Impact of explicit thresholds vs implicit
- Value of distractor explanations
- Optimal explanation length

### Phase 4: Adaptive Testing (Week 5-8)
**Goal:** Test the adaptive learning engine

**Protocol:**
1. System identifies your weakest patterns
2. Serves you more questions targeting those patterns
3. Tracks improvement over time
4. Adjusts difficulty based on performance

**What We'll Learn:**
- How fast you improve on weak patterns
- Whether focused practice works better
- Optimal question mix for learning
- Spacing intervals for retention

---

## Data Dashboard (For You)

### Daily View
```
Today's Performance
─────────────────────────────────────────
Questions Answered: 50
Accuracy: 82% ↑4%
Time per Question: 38s ↓2s

Your Weakest Today:
1. Timeline Errors (60%)
2. Treatment Hierarchy (70%)

Recommendation:
Focus on 15 timeline questions tomorrow
```

### Weekly View
```
Week 1 Progress
─────────────────────────────────────────
Total Questions: 350
Overall Accuracy: 78%
Improvement: +6% since start

Mastered Patterns:
✓ Diagnostic Sequence (90%)
✓ Differential Narrowing (88%)

Needs Work:
⚠ Timeline Errors (55% → 62%, improving)
⚠ Stable/Unstable (67%, plateau)

Predicted Score: 245 (CI: 238-252)
Target Score: 260
Gap: 15 points
Estimated Time to Target: 4-6 weeks
```

### Insights View
```
Learning Insights
─────────────────────────────────────────
You learn best:
• In 45-60 minute sessions
• With morning study (82% vs 74% evening)
• When reading explanations slowly (15s avg)
• After sleeping on material (retention +8%)

You struggle with:
• Questions with time pressure
• Rushed explanation reading (<10s)
• Late evening sessions

Personalized Tips:
1. Study in mornings when possible
2. Take 5min break every hour
3. Don't rush explanations
4. Review weak patterns before bed
```

---

## Implementation Checklist

### Phase 1: MVP (Minimum Viable Product)
- [ ] Black/white/navy UI implemented
- [ ] Question display working
- [ ] Answer submission and feedback
- [ ] Basic explanation display
- [ ] Progress tracking
- [ ] Session statistics
- [ ] Data collection (silent)

### Phase 2: Analytics
- [ ] Dashboard showing performance
- [ ] Specialty breakdown
- [ ] Reasoning pattern tracking
- [ ] Retention testing automation
- [ ] Prediction algorithm

### Phase 3: Adaptive Features
- [ ] A/B testing framework
- [ ] Explanation versioning
- [ ] Automatic improvement promotion
- [ ] Weakness-based question selection
- [ ] Personalized recommendations

---

## Tech Stack Recommendation

### Frontend
```
Framework: Next.js 14 (React)
Language: TypeScript
Styling: Tailwind CSS
State: Zustand (lightweight)
Charts: Recharts
Deployment: Vercel
```

### Backend
```
Framework: FastAPI (Python)
Database: PostgreSQL
Cache: Redis
Auth: JWT
Deployment: Railway/Render
```

### Data Tracking
```
Events: PostHog or custom
Storage: PostgreSQL + TimescaleDB
Analytics: Python (pandas, scikit-learn)
```

---

## Next Steps

1. **Finish question extraction** (get to 1,300+ shelf + 2,000+ NBME)
2. **Upload remaining resources** (UWorld, AMBOSS, First Aid)
3. **Build MVP** (basic black/white/navy interface)
4. **Start testing on you** (establish baseline)
5. **Iterate based on your data** (improve continuously)

This system will be specifically tuned to YOUR learning patterns, then generalized for other students.
