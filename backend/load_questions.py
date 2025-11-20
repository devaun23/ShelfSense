"""
Load all 2,001 questions from JSON into database
"""

import json
import sys
from pathlib import Path

# Add app directory to path
sys.path.insert(0, str(Path(__file__).parent))

from app.database import SessionLocal, engine, Base
from app.models.models import Question

def load_questions_from_json():
    """Load all questions from master database JSON"""

    # Path to master database
    json_path = Path(__file__).parent.parent / "data" / "extracted_questions" / "shelfsense_master_database.json"

    if not json_path.exists():
        print(f"Error: {json_path} not found")
        return

    print(f"Loading questions from: {json_path}")

    with open(json_path, 'r') as f:
        data = json.load(f)

    # Extract questions from nested structure
    if isinstance(data, dict) and 'questions' in data:
        questions_data = data['questions']
    else:
        questions_data = data

    print(f"Found {len(questions_data)} questions in JSON")

    # Create database session
    db = SessionLocal()

    try:
        # Clear existing questions (for fresh load)
        db.query(Question).delete()
        db.commit()
        print("Cleared existing questions")

        # Load questions
        loaded = 0
        for q_data in questions_data:
            # Extract choices - handle both list of strings and list of objects
            choices = []
            if 'choices' in q_data and isinstance(q_data['choices'], list):
                # Convert from object format to simple text list
                for choice in q_data['choices']:
                    if isinstance(choice, dict) and 'text' in choice:
                        choices.append(choice['text'])
                    elif isinstance(choice, str):
                        choices.append(choice)
            elif 'options' in q_data and isinstance(q_data['options'], list):
                for choice in q_data['options']:
                    if isinstance(choice, dict) and 'text' in choice:
                        choices.append(choice['text'])
                    elif isinstance(choice, str):
                        choices.append(choice)

            if not choices:
                print(f"Warning: No choices found for question {q_data.get('id', 'unknown')}, skipping")
                continue

            # Build vignette from complex structure or use simple string
            vignette = ""
            if isinstance(q_data.get('vignette'), dict):
                v = q_data['vignette']
                vignette = f"{v.get('demographics', '')} {v.get('presentation', '')}".strip()
                if q_data.get('question_stem'):
                    vignette = f"{vignette}\n\n{q_data['question_stem']}"
            else:
                vignette = str(q_data.get('vignette', ''))

            # Get explanation
            explanation = ""
            if isinstance(q_data.get('explanation'), dict):
                explanation = q_data['explanation'].get('correct_answer_explanation', '')
            else:
                explanation = q_data.get('explanation', '')

            question = Question(
                vignette=vignette,
                answer_key=q_data.get('answer_key', q_data.get('correct_answer', '')),
                choices=choices,
                explanation=explanation,
                source=q_data.get('source', ''),
                recency_tier=q_data.get('recency_tier', q_data.get('tier')),
                recency_weight=q_data.get('recency_weight'),
                extra_data={'original_id': q_data.get('id'), 'specialty': q_data.get('specialty')}
            )

            db.add(question)
            loaded += 1

            if loaded % 100 == 0:
                print(f"Loaded {loaded} questions...")
                db.commit()

        # Final commit
        db.commit()
        print(f"\n✓ Successfully loaded {loaded} questions into database")

        # Verify
        total = db.query(Question).count()
        print(f"✓ Verified: {total} questions in database")

        # Show recency weight distribution
        tier_1 = db.query(Question).filter(Question.recency_tier == 1).count()
        tier_2 = db.query(Question).filter(Question.recency_tier == 2).count()
        tier_3 = db.query(Question).filter(Question.recency_tier == 3).count()
        tier_4 = db.query(Question).filter(Question.recency_tier == 4).count()

        print(f"\nRecency Weight Distribution:")
        print(f"  Tier 1 (1.0): {tier_1} questions")
        print(f"  Tier 2 (0.85): {tier_2} questions")
        print(f"  Tier 3 (0.70): {tier_3} questions")
        print(f"  Tier 4 (0.55): {tier_4} questions")

    except Exception as e:
        print(f"Error loading questions: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print("=" * 60)
    print("ShelfSense - Question Database Loader")
    print("=" * 60)

    # Create tables if they don't exist
    Base.metadata.create_all(bind=engine)
    print("✓ Database tables created")

    load_questions_from_json()

    print("\n" + "=" * 60)
    print("Database ready!")
    print("=" * 60)
