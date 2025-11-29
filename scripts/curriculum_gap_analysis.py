#!/usr/bin/env python3
"""
Curriculum Gap Analysis Script

Maps existing questions to the NBME Step 2 CK curriculum matrix
and identifies gaps for targeted question generation.

Usage:
    cd backend && python ../scripts/curriculum_gap_analysis.py
"""

import json
import re
import sqlite3
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple

# NBME Step 2 CK Content Outline (2026 update)
SYSTEM_WEIGHTS = {
    "social_sciences_ethics": {"min": 10, "max": 15, "priority": "HIGH"},
    "renal_urinary_reproductive": {"min": 7, "max": 13, "priority": "HIGH"},
    "cardiovascular": {"min": 6, "max": 12, "priority": "HIGH"},
    "musculoskeletal_skin": {"min": 6, "max": 12, "priority": "HIGH"},
    "behavioral_health": {"min": 5, "max": 10, "priority": "MEDIUM"},
    "nervous_system": {"min": 5, "max": 10, "priority": "MEDIUM"},
    "respiratory": {"min": 5, "max": 10, "priority": "MEDIUM"},
    "gastrointestinal": {"min": 5, "max": 10, "priority": "MEDIUM"},
    "multisystem": {"min": 4, "max": 8, "priority": "MEDIUM"},
    "immune": {"min": 3, "max": 5, "priority": "MEDIUM"},
    "blood_lymph": {"min": 3, "max": 6, "priority": "MEDIUM"},
    "biostatistics_epi": {"min": 3, "max": 5, "priority": "MEDIUM"},
    "pregnancy_ob": {"min": 3, "max": 7, "priority": "MEDIUM"},
    "endocrine": {"min": 3, "max": 7, "priority": "MEDIUM"},
    "human_development": {"min": 2, "max": 4, "priority": "LOW"},
}

TASK_WEIGHTS = {
    "diagnosis": {"min": 16, "max": 20, "priority": "HIGH"},
    "lab_diagnostic": {"min": 13, "max": 17, "priority": "HIGH"},
    "mixed_management": {"min": 12, "max": 16, "priority": "HIGH"},
    "pharmacotherapy": {"min": 8, "max": 12, "priority": "MEDIUM"},
    "clinical_interventions": {"min": 6, "max": 10, "priority": "MEDIUM"},
    "health_maintenance": {"min": 5, "max": 10, "priority": "MEDIUM"},
    "prognosis": {"min": 5, "max": 9, "priority": "MEDIUM"},
    "systems_practice": {"min": 5, "max": 7, "priority": "MEDIUM"},
    "professionalism": {"min": 5, "max": 7, "priority": "MEDIUM"},
    "practice_learning": {"min": 3, "max": 5, "priority": "LOW"},
}

DISCIPLINE_WEIGHTS = {
    "internal_medicine": {"min": 55, "max": 65},
    "surgery": {"min": 20, "max": 30},
    "pediatrics": {"min": 17, "max": 27},
    "obgyn": {"min": 10, "max": 20},
    "psychiatry": {"min": 10, "max": 15},
}

