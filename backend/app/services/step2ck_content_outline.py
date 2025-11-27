"""
USMLE Step 2 CK Content Outline
Based on official NBME blueprint and high-yield topics from First Aid

This defines the exact distribution and topics tested on Step 2 CK
"""

# Official USMLE Step 2 CK Discipline Distribution (from USMLE.org)
DISCIPLINE_DISTRIBUTION = {
    "Medicine": 60,  # 55-65% (using midpoint)
    "Surgery": 25,  # 20-30%
    "Pediatrics": 22,  # 17-27%
    "Obstetrics & Gynecology": 15,  # 10-20%
    "Psychiatry": 12,  # 10-15%
}

# Physician Task/Competency Distribution (from USMLE.org)
COMPETENCY_DISTRIBUTION = {
    "diagnosis": 18,  # 16-20% (Patient Care: Diagnosis)
    "laboratory_diagnostic": 15,  # 13-17% (Lab/Diagnostic Studies)
    "mixed_management": 14,  # 12-16% (Mixed Management)
    "pharmacotherapy": 10,  # 8-12% (Pharmacotherapy)
    "clinical_interventions": 8,  # 6-10% (Clinical Interventions)
    "prognosis": 7,  # 5-9% (Prognosis/Outcome)
    "prevention": 7,  # 5-10% (Health Maintenance/Disease Prevention)
    "professionalism": 6,  # 5-7% (Professionalism)
    "systems_based": 6,  # 5-7% (Systems-based Practice & Patient Safety)
    "practice_improvement": 4,  # 3-5% (Practice-based Learning)
}

