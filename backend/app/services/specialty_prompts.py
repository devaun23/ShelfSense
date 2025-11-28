"""
Specialty-Specific Question Generation Configuration

Deep customization for each USMLE specialty with:
- Demographics and presentation styles
- Distractor patterns common to the specialty
- High-yield concepts from First Aid
- Validation rules specific to the specialty

Following ShelfSense guidelines:
- Adaptive First: Questions tailored to specialty patterns
- NBME Gold Book: Specialty-appropriate presentations
- 99th Percentile Goal: High-yield concepts targeted
"""

from typing import Dict, List, Optional
import random

# Comprehensive specialty configuration for deep customization
SPECIALTY_CONFIG = {
    "Medicine": {
        "full_name": "Internal Medicine",
        "demographics": {
            "age_ranges": [
                {"range": "45-65 years", "context": "chronic disease management", "weight": 0.4},
                {"range": "65-80 years", "context": "multiple comorbidities", "weight": 0.35},
                {"range": "25-45 years", "context": "acute presentations", "weight": 0.25},
            ],
            "common_settings": [
                "outpatient clinic",
                "hospital ward",
                "ICU",
                "emergency department",
            ],
            "risk_factors": [
                "type 2 diabetes mellitus",
                "hypertension",
                "hyperlipidemia",
                "smoking history",
                "obesity (BMI >30)",
                "family history of cardiovascular disease",
                "chronic kidney disease",
            ],
        },
        "presentation_style": """Progressive symptom onset with detailed workup. Internal medicine
vignettes typically include:
- Gradual symptom development over days to weeks
- Relevant past medical history affecting current presentation
- Complete vital signs with specific values
- Pertinent laboratory values (CBC, BMP, LFTs as appropriate)
- Imaging findings when relevant to diagnosis""",
        "distractor_patterns": [
            "Similar conditions in the differential (e.g., CHF vs COPD exacerbation)",
            "Related but premature management step (treat before diagnose)",
            "Outdated treatment guidelines (older first-line agents)",
            "Overtreatment of stable conditions",
            "Missing contraindication check before treatment",
        ],
        "high_yield_concepts": [
            "ACS management algorithm (STEMI vs NSTEMI)",
            "Heart failure classification and treatment (HFrEF vs HFpEF)",
            "Atrial fibrillation - rate vs rhythm control, anticoagulation",
            "Hypertensive emergency vs urgency",
            "COPD exacerbation management",
            "Community-acquired pneumonia empiric therapy",
            "Acute kidney injury workup (prerenal vs intrinsic vs postrenal)",
            "Diabetic ketoacidosis management",
            "Electrolyte correction (hyponatremia, hyperkalemia)",
            "Sepsis recognition and early goal-directed therapy",
        ],
        "validation_rules": [
            "Diagnosis questions must include relevant lab/imaging data",
            "Management questions must assess patient stability first",
            "Treatment questions must consider contraindications",
            "Vital signs must be explicitly stated for acute presentations",
        ],
        "typical_vitals": {
            "stable": "BP 130/80 mmHg, HR 78/min, RR 16/min, Temp 37.0°C, SpO2 98% on room air",
            "unstable": "BP 85/50 mmHg, HR 120/min, RR 28/min, Temp 39.2°C, SpO2 88% on room air",
        },
    },

    "Surgery": {
        "full_name": "Surgery",
        "demographics": {
            "age_ranges": [
                {"range": "30-50 years", "context": "trauma and acute abdomen", "weight": 0.35},
                {"range": "50-70 years", "context": "elective surgery and cancer", "weight": 0.4},
                {"range": "70-85 years", "context": "emergent surgery, comorbidities", "weight": 0.25},
            ],
            "common_settings": [
                "emergency department",
                "operating room",
                "post-operative ward",
                "surgical ICU",
            ],
            "risk_factors": [
                "previous abdominal surgery",
                "smoking",
                "obesity",
                "diabetes",
                "anticoagulation use",
                "immunosuppression",
            ],
        },
        "presentation_style": """Acute onset with physical exam focus. Surgical vignettes emphasize:
- Sudden symptom onset with precise timeline
- Detailed abdominal or focused physical exam findings
- Peritoneal signs when relevant (guarding, rebound, rigidity)
- Hemodynamic status for surgical decision-making
- Imaging findings (CT, ultrasound) when needed for diagnosis""",
        "distractor_patterns": [
            "Conservative management when surgery is indicated",
            "Imaging before stabilization in unstable patient",
            "Wrong surgical approach or timing",
            "Missing post-operative complication recognition",
            "Confusing similar acute abdominal conditions",
        ],
        "high_yield_concepts": [
            "Acute abdomen evaluation (appendicitis, cholecystitis, bowel obstruction)",
            "Trauma primary and secondary survey (ATLS)",
            "Surgical wound classification and infection",
            "Post-operative fever workup (5 W's)",
            "Hernia types and management (inguinal, femoral, incarcerated)",
            "Breast mass evaluation algorithm",
            "Thyroid nodule workup",
            "Peripheral arterial disease management",
            "Abdominal aortic aneurysm screening and rupture",
        ],
        "validation_rules": [
            "Acute presentations must include hemodynamic status",
            "Physical exam must include pertinent surgical signs",
            "Post-op questions must specify timeline from surgery",
            "Trauma questions must follow ATLS priorities",
        ],
        "typical_vitals": {
            "stable": "BP 125/75 mmHg, HR 82/min, RR 14/min, Temp 37.1°C, SpO2 99% on room air",
            "unstable": "BP 75/40 mmHg, HR 130/min, RR 26/min, Temp 38.8°C, SpO2 92% on 4L NC",
        },
    },

    "Pediatrics": {
        "full_name": "Pediatrics",
        "demographics": {
            "age_ranges": [
                {"range": "newborn (0-28 days)", "context": "neonatal conditions", "weight": 0.15},
                {"range": "infant (1-12 months)", "context": "developmental milestones, feeding", "weight": 0.2},
                {"range": "toddler (1-3 years)", "context": "infections, behavioral", "weight": 0.2},
                {"range": "preschool (3-5 years)", "context": "infections, development", "weight": 0.15},
                {"range": "school-age (6-12 years)", "context": "chronic conditions, school issues", "weight": 0.15},
                {"range": "adolescent (13-18 years)", "context": "puberty, risk behaviors", "weight": 0.15},
            ],
            "common_settings": [
                "pediatric clinic (well-child visit)",
                "pediatric emergency department",
                "newborn nursery",
                "NICU",
                "pediatric ward",
            ],
            "risk_factors": [
                "prematurity",
                "incomplete vaccinations",
                "daycare attendance",
                "sick contacts",
                "developmental delay",
                "failure to thrive",
            ],
        },
        "presentation_style": """Age-appropriate presentations with developmental context. Pediatric vignettes include:
- Specific age with developmental context
- Growth parameters (weight, height, head circumference percentiles)
- Vaccination status when relevant
- Developmental milestones for age
- Parent/caregiver observations
- Age-appropriate vital sign ranges""",
        "distractor_patterns": [
            "Adult treatment doses or medications",
            "Missing age-specific differential considerations",
            "Ignoring developmental red flags",
            "Wrong vaccination timing",
            "Confusing similar pediatric presentations by age",
        ],
        "high_yield_concepts": [
            "Developmental milestones by age",
            "Vaccination schedule and catch-up",
            "Febrile seizures management",
            "Bronchiolitis (RSV) management",
            "Croup vs epiglottitis",
            "Kawasaki disease criteria and treatment",
            "Intussusception presentation",
            "Pediatric UTI evaluation",
            "Failure to thrive workup",
            "ADHD diagnosis and management",
        ],
        "validation_rules": [
            "Age must be specific (not just 'child')",
            "Vital signs must be age-appropriate ranges",
            "Growth percentiles for relevant conditions",
            "Developmental context when appropriate",
            "Vaccination status for infectious presentations",
        ],
        "typical_vitals": {
            "infant_stable": "HR 120/min, RR 30/min, Temp 37.0°C, SpO2 98% on room air",
            "infant_unstable": "HR 180/min, RR 60/min, Temp 39.5°C, SpO2 88% on room air",
            "child_stable": "BP 95/60 mmHg, HR 90/min, RR 20/min, Temp 37.0°C, SpO2 99%",
            "child_unstable": "BP 70/40 mmHg, HR 150/min, RR 40/min, Temp 40.0°C, SpO2 85%",
        },
    },

    "Psychiatry": {
        "full_name": "Psychiatry",
        "demographics": {
            "age_ranges": [
                {"range": "18-30 years", "context": "first-episode psychosis, substance use", "weight": 0.3},
                {"range": "30-50 years", "context": "mood disorders, anxiety", "weight": 0.35},
                {"range": "50-70 years", "context": "depression, cognitive decline", "weight": 0.2},
                {"range": "adolescent (14-18 years)", "context": "eating disorders, self-harm", "weight": 0.15},
            ],
            "common_settings": [
                "outpatient psychiatry clinic",
                "psychiatric emergency department",
                "inpatient psychiatric unit",
                "consultation-liaison service",
            ],
            "risk_factors": [
                "family history of psychiatric illness",
                "prior psychiatric hospitalizations",
                "substance use history",
                "history of trauma",
                "recent stressors",
                "medication non-adherence",
            ],
        },
        "presentation_style": """Detailed psychiatric history with mental status examination. Psychiatric vignettes include:
- Presenting symptoms with timeline
- Psychiatric history (prior episodes, hospitalizations, medications)
- Substance use history
- Mental status examination findings
- Safety assessment (suicidal/homicidal ideation)
- Functional impairment""",
        "distractor_patterns": [
            "Missing medical cause of psychiatric symptoms",
            "Wrong medication class for diagnosis",
            "Ignoring drug-drug interactions",
            "Missing safety assessment",
            "Confusing similar psychiatric presentations",
        ],
        "high_yield_concepts": [
            "Major depressive disorder criteria and treatment",
            "Bipolar I vs II differentiation",
            "Schizophrenia diagnosis and antipsychotic selection",
            "Suicide risk assessment",
            "Alcohol withdrawal (CIWA) and treatment",
            "Opioid overdose and withdrawal management",
            "Generalized anxiety disorder treatment",
            "PTSD diagnosis and treatment",
            "Eating disorders (anorexia vs bulimia)",
            "Capacity assessment",
        ],
        "validation_rules": [
            "Must include mental status exam findings",
            "Safety assessment for mood/psychotic disorders",
            "Substance use screening when relevant",
            "Rule out medical causes mentioned",
            "Medication questions include side effect profiles",
        ],
        "typical_vitals": {
            "stable": "BP 120/80 mmHg, HR 72/min, RR 16/min, Temp 37.0°C",
            "withdrawal": "BP 160/100 mmHg, HR 110/min, RR 22/min, Temp 38.0°C, tremor present",
        },
    },

    "Obstetrics & Gynecology": {
        "full_name": "Obstetrics and Gynecology",
        "demographics": {
            "age_ranges": [
                {"range": "18-25 years", "context": "first pregnancy, contraception", "weight": 0.25},
                {"range": "25-35 years", "context": "pregnancy management, fertility", "weight": 0.35},
                {"range": "35-45 years", "context": "high-risk pregnancy, perimenopause", "weight": 0.25},
                {"range": "45-55 years", "context": "menopause, gynecologic malignancy", "weight": 0.15},
            ],
            "common_settings": [
                "prenatal clinic",
                "labor and delivery",
                "gynecology clinic",
                "emergency department",
            ],
            "risk_factors": [
                "advanced maternal age (>35)",
                "previous cesarean section",
                "gestational diabetes",
                "preeclampsia history",
                "multiple prior pregnancies",
                "obesity",
            ],
        },
        "presentation_style": """Obstetric history with gestational context. OBGYN vignettes include:
- Gravidity and parity (G_P_) format
- Last menstrual period or gestational age
- Prenatal care history
- Obstetric complications history
- Current pregnancy symptoms
- Fetal status (heart tones, movement)""",
        "distractor_patterns": [
            "Wrong gestational age for intervention",
            "Missing fetal assessment in obstetric emergency",
            "Contraindicated medications in pregnancy",
            "Wrong timing for prenatal screening",
            "Confusing similar bleeding presentations",
        ],
        "high_yield_concepts": [
            "Prenatal care timeline and screening",
            "Preeclampsia diagnosis and management",
            "Gestational diabetes screening and management",
            "Preterm labor evaluation",
            "Postpartum hemorrhage management",
            "Ectopic pregnancy diagnosis",
            "Abnormal uterine bleeding workup",
            "Contraception options and contraindications",
            "Ovarian mass evaluation",
            "Cervical cancer screening guidelines",
        ],
        "validation_rules": [
            "Obstetric cases must include G_P_ notation",
            "Gestational age must be specified",
            "Fetal status assessment in emergencies",
            "Medication safety in pregnancy considered",
            "Prenatal screening timing must be accurate",
        ],
        "typical_vitals": {
            "pregnancy_stable": "BP 110/70 mmHg, HR 88/min, RR 18/min, Temp 37.0°C, FHR 140/min",
            "preeclampsia": "BP 160/110 mmHg, HR 92/min, RR 20/min, Temp 37.0°C, 2+ proteinuria",
        },
    },

    "Emergency Medicine": {
        "full_name": "Emergency Medicine",
        "demographics": {
            "age_ranges": [
                {"range": "20-40 years", "context": "trauma, overdose", "weight": 0.3},
                {"range": "40-65 years", "context": "chest pain, acute abdomen", "weight": 0.35},
                {"range": "65+ years", "context": "falls, MI, stroke", "weight": 0.35},
            ],
            "common_settings": [
                "emergency department triage",
                "trauma bay",
                "resuscitation room",
            ],
            "risk_factors": [
                "mechanism of injury",
                "anticoagulation",
                "recent surgery",
                "substance use",
                "cardiac history",
            ],
        },
        "presentation_style": """Acute presentations requiring rapid assessment. EM vignettes emphasize:
- Exact timing of symptom onset
- Mechanism of injury for trauma
- Vital sign instability indicators
- Primary survey findings
- Need for immediate intervention vs workup""",
        "distractor_patterns": [
            "Workup before stabilization",
            "Missing life-threatening diagnosis",
            "Wrong triage priority",
            "Delayed definitive treatment",
            "Missing toxidrome recognition",
        ],
        "high_yield_concepts": [
            "ATLS primary and secondary survey",
            "STEMI activation criteria",
            "Stroke thrombolysis window",
            "Toxidrome recognition and antidotes",
            "Airway management indications",
            "Sepsis bundle compliance",
            "Trauma imaging decisions",
            "Resuscitation endpoints",
        ],
        "validation_rules": [
            "Stability assessment must be clear",
            "Time-sensitive diagnoses need explicit timeline",
            "Trauma must follow ATLS framework",
            "Vital signs required for all presentations",
        ],
        "typical_vitals": {
            "stable": "BP 130/85 mmHg, HR 88/min, RR 18/min, Temp 37.2°C, SpO2 97% on RA",
            "unstable": "BP 70/40 mmHg, HR 140/min, RR 32/min, Temp 35.5°C, SpO2 82% on NRB",
        },
    },
}