# Keywords for system classification
SYSTEM_KEYWORDS = {
    "cardiovascular": [
        "heart", "cardiac", "chest pain", "myocardial", "arrhythmia", "hypertension",
        "blood pressure", "murmur", "coronary", "atrial", "ventricular", "aortic",
        "mitral", "tricuspid", "palpitation", "syncope", "edema", "dvt", "pulmonary embolism",
        "stroke", "tia", "carotid", "peripheral vascular", "claudication"
    ],
    "respiratory": [
        "lung", "pulmonary", "breath", "cough", "wheeze", "asthma", "copd", "pneumonia",
        "bronchitis", "dyspnea", "hypoxia", "oxygen", "chest x-ray", "tuberculosis",
        "pleural", "sputum", "hemoptysis", "pulmonary function"
    ],
    "gastrointestinal": [
        "abdomen", "abdominal", "liver", "hepat", "bowel", "colon", "stomach", "gastric",
        "intestin", "diarrhea", "constipation", "nausea", "vomit", "stool", "rectal",
        "appendic", "gallbladder", "pancrea", "esophag", "dysphagia", "jaundice",
        "ascites", "cirrhosis", "gi bleed", "melena", "hematemesis"
    ],
    "renal_urinary_reproductive": [
        "kidney", "renal", "urinary", "bladder", "urine", "creatinine", "bun",
        "dialysis", "proteinuria", "hematuria", "dysuria", "prostate", "testicular",
        "ovarian", "uterine", "vaginal", "menstrual", "pelvic", "sexually transmitted",
        "std", "sti", "contraception", "infertility", "erectile"
    ],
    "nervous_system": [
        "brain", "neurolog", "headache", "seizure", "stroke", "weakness", "numbness",
        "tingling", "paresthesia", "paralysis", "dementia", "alzheimer", "parkinson",
        "multiple sclerosis", "meningitis", "encephalitis", "neuropathy", "lumbar puncture",
        "cranial nerve", "reflex", "gait", "tremor", "vertigo", "dizziness"
    ],
    "musculoskeletal_skin": [
        "joint", "arthritis", "muscle", "bone", "fracture", "back pain", "neck pain",
        "knee", "hip", "shoulder", "wrist", "ankle", "osteoporosis", "rash", "skin",
        "dermatitis", "psoriasis", "melanoma", "wound", "laceration", "burn",
        "erythema", "pruritus", "lesion", "rheumatoid", "lupus", "gout"
    ],
    "endocrine": [
        "diabetes", "thyroid", "glucose", "insulin", "hba1c", "hyperglycemia",
        "hypoglycemia", "hypothyroid", "hyperthyroid", "adrenal", "cortisol",
        "pituitary", "hormone", "testosterone", "estrogen", "calcium", "parathyroid",
        "osteoporosis", "obesity", "metabolic"
    ],
    "behavioral_health": [
        "depression", "anxiety", "psychiatric", "mental", "suicide", "psychosis",
        "schizophrenia", "bipolar", "mood", "panic", "ptsd", "ocd", "adhd",
        "eating disorder", "substance abuse", "alcohol", "drug abuse", "withdrawal",
        "insomnia", "sleep", "stress", "counseling", "therapy"
    ],
    "immune": [
        "allergy", "allergic", "anaphylaxis", "immune", "autoimmune", "hiv", "aids",
        "immunodeficiency", "transplant", "rejection", "vaccine", "immunization",
        "lymph node", "spleen", "immunoglobulin", "antibody"
    ],
    "blood_lymph": [
        "anemia", "hemoglobin", "hematocrit", "platelet", "bleeding", "clotting",
        "coagulation", "leukemia", "lymphoma", "transfusion", "sickle cell",
        "thalassemia", "neutropenia", "thrombocytopenia", "anticoagulant", "warfarin"
    ],
    "pregnancy_ob": [
        "pregnant", "pregnancy", "prenatal", "gestational", "trimester", "fetal",
        "labor", "delivery", "cesarean", "postpartum", "breastfeeding", "lactation",
        "preeclampsia", "eclampsia", "placenta", "amniotic", "contractions"
    ],
    "biostatistics_epi": [
        "sensitivity", "specificity", "positive predictive", "negative predictive",
        "odds ratio", "relative risk", "confidence interval", "p-value", "statistical",
        "study design", "randomized", "cohort", "case-control", "prevalence", "incidence",
        "screening", "epidemiology", "population", "meta-analysis"
    ],
    "social_sciences_ethics": [
        "informed consent", "ethics", "autonomy", "beneficence", "confidentiality",
        "hipaa", "advance directive", "end of life", "palliative", "hospice",
        "capacity", "competence", "surrogate", "power of attorney", "malpractice",
        "disclosure", "error", "quality improvement", "patient safety", "handoff",
        "communication", "cultural", "interpreter", "health literacy"
    ],
    "human_development": [
        "well child", "developmental milestone", "growth chart", "immunization schedule",
        "adolescent", "geriatric", "elderly", "aging", "preventive care", "screening age"
    ],
    "multisystem": [
        "sepsis", "shock", "trauma", "multiorgan", "icu", "critical care", "fever",
        "weight loss", "fatigue", "malaise", "night sweats", "cachexia"
    ],
}