# High-yield topics by specialty (from First Aid + NBME outline)
HIGH_YIELD_TOPICS = {
    "Internal Medicine": {
        "Cardiology": [
            "Acute coronary syndrome (STEMI, NSTEMI, unstable angina)",
            "Heart failure (systolic vs diastolic, acute decompensation)",
            "Atrial fibrillation management (rate vs rhythm control, anticoagulation)",
            "Hypertension management (JNC guidelines, resistant hypertension)",
            "Valvular heart disease (AS, AR, MS, MR - timing of surgery)",
            "Aortic dissection",
            "Pericarditis and cardiac tamponade",
            "Infective endocarditis (Duke criteria, prophylaxis)",
        ],
        "Pulmonology": [
            "COPD exacerbation management",
            "Asthma (step therapy, acute exacerbation)",
            "Pneumonia (CAP, HAP, VAP - empiric antibiotics)",
            "Pulmonary embolism (Wells criteria, diagnostic algorithm)",
            "Pleural effusion (Light's criteria, thoracentesis)",
            "Lung cancer screening and diagnosis",
            "Interstitial lung disease",
            "Sleep apnea",
        ],
        "Gastroenterology": [
            "GI bleeding (upper vs lower, management priorities)",
            "Inflammatory bowel disease (UC vs Crohn, complications)",
            "Cirrhosis complications (ascites, SBP, hepatic encephalopathy, varices)",
            "Acute pancreatitis (Ranson criteria, management)",
            "Cholecystitis and choledocholithiasis",
            "Diverticulitis",
            "Hepatitis (viral hepatitis A-E, alcoholic, drug-induced)",
            "Colorectal cancer screening",
        ],
        "Nephrology": [
            "Acute kidney injury (prerenal, intrinsic, postrenal)",
            "Chronic kidney disease (staging, complications, anemia management)",
            "Electrolyte disorders (hyponatremia, hyperkalemia, hypercalcemia)",
            "Acid-base disorders (metabolic vs respiratory, anion gap)",
            "Nephrotic vs nephritic syndrome",
            "Urinary tract infections",
        ],
        "Endocrinology": [
            "Diabetes mellitus (type 1 vs 2, complications, target HbA1c)",
            "Diabetic ketoacidosis and hyperosmolar hyperglycemic state",
            "Thyroid disorders (hypo/hyperthyroidism, thyroid nodules)",
            "Adrenal disorders (Addison's, Cushing's, pheochromocytoma)",
            "Hypoglycemia evaluation",
        ],
        "Hematology": [
            "Anemia workup (microcytic, normocytic, macrocytic)",
            "Transfusion medicine and reactions",
            "Anticoagulation (warfarin, DOACs, heparin)",
            "Thrombocytopenia (ITP, TTP, HIT)",
            "Venous thromboembolism prophylaxis and treatment",
        ],
        "Infectious Disease": [
            "HIV/AIDS (opportunistic infections, antiretroviral therapy)",
            "Sepsis and septic shock (SIRS criteria, early goal-directed therapy)",
            "Meningitis (bacterial, viral, fungal)",
            "Endocarditis",
            "Skin and soft tissue infections (cellulitis, necrotizing fasciitis)",
            "Tuberculosis (latent vs active, treatment)",
        ],
        "Rheumatology": [
            "Rheumatoid arthritis",
            "Systemic lupus erythematosus",
            "Gout and pseudogout",
            "Giant cell arteritis and polymyalgia rheumatica",
            "Septic arthritis",
        ],
    },
    "Surgery": {
        "General Surgery": [
            "Acute abdomen (appendicitis, bowel obstruction, perforation)",
            "Hernias (inguinal, femoral, incarcerated)",
            "Breast masses and cancer",
            "Thyroid nodules and cancer",
            "Traumatic injuries (ATLS protocols)",
        ],
        "Vascular": [
            "Peripheral arterial disease",
            "Aortic aneurysm (AAA screening, rupture)",
            "Venous insufficiency and DVT",
        ],
        "Surgical Complications": [
            "Postoperative fever (5 W's)",
            "Wound infections",
            "Anastomotic leak",
            "Ileus vs bowel obstruction",
        ],
    },
    "Pediatrics": {
        "Well-child Care": [
            "Developmental milestones",
            "Vaccination schedule",
            "Growth charts and failure to thrive",
            "Newborn screening",
        ],
        "Pediatric Emergencies": [
            "Febrile seizures",
            "Croup vs epiglottitis",
            "Bronchiolitis (RSV)",
            "Intussusception",
            "Appendicitis",
        ],
        "Infectious Diseases": [
            "Kawasaki disease",
            "Meningitis",
            "Common childhood infections (measles, mumps, rubella, varicella)",
        ],
        "Chronic Conditions": [
            "Asthma management in children",
            "ADHD",
            "Autism spectrum disorder",
            "Congenital heart disease",
        ],
    },
    "Psychiatry": {
        "Mood Disorders": [
            "Major depressive disorder (diagnosis, treatment algorithm)",
            "Bipolar disorder (type I vs II, mood stabilizers)",
            "Suicide risk assessment",
        ],
        "Psychotic Disorders": [
            "Schizophrenia (diagnosis, antipsychotics, side effects)",
            "Brief psychotic disorder",
        ],
        "Anxiety Disorders": [
            "Generalized anxiety disorder",
            "Panic disorder",
            "PTSD",
            "OCD",
        ],
        "Substance Use": [
            "Alcohol withdrawal (CIWA scale, benzodiazepines)",
            "Opioid overdose and withdrawal",
            "Stimulant intoxication",
        ],
        "Other": [
            "Eating disorders (anorexia vs bulimia)",
            "Personality disorders",
            "Capacity and informed consent",
        ],
    },
    "Obstetrics & Gynecology": {
        "Obstetrics": [
            "Prenatal care and screening",
            "Hypertensive disorders of pregnancy (preeclampsia, eclampsia)",
            "Gestational diabetes",
            "Preterm labor and PROM",
            "Postpartum hemorrhage",
            "Ectopic pregnancy",
        ],
        "Gynecology": [
            "Abnormal uterine bleeding",
            "Pelvic inflammatory disease",
            "Ovarian masses and cancer",
            "Contraception methods",
            "Menopause management",
            "Sexual assault evaluation",
        ],
    },
    "Emergency Medicine": {
        "Trauma": [
            "ATLS protocols and primary survey",
            "Head trauma and intracranial hemorrhage",
            "Chest trauma (pneumothorax, hemothorax)",
            "Abdominal trauma",
        ],
        "Toxicology": [
            "Acetaminophen overdose",
            "Salicylate toxicity",
            "Carbon monoxide poisoning",
            "Toxidromes",
        ],
        "Environmental": [
            "Heat stroke",
            "Hypothermia",
            "Near-drowning",
        ],
    },
}

