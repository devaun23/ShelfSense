# ShelfSense Behavioral Tracking System

## Overview

This document outlines the invisible behavioral tracking system that monitors user interaction with explanations to automatically improve their effectiveness.

## What We Track (Without User Knowing)

### 1. Mouse Hover Time

Track how long users hover over different parts of explanations to identify confusing sections.

```javascript
<div class="explanation" data-explanation-id="ex_001">
    Clinical reasoning: BP 80/50 defines instability...
</div>

let hoverStart, hoverEnd;
document.querySelector('.explanation').addEventListener('mouseenter', (e) => {
    hoverStart = Date.now();
});
document.querySelector('.explanation').addEventListener('mouseleave', (e) => {
    hoverEnd = Date.now();
    trackEvent('explanation_hover', {
        id: e.target.dataset.explanationId,
        duration: hoverEnd - hoverStart
    });
});
// Long hover = re-reading = confusion
```

### 2. Scroll Behavior

Monitor whether users scroll past quickly or stop to read.

```javascript
let explanationVisible = false;
const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            trackEvent('explanation_viewed', {
                id: entry.target.dataset.explanationId,
                timestamp: Date.now()
            });
        }
    });
});
// Did they scroll past quickly or stop to read?
```

### 3. Re-reading Pattern

Track if users scroll back to re-read explanations.

```javascript
let viewCount = 0;
window.addEventListener('scroll', () => {
    if (explanationInView() && !currentlyVisible) {
        viewCount++;
        if (viewCount > 1) {
            trackEvent('explanation_reread', {
                id: explanationId,
                count: viewCount
            });
        }
    }
});
// Multiple views = didn't understand first time
```

### 4. Next Question Timing

Measure time between explanation display and clicking next question.

```javascript
After showing explanation:
const comprehensionTime = timeToClickNext - explanationShownTime;

if (comprehensionTime < 2000) {
    // Clicked next immediately = didn't read
    flag('skipped_explanation');
} else if (comprehensionTime > 15000) {
    // Took very long = confused
    flag('struggled_with_explanation');
}
```

### 5. Subsequent Question Performance

The most important metric: Do they get similar questions right later?

```javascript
// 24 hours later, serve similar question:

if (user.answers_correctly) {
    // Explanation worked - they learned the pattern
    mark_explanation_effective(original_explanation_id);
} else if (user.makes_same_error) {
    // Explanation failed - didn't address their misconception
    mark_explanation_ineffective(original_explanation_id, 'same_error');
}
```

## Complete Tracking Function

```javascript
function trackExplanationEffectiveness(explanationId) {
    const metrics = {
        // Immediate behavior
        hoverDuration: null,
        scrollPauseDuration: null,
        rereadCount: 0,
        timeToNextQuestion: null,

        // Delayed validation
        similarQuestionCorrect: null,  // Check 24hrs later
        errorPattern: null,             // If wrong, what type?
        confidenceChange: null          // More or less confident?
    };

    // All tracked silently in background
    // User just sees explanation and moves on

    sendToBackend('/api/explanation-metrics', metrics);
}
```

## Backend Analysis

```python
def analyze_explanation_effectiveness(explanation_id):
    metrics = get_metrics(explanation_id)

    # Red flags that explanation isn't working:
    if metrics['avg_reread_count'] > 2:
        flag('confusing')

    if metrics['avg_hover_duration'] > 20000:
        flag('too_complex')

    if metrics['skip_rate'] > 0.3:
        flag('not_engaging')

    if metrics['retention_rate'] < 0.7:
        flag('not_memorable')

    if metrics['same_error_rate'] > 0.4:
        flag('missing_key_distinction')

    return recommendations
```

## User Experience vs What We Track

### What User Sees:
1. Gets question wrong
2. Sees explanation for 5-10 seconds
3. Clicks "Next Question"
4. Continues training
5. Days later, gets similar question

### What We Track (Invisibly):
1. How long they hovered over each part
2. If they scrolled back up to re-read
3. How quickly they moved on
4. If they got similar question right later
5. Their confidence changes

No surveys, no "rate this explanation", no thumbs up/down. Just pure behavioral data.

## Privacy Note

Store only:
- Interaction patterns (not screenshots)
- Timing data (not personal info)
- Performance metrics (not identity)

All data is anonymized and aggregated for analysis.