# Keywords for task classification
TASK_KEYWORDS = {
    "diagnosis": [
        "most likely diagnosis", "most likely cause", "what is the diagnosis",
        "most likely explanation", "best explains", "most consistent with",
        "most likely etiology", "which of the following is the diagnosis"
    ],
    "lab_diagnostic": [
        "next step in workup", "next diagnostic step", "most appropriate test",
        "which test", "next step in evaluation", "confirm the diagnosis",
        "most helpful", "initial workup", "appropriate imaging", "laboratory"
    ],
    "mixed_management": [
        "most appropriate management", "next step in management", "best initial therapy",
        "most appropriate treatment", "how should you manage", "next best step",
        "initial management", "appropriate intervention"
    ],
    "pharmacotherapy": [
        "which medication", "drug of choice", "first-line treatment", "prescribe",
        "pharmacologic", "most appropriate drug", "medication adjustment",
        "add which medication", "discontinue", "contraindicated medication"
    ],
    "clinical_interventions": [
        "surgical", "procedure", "surgery", "biopsy", "excision", "intubation",
        "catheter", "drain", "resection", "intervention", "operative"
    ],
    "health_maintenance": [
        "screening", "prevention", "vaccine", "immunization", "counseling",
        "risk reduction", "lifestyle", "health maintenance", "preventive"
    ],
    "prognosis": [
        "prognosis", "outcome", "complication", "risk of", "likelihood of",
        "expected course", "mortality", "survival", "recurrence"
    ],
    "professionalism": [
        "appropriate response", "how should you respond", "what do you tell",
        "ethical", "should you", "appropriate to say", "disclosure",
        "communication with patient", "family meeting"
    ],
    "systems_practice": [
        "quality improvement", "patient safety", "error", "handoff", "transition",
        "discharge planning", "care coordination", "system", "protocol"
    ],
    "practice_learning": [
        "evidence", "study", "research", "literature", "guideline", "recommendation",
        "level of evidence", "grade of recommendation"
    ],
}


def classify_system(vignette: str, specialty: str) -> str:
    """Classify a question into a body system based on vignette content."""
    vignette_lower = vignette.lower()

    # Score each system based on keyword matches
    scores = defaultdict(int)
    for system, keywords in SYSTEM_KEYWORDS.items():
        for keyword in keywords:
            if keyword in vignette_lower:
                scores[system] += 1

    # Return highest scoring system, or fallback to specialty mapping
    if scores:
        return max(scores, key=scores.get)

    # Specialty-based fallback
    specialty_to_system = {
        "internal_medicine": "multisystem",
        "surgery": "gastrointestinal",
        "pediatrics": "human_development",
        "neurology": "nervous_system",
        "psychiatry": "behavioral_health",
        "obgyn": "pregnancy_ob",
        "general": "multisystem",
    }
    return specialty_to_system.get(specialty, "multisystem")


def classify_task(vignette: str) -> str:
    """Classify a question into a physician task based on question stem."""
    vignette_lower = vignette.lower()

    # Score each task based on keyword matches
    scores = defaultdict(int)
    for task, keywords in TASK_KEYWORDS.items():
        for keyword in keywords:
            if keyword in vignette_lower:
                scores[task] += 2  # Higher weight for exact phrase matches

    # Return highest scoring task
    if scores:
        return max(scores, key=scores.get)

    # Default to diagnosis if no clear task identified
    return "diagnosis"


def map_specialty_to_discipline(specialty: str) -> str:
    """Map database specialty to NBME discipline."""
    mapping = {
        "internal_medicine": "internal_medicine",
        "surgery": "surgery",
        "pediatrics": "pediatrics",
        "neurology": "internal_medicine",  # Neurology is part of IM for Step 2
        "psychiatry": "psychiatry",
        "obgyn": "obgyn",
        "general": "internal_medicine",
    }
    return mapping.get(specialty, "internal_medicine")