def get_specialty_config(specialty: str) -> Optional[Dict]:
    """
    Get the complete configuration for a specialty.

    Args:
        specialty: Specialty name (e.g., "Medicine", "Surgery")

    Returns:
        Complete configuration dict or None if not found
    """
    # Handle various specialty name formats
    specialty_map = {
        "Medicine": "Medicine",
        "Internal Medicine": "Medicine",
        "Surgery": "Surgery",
        "General Surgery": "Surgery",
        "Pediatrics": "Pediatrics",
        "Psychiatry": "Psychiatry",
        "Obstetrics & Gynecology": "Obstetrics & Gynecology",
        "Obstetrics and Gynecology": "Obstetrics & Gynecology",
        "OBGYN": "Obstetrics & Gynecology",
        "Emergency Medicine": "Emergency Medicine",
        "EM": "Emergency Medicine",
    }

    normalized = specialty_map.get(specialty, specialty)
    return SPECIALTY_CONFIG.get(normalized)


def get_specialty_demographics(specialty: str) -> Dict:
    """
    Get demographic configuration for generating patient scenarios.

    Returns age range, setting, and risk factors appropriate for specialty.
    """
    config = get_specialty_config(specialty)
    if not config:
        return {}

    demographics = config.get("demographics", {})

    # Select weighted age range
    age_ranges = demographics.get("age_ranges", [])
    if age_ranges:
        weights = [ar.get("weight", 1.0) for ar in age_ranges]
        selected_age = random.choices(age_ranges, weights=weights, k=1)[0]
    else:
        selected_age = {"range": "45-65 years", "context": "general"}

    # Select random setting and risk factors
    settings = demographics.get("common_settings", ["clinic"])
    risk_factors = demographics.get("risk_factors", [])

    return {
        "age_range": selected_age["range"],
        "age_context": selected_age.get("context", ""),
        "setting": random.choice(settings),
        "risk_factors": random.sample(risk_factors, min(2, len(risk_factors))) if risk_factors else [],
    }