# Question type distribution (NBME Gold Book templates)
QUESTION_TYPES = {
    "diagnosis": 0.35,          # 35% - "Most likely diagnosis?"
    "next_step": 0.30,          # 30% - "Next best step in management?"
    "mechanism": 0.10,          # 10% - "Most likely mechanism?"
    "risk_factor": 0.08,        # 8% - "Strongest predisposing factor?"
    "complication": 0.07,       # 7% - "Most likely complication?"
    "prevention": 0.05,         # 5% - "Best way to prevent?"
    "prognosis": 0.05,          # 5% - "Most likely outcome?"
}

# Clinical setting distribution
CLINICAL_SETTINGS = [
    "Emergency department",
    "Outpatient clinic",
    "Hospital ward",
    "ICU",
    "Operating room",
    "Labor and delivery",
    "Pediatric clinic",
]

# Common test-taking traps (from NBME Gold Book)
COMMON_DISTRACTORS = [
    "Premature diagnosis before adequate workup",
    "Outdated treatment guidelines",
    "Overtreatment of stable conditions",
    "Missing urgent/emergent conditions",
    "Confusing similar diseases",
]


def get_weighted_specialty():
    """Select specialty based on official USMLE discipline distribution"""
    import random
    specialties = list(DISCIPLINE_DISTRIBUTION.keys())
    weights = list(DISCIPLINE_DISTRIBUTION.values())
    return random.choices(specialties, weights=weights, k=1)[0]


def get_high_yield_topic(specialty):
    """Select high-yield topic from specialty (maps to First Aid topics)"""
    import random
    # Map USMLE disciplines to our high-yield topics
    # Must match specialty names from massive_pool.py SPECIALTIES list
    specialty_map = {
        # Direct matches
        "Internal Medicine": "Internal Medicine",
        "Surgery": "Surgery",
        "Pediatrics": "Pediatrics",
        "Psychiatry": "Psychiatry",
        "Emergency Medicine": "Emergency Medicine",
        # Handle "and" vs "&" mismatch
        "Obstetrics and Gynecology": "Obstetrics & Gynecology",
        "Obstetrics & Gynecology": "Obstetrics & Gynecology",
        # Legacy mappings
        "Medicine": "Internal Medicine",
        # Fallback specialties to Internal Medicine (common primary care topics)
        "Family Medicine": "Internal Medicine",
        "Preventive Medicine": "Internal Medicine",
    }

    mapped_specialty = specialty_map.get(specialty, "Internal Medicine")
    if mapped_specialty not in HIGH_YIELD_TOPICS:
        print(f"[ContentOutline] WARNING: No topics for mapped specialty '{mapped_specialty}' (from '{specialty}')")
        return None

    category = random.choice(list(HIGH_YIELD_TOPICS[mapped_specialty].keys()))
    topic = random.choice(HIGH_YIELD_TOPICS[mapped_specialty][category])
    return topic


def get_question_type():
    """Select question competency based on official USMLE distribution"""
    import random
    competencies = list(COMPETENCY_DISTRIBUTION.keys())
    weights = list(COMPETENCY_DISTRIBUTION.values())
    return random.choices(competencies, weights=weights, k=1)[0]