def calculate_targets(total_questions: int) -> Tuple[Dict, Dict, Dict]:
    """Calculate target question counts based on NBME weightings."""
    system_targets = {}
    for system, weights in SYSTEM_WEIGHTS.items():
        target = (weights["min"] + weights["max"]) / 2 / 100 * total_questions
        system_targets[system] = {
            "min": int(weights["min"] / 100 * total_questions),
            "max": int(weights["max"] / 100 * total_questions),
            "target": int(target),
            "priority": weights["priority"],
        }

    task_targets = {}
    for task, weights in TASK_WEIGHTS.items():
        target = (weights["min"] + weights["max"]) / 2 / 100 * total_questions
        task_targets[task] = {
            "min": int(weights["min"] / 100 * total_questions),
            "max": int(weights["max"] / 100 * total_questions),
            "target": int(target),
            "priority": weights["priority"],
        }

    discipline_targets = {}
    for disc, weights in DISCIPLINE_WEIGHTS.items():
        target = (weights["min"] + weights["max"]) / 2 / 100 * total_questions
        discipline_targets[disc] = {
            "min": int(weights["min"] / 100 * total_questions),
            "max": int(weights["max"] / 100 * total_questions),
            "target": int(target),
        }

    return system_targets, task_targets, discipline_targets