def get_specialty_prompt_context(specialty: str, question_type: str = "diagnosis") -> str:
    """
    Get specialty-specific prompt context for injection into generation steps.

    Args:
        specialty: Medical specialty
        question_type: Type of question (diagnosis, next_step, mechanism, etc.)

    Returns:
        Formatted string with specialty-specific guidance
    """
    config = get_specialty_config(specialty)
    if not config:
        return ""

    demographics = get_specialty_demographics(specialty)
    presentation_style = config.get("presentation_style", "")
    high_yield = config.get("high_yield_concepts", [])
    distractors = config.get("distractor_patterns", [])

    # Select relevant high-yield concepts
    selected_concepts = random.sample(high_yield, min(3, len(high_yield)))

    context = f"""
SPECIALTY-SPECIFIC GUIDANCE FOR {config.get('full_name', specialty).upper()}:

PATIENT DEMOGRAPHICS:
- Typical age range: {demographics.get('age_range', 'adult')} ({demographics.get('age_context', '')})
- Clinical setting: {demographics.get('setting', 'clinic')}
- Common risk factors: {', '.join(demographics.get('risk_factors', []))}

PRESENTATION STYLE:
{presentation_style}

HIGH-YIELD CONCEPTS TO CONSIDER:
{chr(10).join(f'- {concept}' for concept in selected_concepts)}

COMMON DISTRACTOR PATTERNS FOR THIS SPECIALTY:
{chr(10).join(f'- {d}' for d in distractors[:3])}
"""
    return context


