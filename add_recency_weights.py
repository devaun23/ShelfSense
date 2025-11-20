#!/usr/bin/env python3
"""
Add Recency Weights to All Questions
Based on QUESTION_WEIGHTING_STRATEGY.md
"""

import json
from pathlib import Path
import re

def get_recency_weight(question):
    """
    Assign recency weight based on source
    Newer = More accurate for current exams
    """
    source = str(question.get('source', ''))

    # NBME weights (highest priority)
    if 'NBME 14' in source or 'NBME 13' in source or 'NBME 12' in source or 'NBME 11' in source:
        tier = 1
        weight = 1.0
    elif 'NBME 10' in source or 'NBME 9' in source or 'NBME 8' in source:
        tier = 2
        weight = 0.85
    elif 'NBME 7' in source or 'NBME 6' in source:
        tier = 3
        weight = 0.70
    elif 'NBME' in source:  # NBME 4, 5 or older
        tier = 4
        weight = 0.55

    # Shelf exam weights (infer from form/file number)
    elif any(x in source for x in ['Form 8', 'Form 7', '8 -', '7 -', 'Medicine 8', 'Medicine 7',
                                     'Neuro 8', 'Neuro 7', 'Pediatrics 8', 'Pediatrics 7',
                                     'Surgery 8', 'Surgery 7']):
        tier = 2
        weight = 0.85
    elif any(x in source for x in ['Form 6', 'Form 5', '6 -', '5 -']):
        tier = 3
        weight = 0.70
    elif any(x in source for x in ['Form 4', 'Form 3', '4 -', '3 -']):
        tier = 4
        weight = 0.55
    elif any(x in source for x in ['Form 2', 'Form 1', '2 -', '1 -']):
        tier = 5
        weight = 0.40

    # Default for unknown sources
    else:
        tier = 3
        weight = 0.60

    return {
        'recency_tier': tier,
        'recency_weight': weight
    }

def add_weights_to_database():
    """Add recency weights to master database"""
    print(f"\n{'='*70}")
    print("Adding Recency Weights to Master Database")
    print(f"{'='*70}\n")

    db_path = Path("/Users/devaun/ShelfSense/data/extracted_questions/shelfsense_master_database.json")

    if not db_path.exists():
        print(f"Error: Master database not found at {db_path}")
        return

    # Load database
    with open(db_path, 'r', encoding='utf-8') as f:
        master_db = json.load(f)

    questions = master_db.get('questions', [])
    print(f"Processing {len(questions)} questions...")

    # Add weights to each question
    tier_counts = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}

    for q in questions:
        weights = get_recency_weight(q)
        q['recency_tier'] = weights['recency_tier']
        q['recency_weight'] = weights['recency_weight']
        tier_counts[weights['recency_tier']] += 1

    # Update metadata
    master_db['metadata']['recency_weighted'] = True
    master_db['metadata']['weighting_version'] = '1.0'

    # Save updated database
    with open(db_path, 'w', encoding='utf-8') as f:
        json.dump(master_db, f, indent=2, ensure_ascii=False)

    print(f"✓ Added recency weights to all {len(questions)} questions")
    print(f"\nWeight Distribution:")
    print(f"  Tier 1 (Weight 1.0  - NBME 11-14):           {tier_counts[1]} questions")
    print(f"  Tier 2 (Weight 0.85 - NBME 8-10, Forms 7-8): {tier_counts[2]} questions")
    print(f"  Tier 3 (Weight 0.70 - NBME 6-7, Forms 5-6):  {tier_counts[3]} questions")
    print(f"  Tier 4 (Weight 0.55 - Older NBMEs, Forms 3-4): {tier_counts[4]} questions")
    print(f"  Tier 5 (Weight 0.40 - Forms 1-2):            {tier_counts[5]} questions")
    print(f"\n✓ Master database updated: {db_path}")
    print(f"{'='*70}\n")

if __name__ == "__main__":
    add_weights_to_database()