def run_analysis(db_path: str = "shelfsense.db"):
    """Run the gap analysis on existing questions."""

    # Connect to database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Fetch all active questions
    cursor.execute("""
        SELECT id, vignette, specialty, difficulty_level, source_type
        FROM questions
        WHERE rejected = 0 OR rejected IS NULL
    """)
    questions = cursor.fetchall()
    conn.close()

    total = len(questions)
    print(f"\n{'='*60}")
    print(f"CURRICULUM GAP ANALYSIS")
    print(f"{'='*60}")
    print(f"Total active questions: {total}")
    print(f"Target for 280+: ~4,000-6,000 questions")
    print(f"Gap to fill: {max(0, 4000 - total):,} - {max(0, 6000 - total):,} questions")

    # Classify all questions
    system_counts = defaultdict(list)
    task_counts = defaultdict(list)
    discipline_counts = defaultdict(list)
    matrix_counts = defaultdict(lambda: defaultdict(list))

    for q_id, vignette, specialty, difficulty, source_type in questions:
        if not vignette:
            continue

        system = classify_system(vignette, specialty or "general")
        task = classify_task(vignette)
        discipline = map_specialty_to_discipline(specialty or "general")

        system_counts[system].append(q_id)
        task_counts[task].append(q_id)
        discipline_counts[discipline].append(q_id)
        matrix_counts[system][task].append(q_id)

    # Calculate targets for 4000 questions (comprehensive coverage)
    target_total = 4000
    system_targets, task_targets, discipline_targets = calculate_targets(target_total)

    # Print system coverage
    print(f"\n{'='*60}")
    print("SYSTEM COVERAGE")
    print(f"{'='*60}")
    print(f"{'System':<30} {'Current':>8} {'Target':>8} {'Gap':>8} {'Priority':>10}")
    print("-" * 60)

    system_gaps = []
    for system in sorted(SYSTEM_WEIGHTS.keys(), key=lambda x: -SYSTEM_WEIGHTS[x]["min"]):
        current = len(system_counts.get(system, []))
        target = system_targets[system]["target"]
        gap = max(0, target - current)
        priority = system_targets[system]["priority"]

        status = "OK" if current >= target else f"-{gap}"
        print(f"{system:<30} {current:>8} {target:>8} {status:>8} {priority:>10}")

        if gap > 0:
            system_gaps.append({
                "system": system,
                "current": current,
                "target": target,
                "gap": gap,
                "priority": priority,
            })

    # Print task coverage
    print(f"\n{'='*60}")
    print("PHYSICIAN TASK COVERAGE")
    print(f"{'='*60}")
    print(f"{'Task':<30} {'Current':>8} {'Target':>8} {'Gap':>8} {'Priority':>10}")
    print("-" * 60)

    task_gaps = []
    for task in sorted(TASK_WEIGHTS.keys(), key=lambda x: -TASK_WEIGHTS[x]["min"]):
        current = len(task_counts.get(task, []))
        target = task_targets[task]["target"]
        gap = max(0, target - current)
        priority = task_targets[task]["priority"]

        status = "OK" if current >= target else f"-{gap}"
        print(f"{task:<30} {current:>8} {target:>8} {status:>8} {priority:>10}")

        if gap > 0:
            task_gaps.append({
                "task": task,
                "current": current,
                "target": target,
                "gap": gap,
                "priority": priority,
            })

    # Print discipline coverage
    print(f"\n{'='*60}")
    print("DISCIPLINE COVERAGE")
    print(f"{'='*60}")
    print(f"{'Discipline':<30} {'Current':>8} {'Target':>8} {'Gap':>8}")
    print("-" * 60)

    for disc in sorted(DISCIPLINE_WEIGHTS.keys(), key=lambda x: -DISCIPLINE_WEIGHTS[x]["min"]):
        current = len(discipline_counts.get(disc, []))
        target = discipline_targets[disc]["target"]
        gap = max(0, target - current)

        status = "OK" if current >= target else f"-{gap}"
        print(f"{disc:<30} {current:>8} {target:>8} {status:>8}")

    # Print curriculum matrix
    print(f"\n{'='*60}")
    print("CURRICULUM MATRIX (System x Task)")
    print(f"{'='*60}")

    # Top tasks for columns
    top_tasks = ["diagnosis", "lab_diagnostic", "mixed_management", "pharmacotherapy"]
    header = f"{'System':<25}" + "".join([f"{t[:8]:>10}" for t in top_tasks])
    print(header)
    print("-" * (25 + 10 * len(top_tasks)))

    matrix_gaps = []
    for system in sorted(SYSTEM_WEIGHTS.keys(), key=lambda x: -SYSTEM_WEIGHTS[x]["min"]):
        row = f"{system[:24]:<25}"
        for task in top_tasks:
            count = len(matrix_counts[system][task])
            # Target: at least 10 questions per high-yield cell
            target = 10 if SYSTEM_WEIGHTS[system]["priority"] == "HIGH" else 5
            if count < target:
                row += f"{count:>10}"
                matrix_gaps.append({
                    "system": system,
                    "task": task,
                    "current": count,
                    "target": target,
                    "gap": target - count,
                    "priority_score": (
                        (3 if SYSTEM_WEIGHTS[system]["priority"] == "HIGH" else 1) *
                        (3 if TASK_WEIGHTS[task]["priority"] == "HIGH" else 1)
                    )
                })
            else:
                row += f"{count:>10}"
        print(row)

    # Priority generation order
    print(f"\n{'='*60}")
    print("PRIORITY GENERATION ORDER")
    print(f"{'='*60}")

    # Sort by priority score (HIGH system * HIGH task = 9, HIGH * MEDIUM = 3, etc.)
    matrix_gaps.sort(key=lambda x: (-x["priority_score"], -x["gap"]))

    print(f"\nTop 20 curriculum cells needing questions:")
    print(f"{'System':<25} {'Task':<20} {'Current':>8} {'Gap':>8} {'Score':>8}")
    print("-" * 70)

    for gap in matrix_gaps[:20]:
        print(f"{gap['system']:<25} {gap['task']:<20} {gap['current']:>8} {gap['gap']:>8} {gap['priority_score']:>8}")

    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")

    total_system_gap = sum(g["gap"] for g in system_gaps)
    total_task_gap = sum(g["gap"] for g in task_gaps)
    total_matrix_gap = sum(g["gap"] for g in matrix_gaps)

    print(f"Questions needed to reach 4,000 target: {max(0, 4000 - total):,}")
    print(f"System-level gaps: {total_system_gap:,} questions")
    print(f"Task-level gaps: {total_task_gap:,} questions")
    print(f"Matrix cell gaps: {total_matrix_gap:,} questions (high-yield cells)")

    # Save gaps to JSON for use by generator
    output = {
        "analysis_date": str(Path(__file__).stat().st_mtime),
        "total_questions": total,
        "target_questions": target_total,
        "system_gaps": system_gaps,
        "task_gaps": task_gaps,
        "matrix_gaps": matrix_gaps[:50],  # Top 50 priority cells
    }

    output_path = Path(__file__).parent.parent / "backend" / "curriculum_gaps.json"
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)

    print(f"\nGap analysis saved to: {output_path}")
    print(f"\nNext step: Run OllamaQuestionGenerator to fill priority gaps")

    return output


if __name__ == "__main__":
    import os
    os.chdir(Path(__file__).parent.parent / "backend")
    run_analysis()