def get_specialty_validation_rules(specialty: str) -> List[str]:
    """
    Get specialty-specific validation rules for quality checking.

    Returns list of rules that must be checked for this specialty.
    """
    config = get_specialty_config(specialty)
    if not config:
        return []

    return config.get("validation_rules", [])


def get_specialty_vitals(specialty: str, stable: bool = True) -> str:
    """
    Get typical vital signs for a specialty presentation.

    Args:
        specialty: Medical specialty
        stable: If True, returns stable vitals; if False, returns unstable

    Returns:
        Formatted vital signs string
    """
    config = get_specialty_config(specialty)
    if not config:
        return "BP 120/80 mmHg, HR 78/min, RR 16/min, Temp 37.0°C, SpO2 98% on room air"

    vitals = config.get("typical_vitals", {})

    if stable:
        # Find any key containing 'stable'
        for key, value in vitals.items():
            if "stable" in key.lower():
                return value
        return vitals.get("stable", "BP 120/80 mmHg, HR 78/min, RR 16/min, Temp 37.0°C")
    else:
        # Find any key containing 'unstable'
        for key, value in vitals.items():
            if "unstable" in key.lower() or "withdrawal" in key.lower() or "preeclampsia" in key.lower():
                return value
        return vitals.get("unstable", "BP 85/50 mmHg, HR 120/min, RR 28/min, Temp 39.0°C")
