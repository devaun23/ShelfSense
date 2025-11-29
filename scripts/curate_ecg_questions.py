#!/usr/bin/env python3
"""
ECG Question Curation Script

Creates 50 high-yield ECG questions for Internal Medicine shelf exam.
Uses PhysioNet PTB-XL dataset (FREE, open access).

ECG Distribution (based on IM Shelf exam weighting):
- STEMI patterns (15): Anterior, Inferior, Lateral
- AFib/Flutter (10): Various presentations
- Heart blocks (8): 1st, 2nd Mobitz I/II, 3rd degree
- LVH (7): With strain, without
- VT/VF (5): Monomorphic, polymorphic
- Other (5): WPW, Brugada, Long QT, PE, Hyperkalemia

Usage:
    python scripts/curate_ecg_questions.py
    python scripts/curate_ecg_questions.py --dry-run  # Preview only
"""

import argparse
import json
import logging
import sys
import uuid
from pathlib import Path
from datetime import datetime

# Add backend to path
backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from dotenv import load_dotenv
env_file = backend_path / ".env"
if env_file.exists():
    load_dotenv(env_file)

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# PhysioNet PTB-XL Dataset Base URL
# Using publicly accessible ECG images from PhysioNet
PHYSIONET_BASE = "https://physionet.org/files/ptb-xl/1.0.3"

# High-yield ECG questions for IM Shelf
# Each includes: diagnosis, clinical vignette, ECG description, and answer choices
ECG_QUESTIONS = [
    # === STEMI (15 questions) ===
    {
        "diagnosis": "Anterior STEMI",
        "vignette": "A 62-year-old man with hypertension and diabetes presents with crushing substernal chest pain radiating to his left arm for 45 minutes. He is diaphoretic and appears anxious. Vital signs: BP 100/70 mmHg, HR 95 bpm, RR 22/min. An ECG is obtained.\n\nThe ECG shows ST-segment elevation in leads V1-V4 with reciprocal ST depression in leads II, III, and aVF.\n\nWhat is the most likely diagnosis?",
        "choices": ["A. Anterior STEMI", "B. Inferior STEMI", "C. Pericarditis", "D. Pulmonary embolism", "E. Aortic dissection"],
        "answer_key": "A",
        "explanation": "ST elevation in V1-V4 indicates anterior wall involvement (LAD territory). Reciprocal changes in inferior leads support acute MI.",
        "image_type": "ecg",
        "ecg_pattern": "anterior_stemi"
    },
    {
        "diagnosis": "Inferior STEMI",
        "vignette": "A 58-year-old woman presents with nausea, vomiting, and epigastric discomfort for 2 hours. She has a history of smoking. Vital signs: BP 90/60 mmHg, HR 52 bpm. An ECG is obtained.\n\nThe ECG shows ST-segment elevation in leads II, III, and aVF with ST depression in leads I and aVL.\n\nWhat is the next best step in management?",
        "choices": ["A. Administer aspirin and activate cardiac catheterization lab", "B. Start IV fluids and repeat ECG in 6 hours", "C. Obtain CT scan of abdomen", "D. Administer proton pump inhibitor", "E. Perform upper endoscopy"],
        "answer_key": "A",
        "explanation": "Inferior STEMI (RCA territory) with hypotension and bradycardia suggests right ventricular involvement. Immediate reperfusion is critical.",
        "image_type": "ecg",
        "ecg_pattern": "inferior_stemi"
    },
    {
        "diagnosis": "Lateral STEMI",
        "vignette": "A 55-year-old man with hyperlipidemia presents with severe chest pressure for 1 hour. An ECG shows ST elevation in leads I, aVL, V5, and V6.\n\nWhich coronary artery is most likely occluded?",
        "choices": ["A. Left circumflex artery", "B. Right coronary artery", "C. Left anterior descending artery", "D. Posterior descending artery", "E. Left main coronary artery"],
        "answer_key": "A",
        "explanation": "Lateral wall involvement (I, aVL, V5-V6) typically indicates left circumflex artery occlusion.",
        "image_type": "ecg",
        "ecg_pattern": "lateral_stemi"
    },
    {
        "diagnosis": "Posterior STEMI",
        "vignette": "A 60-year-old man presents with chest pain. Standard 12-lead ECG shows ST depression in V1-V3 with tall R waves. Posterior leads (V7-V9) show ST elevation.\n\nWhat is the diagnosis?",
        "choices": ["A. Posterior STEMI", "B. Anterior NSTEMI", "C. Right ventricular MI", "D. Prinzmetal angina", "E. Hypertrophic cardiomyopathy"],
        "answer_key": "A",
        "explanation": "ST depression in V1-V3 with tall R waves is the mirror image of posterior ST elevation. Posterior leads confirm the diagnosis.",
        "image_type": "ecg",
        "ecg_pattern": "posterior_stemi"
    },
    {
        "diagnosis": "STEMI with RBBB",
        "vignette": "A 70-year-old man with prior MI presents with chest pain. ECG shows new ST elevation in V1-V4 with a QRS duration of 140 ms and rsR' pattern in V1.\n\nWhat finding indicates acute STEMI despite the bundle branch block?",
        "choices": ["A. Concordant ST elevation >1mm in leads with positive QRS", "B. Any ST changes in precordial leads", "C. QRS duration >120ms", "D. Presence of Q waves", "E. T wave inversions"],
        "answer_key": "A",
        "explanation": "Sgarbossa criteria: concordant ST elevation (same direction as QRS) strongly suggests STEMI in presence of RBBB or LBBB.",
        "image_type": "ecg",
        "ecg_pattern": "stemi_rbbb"
    },
    # Additional STEMI patterns
    {
        "diagnosis": "Anterolateral STEMI",
        "vignette": "A 65-year-old diabetic man presents with 30 minutes of substernal chest pressure, diaphoresis, and shortness of breath. ECG shows ST elevation in leads V2-V6, I, and aVL.\n\nThis ECG pattern is most consistent with occlusion of which vessel?",
        "choices": ["A. Proximal LAD before first diagonal", "B. RCA", "C. Distal LAD", "D. First obtuse marginal", "E. Ramus intermedius"],
        "answer_key": "A",
        "explanation": "Extensive anterolateral involvement suggests proximal LAD occlusion before the first diagonal branch, causing widespread anterior and lateral changes.",
        "image_type": "ecg",
        "ecg_pattern": "anterolateral_stemi"
    },
    {
        "diagnosis": "Inferior STEMI with RV involvement",
        "vignette": "A 59-year-old man presents with chest pain. ECG shows ST elevation in II, III, aVF, and right-sided lead V4R. BP is 85/50 mmHg.\n\nWhich intervention should be AVOIDED?",
        "choices": ["A. Nitroglycerin", "B. Aspirin", "C. Heparin", "D. Oxygen", "E. Morphine"],
        "answer_key": "A",
        "explanation": "RV infarction causes preload-dependent hypotension. Nitrates reduce preload and can cause severe hypotension.",
        "image_type": "ecg",
        "ecg_pattern": "inferior_stemi_rv"
    },
    {
        "diagnosis": "Wellens syndrome",
        "vignette": "A 52-year-old woman presents with resolved chest pain. She is pain-free and hemodynamically stable. ECG shows biphasic T waves in V2-V3.\n\nWhat is the most appropriate management?",
        "choices": ["A. Urgent coronary angiography", "B. Exercise stress test", "C. Serial troponins and discharge if negative", "D. CT coronary angiography", "E. Echocardiogram"],
        "answer_key": "A",
        "explanation": "Wellens syndrome indicates critical proximal LAD stenosis. Stress testing is contraindicated as it may precipitate MI.",
        "image_type": "ecg",
        "ecg_pattern": "wellens"
    },
    {
        "diagnosis": "De Winter T waves",
        "vignette": "A 48-year-old man presents with ongoing chest pain. ECG shows ST depression with upsloping to tall, symmetric T waves in V1-V6. No ST elevation is present.\n\nThis pattern is equivalent to which condition?",
        "choices": ["A. Anterior STEMI", "B. Posterior STEMI", "C. Unstable angina", "D. Pericarditis", "E. Takotsubo cardiomyopathy"],
        "answer_key": "A",
        "explanation": "De Winter T waves are a STEMI equivalent indicating proximal LAD occlusion. Requires emergent catheterization.",
        "image_type": "ecg",
        "ecg_pattern": "de_winter"
    },
    {
        "diagnosis": "Acute anteroseptal STEMI",
        "vignette": "A 67-year-old man presents with severe chest pain for 20 minutes. ECG shows ST elevation in V1-V3 with Q waves beginning to form.\n\nWhat is the time window for optimal benefit from primary PCI?",
        "choices": ["A. Within 90 minutes of first medical contact", "B. Within 6 hours of symptom onset", "C. Within 24 hours", "D. Within 48 hours", "E. Anytime within the first week"],
        "answer_key": "A",
        "explanation": "Door-to-balloon time should be <90 minutes. Q wave formation indicates ongoing necrosis emphasizing urgency.",
        "image_type": "ecg",
        "ecg_pattern": "anteroseptal_stemi"
    },
    {
        "diagnosis": "High lateral STEMI",
        "vignette": "A 54-year-old woman presents with chest and left shoulder pain. Standard ECG shows ST elevation only in leads I and aVL with reciprocal depression in III.\n\nWhat additional leads might show ST elevation?",
        "choices": ["A. V7-V9 (posterior leads)", "B. V1-V2", "C. Right-sided leads", "D. Lewis leads", "E. This is the complete picture"],
        "answer_key": "E",
        "explanation": "High lateral STEMI may only show changes in I and aVL. The circumflex marginal branch supplies this limited territory.",
        "image_type": "ecg",
        "ecg_pattern": "high_lateral_stemi"
    },
    {
        "diagnosis": "Inferior STEMI vs Pericarditis",
        "vignette": "A 45-year-old man presents with sharp chest pain worse with inspiration. ECG shows ST elevation in II, III, aVF and also in V5-V6, I, aVL without reciprocal changes.\n\nWhich feature best distinguishes pericarditis from inferior STEMI?",
        "choices": ["A. Diffuse ST elevation without reciprocal changes", "B. ST elevation in inferior leads", "C. Presence of chest pain", "D. Elevated troponin", "E. Tachycardia"],
        "answer_key": "A",
        "explanation": "Pericarditis shows diffuse ST elevation (except aVR) without reciprocal depression, unlike regional STEMI patterns.",
        "image_type": "ecg",
        "ecg_pattern": "pericarditis_vs_stemi"
    },
    {
        "diagnosis": "STEMI with complete heart block",
        "vignette": "A 72-year-old man presents with chest pain and near-syncope. ECG shows ST elevation in II, III, aVF with complete AV dissociation. Ventricular rate is 35 bpm.\n\nWhat is the next step?",
        "choices": ["A. Transcutaneous pacing and emergent PCI", "B. Atropine alone", "C. Observation", "D. Thrombolytics", "E. Permanent pacemaker placement"],
        "answer_key": "A",
        "explanation": "Inferior STEMI with complete heart block requires pacing support and emergent revascularization.",
        "image_type": "ecg",
        "ecg_pattern": "stemi_chb"
    },
    {
        "diagnosis": "Evolving STEMI",
        "vignette": "A 63-year-old man had chest pain 6 hours ago that has since resolved. ECG shows Q waves in V1-V4 with T wave inversions but no ST elevation.\n\nWhat does this pattern represent?",
        "choices": ["A. Completed anterior MI in evolution", "B. Acute anterior STEMI", "C. Unstable angina", "D. Old anterior MI", "E. Normal variant"],
        "answer_key": "A",
        "explanation": "Q waves with T inversions after resolved ST elevation represent an evolving/completed MI. Timing suggests recent event.",
        "image_type": "ecg",
        "ecg_pattern": "evolving_mi"
    },
    {
        "diagnosis": "STEMI in young patient",
        "vignette": "A 32-year-old man with cocaine use presents with severe chest pain. ECG shows ST elevation in V1-V4. Troponin is elevated.\n\nWhat is the preferred initial management?",
        "choices": ["A. Benzodiazepines and coronary angiography", "B. Beta-blockers", "C. Thrombolytics", "D. Aspirin only and observation", "E. Discharge with follow-up"],
        "answer_key": "A",
        "explanation": "Cocaine-induced MI requires anxiolysis and angiography. Beta-blockers are relatively contraindicated due to unopposed alpha stimulation.",
        "image_type": "ecg",
        "ecg_pattern": "cocaine_mi"
    },

    # === ATRIAL FIBRILLATION/FLUTTER (10 questions) ===
    {
        "diagnosis": "Atrial fibrillation with RVR",
        "vignette": "A 68-year-old woman with hypertension presents with palpitations for 2 days. Vital signs: HR 142 bpm, irregularly irregular. ECG shows no discernible P waves with an irregularly irregular ventricular response.\n\nWhat is the CHA2DS2-VASc score and recommended anticoagulation?",
        "choices": ["A. Score 3, recommend anticoagulation", "B. Score 1, aspirin only", "C. Score 0, no anticoagulation", "D. Score 2, consider anticoagulation", "E. Anticoagulation not indicated for new-onset AF"],
        "answer_key": "A",
        "explanation": "Age >65 (1) + female (1) + hypertension (1) = 3. Score >=2 warrants anticoagulation.",
        "image_type": "ecg",
        "ecg_pattern": "afib_rvr"
    },
    {
        "diagnosis": "Atrial flutter",
        "vignette": "A 72-year-old man presents with fatigue. ECG shows a regular ventricular rate of 150 bpm with sawtooth flutter waves best seen in leads II, III, and aVF.\n\nWhat is the typical atrial rate in typical atrial flutter?",
        "choices": ["A. 300 bpm", "B. 150 bpm", "C. 100 bpm", "D. 200 bpm", "E. 400 bpm"],
        "answer_key": "A",
        "explanation": "Typical flutter has atrial rate ~300 bpm. With 2:1 AV block (most common), ventricular rate is 150 bpm.",
        "image_type": "ecg",
        "ecg_pattern": "aflutter"
    },
    {
        "diagnosis": "Afib with slow ventricular response",
        "vignette": "A 78-year-old man on metoprolol presents with fatigue. HR is 45 bpm, irregularly irregular. ECG shows atrial fibrillation with slow ventricular response.\n\nWhat is the most likely cause of the slow rate?",
        "choices": ["A. Beta-blocker effect", "B. Hypothyroidism", "C. Sick sinus syndrome", "D. Complete heart block", "E. Digoxin toxicity"],
        "answer_key": "A",
        "explanation": "Beta-blockers slow AV conduction, causing slow ventricular response in AFib. Always consider medication effect first.",
        "image_type": "ecg",
        "ecg_pattern": "afib_svr"
    },
    {
        "diagnosis": "New-onset atrial fibrillation",
        "vignette": "A 55-year-old man presents with palpitations for 12 hours. He is hemodynamically stable. ECG confirms atrial fibrillation at 130 bpm. TTE shows no thrombus.\n\nWhat is the preferred strategy?",
        "choices": ["A. Rate control with diltiazem", "B. Immediate cardioversion", "C. Amiodarone loading", "D. Discharge with rate control", "E. Ablation referral"],
        "answer_key": "A",
        "explanation": "For stable new-onset AF, rate control is first-line. Cardioversion can be considered if onset <48 hours or after TEE.",
        "image_type": "ecg",
        "ecg_pattern": "new_afib"
    },
    {
        "diagnosis": "Atrial fibrillation with WPW",
        "vignette": "A 35-year-old man presents with palpitations and HR 200 bpm, irregularly irregular. ECG shows wide, bizarre QRS complexes with varying morphology.\n\nWhich medication is CONTRAINDICATED?",
        "choices": ["A. Diltiazem", "B. Procainamide", "C. Ibutilide", "D. Amiodarone", "E. Electrical cardioversion"],
        "answer_key": "A",
        "explanation": "AV nodal blockers (diltiazem, verapamil, digoxin) in pre-excited AF can accelerate conduction via accessory pathway causing VF.",
        "image_type": "ecg",
        "ecg_pattern": "afib_wpw"
    },
    {
        "diagnosis": "Lone atrial fibrillation",
        "vignette": "A 42-year-old healthy marathon runner presents with paroxysmal palpitations. ECG during symptoms shows atrial fibrillation. TTE is normal. He has no comorbidities.\n\nWhat is the CHA2DS2-VASc score?",
        "choices": ["A. 0", "B. 1", "C. 2", "D. 3", "E. Score cannot be calculated"],
        "answer_key": "A",
        "explanation": "Young male with no risk factors has score of 0. Anticoagulation not routinely recommended.",
        "image_type": "ecg",
        "ecg_pattern": "lone_afib"
    },
    {
        "diagnosis": "Atrial flutter with variable block",
        "vignette": "A 70-year-old woman presents with palpitations. ECG shows sawtooth waves at 300/min with ventricular rates alternating between 75 and 150 bpm.\n\nWhat is the mechanism?",
        "choices": ["A. Variable AV block (2:1 and 4:1)", "B. Sick sinus syndrome", "C. Dual AV nodal physiology", "D. Accessory pathway", "E. Atrial fibrillation"],
        "answer_key": "A",
        "explanation": "Atrial flutter with variable AV block causes irregular ventricular rates. The flutter rate remains constant at ~300 bpm.",
        "image_type": "ecg",
        "ecg_pattern": "aflutter_variable"
    },
    {
        "diagnosis": "Rate control in AFib",
        "vignette": "A 75-year-old man with heart failure (EF 35%) has permanent atrial fibrillation with rate of 110 bpm at rest.\n\nWhich agent is preferred for rate control?",
        "choices": ["A. Metoprolol", "B. Diltiazem", "C. Verapamil", "D. Flecainide", "E. Sotalol"],
        "answer_key": "A",
        "explanation": "Beta-blockers are preferred in HFrEF. Non-dihydropyridine CCBs (diltiazem, verapamil) have negative inotropy and are avoided.",
        "image_type": "ecg",
        "ecg_pattern": "afib_hf"
    },
    {
        "diagnosis": "Cardioversion of AFib",
        "vignette": "A 60-year-old woman presents with AF for 3 days. She is on warfarin with INR 2.5 for the past 4 weeks.\n\nCan she undergo cardioversion without TEE?",
        "choices": ["A. Yes, with adequate anticoagulation >3 weeks", "B. No, TEE is always required", "C. Only if onset <24 hours", "D. Only with direct oral anticoagulants", "E. Cardioversion is contraindicated after 48 hours"],
        "answer_key": "A",
        "explanation": "With documented therapeutic anticoagulation for >3 weeks, cardioversion can proceed without TEE.",
        "image_type": "ecg",
        "ecg_pattern": "afib_cardioversion"
    },
    {
        "diagnosis": "Tachy-brady syndrome",
        "vignette": "An 80-year-old woman presents with syncope. Monitor shows alternating atrial fibrillation with rates of 140 bpm and sinus pauses up to 5 seconds.\n\nWhat is the definitive treatment?",
        "choices": ["A. Permanent pacemaker with rate control medications", "B. Rate control alone", "C. Ablation alone", "D. No treatment needed", "E. Cardioversion"],
        "answer_key": "A",
        "explanation": "Tachy-brady syndrome requires pacemaker for pauses, then rate control medications can be added safely.",
        "image_type": "ecg",
        "ecg_pattern": "tachy_brady"
    },

    # === HEART BLOCKS (8 questions) ===
    {
        "diagnosis": "First-degree AV block",
        "vignette": "A 45-year-old man has an ECG showing PR interval of 240 ms. He is asymptomatic with no cardiac history.\n\nWhat is the appropriate management?",
        "choices": ["A. No treatment needed", "B. Pacemaker implantation", "C. Discontinue all medications", "D. Cardiac catheterization", "E. EP study"],
        "answer_key": "A",
        "explanation": "Isolated first-degree AV block (PR >200ms) in asymptomatic patients requires no treatment.",
        "image_type": "ecg",
        "ecg_pattern": "first_degree_avb"
    },
    {
        "diagnosis": "Mobitz I (Wenckebach)",
        "vignette": "A 60-year-old man post-inferior MI has ECG showing progressive PR prolongation followed by a dropped beat, then the cycle repeats.\n\nWhat is the typical prognosis?",
        "choices": ["A. Usually benign, resolves spontaneously", "B. Requires permanent pacemaker", "C. High risk of complete heart block", "D. Indicates anterior MI", "E. Requires emergent treatment"],
        "answer_key": "A",
        "explanation": "Mobitz I after inferior MI is usually at AV node level and often resolves. It rarely progresses to complete block.",
        "image_type": "ecg",
        "ecg_pattern": "mobitz_i"
    },
    {
        "diagnosis": "Mobitz II",
        "vignette": "A 75-year-old man presents with presyncope. ECG shows constant PR intervals with intermittent dropped QRS complexes. QRS is widened.\n\nWhat is indicated?",
        "choices": ["A. Permanent pacemaker", "B. Observation only", "C. Atropine trial", "D. Beta-blocker", "E. Calcium channel blocker"],
        "answer_key": "A",
        "explanation": "Mobitz II indicates infra-nodal disease with high risk of complete block. Permanent pacemaker is indicated.",
        "image_type": "ecg",
        "ecg_pattern": "mobitz_ii"
    },
    {
        "diagnosis": "Complete heart block",
        "vignette": "An 82-year-old woman presents with syncope. ECG shows regular P waves at 80/min and regular QRS at 35/min with no relationship between them.\n\nWhat is the escape rhythm likely originating from?",
        "choices": ["A. Ventricle", "B. AV junction", "C. Atrium", "D. SA node", "E. Purkinje fibers"],
        "answer_key": "A",
        "explanation": "Rate <40 with wide QRS suggests ventricular escape. Junctional escape would be 40-60 bpm with narrow QRS.",
        "image_type": "ecg",
        "ecg_pattern": "complete_hb"
    },
    {
        "diagnosis": "2:1 AV block",
        "vignette": "A 70-year-old man has ECG showing every other P wave followed by QRS, with constant PR intervals. The rhythm cannot be classified as Mobitz I or II.\n\nHow can you differentiate?",
        "choices": ["A. Look at QRS width and clinical context", "B. It is always Mobitz I", "C. It is always Mobitz II", "D. Perform carotid massage", "E. The distinction is not clinically important"],
        "answer_key": "A",
        "explanation": "2:1 block with narrow QRS suggests nodal level (Mobitz I behavior). Wide QRS suggests infra-nodal (Mobitz II behavior).",
        "image_type": "ecg",
        "ecg_pattern": "2to1_avb"
    },
    {
        "diagnosis": "High-grade AV block",
        "vignette": "A 68-year-old woman on telemetry shows 3:1 AV block intermittently progressing to 4:1 block. She has lightheadedness.\n\nWhat is the management?",
        "choices": ["A. Pacemaker implantation", "B. Observation", "C. Increase heart rate with exercise", "D. Atropine as needed", "E. Beta-blocker"],
        "answer_key": "A",
        "explanation": "High-grade AV block (multiple consecutive non-conducted P waves) is a Class I indication for pacing.",
        "image_type": "ecg",
        "ecg_pattern": "high_grade_avb"
    },
    {
        "diagnosis": "AV block with symptoms",
        "vignette": "A 72-year-old man with Mobitz I has recurrent syncope. His heart rate drops to 35 bpm during episodes.\n\nDoes he need a pacemaker?",
        "choices": ["A. Yes, symptomatic bradycardia is an indication", "B. No, Mobitz I never needs pacing", "C. Only if post-MI", "D. Only with complete block", "E. Trial of theophylline first"],
        "answer_key": "A",
        "explanation": "Symptomatic bradycardia regardless of mechanism is an indication for pacing.",
        "image_type": "ecg",
        "ecg_pattern": "symptomatic_avb"
    },
    {
        "diagnosis": "Bifascicular block",
        "vignette": "A 65-year-old man has ECG showing RBBB with left anterior fascicular block. He is asymptomatic.\n\nWhat is the risk?",
        "choices": ["A. Progression to complete heart block over years", "B. Immediate need for pacemaker", "C. High risk of sudden death", "D. No increased risk", "E. Requires ICD"],
        "answer_key": "A",
        "explanation": "Bifascicular block can progress to complete block but usually slowly. Prophylactic pacing not indicated if asymptomatic.",
        "image_type": "ecg",
        "ecg_pattern": "bifascicular"
    },

    # === LVH (7 questions) ===
    {
        "diagnosis": "LVH with strain",
        "vignette": "A 58-year-old man with long-standing hypertension has ECG showing tall R waves in V5-V6 (R in V5 = 30mm), deep S waves in V1-V2, and ST depression with T wave inversions in lateral leads.\n\nWhat do the ST-T changes indicate?",
        "choices": ["A. LVH with strain pattern (secondary repolarization changes)", "B. Acute lateral ischemia", "C. Digoxin effect", "D. Electrolyte abnormality", "E. Pericarditis"],
        "answer_key": "A",
        "explanation": "Asymmetric ST depression/T inversion opposite to QRS direction in LVH is strain pattern, not primary ischemia.",
        "image_type": "ecg",
        "ecg_pattern": "lvh_strain"
    },
    {
        "diagnosis": "LVH voltage criteria",
        "vignette": "A 50-year-old athletic man has ECG showing S in V1 + R in V5 = 38mm. No ST-T changes. He is asymptomatic.\n\nWhat Sokolow-Lyon criterion is met?",
        "choices": ["A. S V1 + R V5/V6 > 35mm", "B. R aVL > 11mm", "C. Cornell criteria", "D. Romhilt-Estes score", "E. No criteria met"],
        "answer_key": "A",
        "explanation": "Sokolow-Lyon: S in V1 + R in V5 or V6 > 35mm. This patient (38mm) meets criteria.",
        "image_type": "ecg",
        "ecg_pattern": "lvh_voltage"
    },
    {
        "diagnosis": "LVH and ischemia",
        "vignette": "A 62-year-old man with LVH on baseline ECG presents with chest pain. New ECG shows deeper ST depression in V4-V6 than baseline.\n\nHow do you assess for ischemia?",
        "choices": ["A. Compare to prior ECG for new changes", "B. ST depression in LVH excludes ischemia", "C. Troponin alone is sufficient", "D. Ignore ECG changes", "E. Immediate cath regardless"],
        "answer_key": "A",
        "explanation": "In LVH, compare to baseline ECG. New or dynamic ST-T changes suggest superimposed ischemia.",
        "image_type": "ecg",
        "ecg_pattern": "lvh_ischemia"
    },
    {
        "diagnosis": "Hypertrophic cardiomyopathy",
        "vignette": "A 25-year-old athlete has ECG showing deep narrow Q waves in lateral leads, LVH by voltage, and T wave inversions. Family history of sudden death.\n\nWhat is the most likely diagnosis?",
        "choices": ["A. Hypertrophic cardiomyopathy", "B. Prior MI", "C. WPW syndrome", "D. Athlete's heart", "E. Dilated cardiomyopathy"],
        "answer_key": "A",
        "explanation": "Deep septal Q waves (pseudo-infarct pattern), LVH, T inversions, and family history suggest HCM.",
        "image_type": "ecg",
        "ecg_pattern": "hcm"
    },
    {
        "diagnosis": "Aortic stenosis ECG",
        "vignette": "A 78-year-old man with systolic murmur has ECG showing LVH with strain pattern and left atrial abnormality.\n\nWhat valvular lesion is suggested?",
        "choices": ["A. Aortic stenosis", "B. Mitral regurgitation", "C. Aortic regurgitation", "D. Tricuspid regurgitation", "E. Pulmonary stenosis"],
        "answer_key": "A",
        "explanation": "Severe AS causes pressure overload LVH with strain. LAA occurs from elevated LV filling pressures.",
        "image_type": "ecg",
        "ecg_pattern": "as_lvh"
    },
    {
        "diagnosis": "LVH criteria comparison",
        "vignette": "A 55-year-old hypertensive woman has R wave in aVL of 13mm.\n\nWhich LVH criterion is met?",
        "choices": ["A. Cornell voltage (R aVL > 11mm in women)", "B. Sokolow-Lyon", "C. Modified Cornell", "D. Romhilt-Estes", "E. None"],
        "answer_key": "A",
        "explanation": "Cornell voltage: R in aVL > 11mm (women) or > 13mm (men).",
        "image_type": "ecg",
        "ecg_pattern": "cornell_lvh"
    },
    {
        "diagnosis": "Secondary vs primary repolarization",
        "vignette": "A patient with LVH and strain pattern develops chest pain. ECG is unchanged from baseline.\n\nWhat conclusion can be drawn?",
        "choices": ["A. Cannot rule out ischemia based on ECG alone", "B. No ischemia present", "C. Definite ischemia", "D. Need immediate cath", "E. LVH precludes MI"],
        "answer_key": "A",
        "explanation": "Unchanged ECG with LVH strain doesn't exclude ischemia. Troponins and clinical assessment are essential.",
        "image_type": "ecg",
        "ecg_pattern": "lvh_baseline"
    },

    # === VT/VF (5 questions) ===
    {
        "diagnosis": "Monomorphic VT",
        "vignette": "A 65-year-old man with prior MI presents with palpitations. BP 95/60. ECG shows wide complex tachycardia at 180 bpm with uniform QRS morphology.\n\nWhat is the treatment?",
        "choices": ["A. Synchronized cardioversion", "B. Adenosine", "C. Verapamil", "D. Observation", "E. Vagal maneuvers"],
        "answer_key": "A",
        "explanation": "Unstable monomorphic VT requires synchronized cardioversion. Adenosine/CCBs are contraindicated in VT.",
        "image_type": "ecg",
        "ecg_pattern": "mono_vt"
    },
    {
        "diagnosis": "Polymorphic VT (Torsades)",
        "vignette": "A 60-year-old woman on sotalol presents with syncope. ECG shows wide complex tachycardia with rotating QRS axis. QTc on prior ECG was 520ms.\n\nWhat is first-line treatment?",
        "choices": ["A. IV magnesium", "B. Amiodarone", "C. Lidocaine", "D. Beta-blocker", "E. Adenosine"],
        "answer_key": "A",
        "explanation": "Torsades de pointes with long QT is treated with IV magnesium, overdrive pacing, and QT-prolonging drug cessation.",
        "image_type": "ecg",
        "ecg_pattern": "torsades"
    },
    {
        "diagnosis": "VT vs SVT with aberrancy",
        "vignette": "A 70-year-old man presents with wide complex tachycardia. AV dissociation is present. There is positive concordance in precordial leads.\n\nWhat is the diagnosis?",
        "choices": ["A. Ventricular tachycardia", "B. SVT with RBBB", "C. SVT with LBBB", "D. Atrial flutter with aberrancy", "E. Cannot determine"],
        "answer_key": "A",
        "explanation": "AV dissociation and positive concordance strongly suggest VT. When in doubt, treat WCT as VT.",
        "image_type": "ecg",
        "ecg_pattern": "vt_vs_svt"
    },
    {
        "diagnosis": "Ventricular fibrillation",
        "vignette": "A 55-year-old man collapses. Monitor shows chaotic irregular rhythm with no discernible QRS complexes.\n\nWhat is immediate management?",
        "choices": ["A. Defibrillation", "B. Synchronized cardioversion", "C. Adenosine", "D. Amiodarone first", "E. Check pulse first"],
        "answer_key": "A",
        "explanation": "VF requires immediate defibrillation (unsynchronized). This is a shockable rhythm in cardiac arrest.",
        "image_type": "ecg",
        "ecg_pattern": "vfib"
    },
    {
        "diagnosis": "Brugada syndrome",
        "vignette": "A 35-year-old man with family history of sudden death has ECG showing coved ST elevation >2mm in V1-V2 with T wave inversion.\n\nWhat is the management?",
        "choices": ["A. ICD implantation if symptomatic or inducible VT", "B. Beta-blocker", "C. No treatment needed", "D. Ablation", "E. Amiodarone"],
        "answer_key": "A",
        "explanation": "Type 1 Brugada with symptoms or inducible VT warrants ICD. Medications do not prevent sudden death.",
        "image_type": "ecg",
        "ecg_pattern": "brugada"
    },

    # === OTHER (5 questions) ===
    {
        "diagnosis": "WPW syndrome",
        "vignette": "A 28-year-old man presents with palpitations. Resting ECG shows short PR interval (<120ms), delta waves, and wide QRS.\n\nWhat arrhythmia is he at risk for?",
        "choices": ["A. Orthodromic AVRT and pre-excited atrial fibrillation", "B. Atrial flutter only", "C. Ventricular fibrillation only", "D. Sinus tachycardia", "E. No increased arrhythmia risk"],
        "answer_key": "A",
        "explanation": "WPW predisposes to AVRT and dangerous pre-excited AF that can degenerate to VF.",
        "image_type": "ecg",
        "ecg_pattern": "wpw"
    },
    {
        "diagnosis": "Pulmonary embolism",
        "vignette": "A 45-year-old woman post-surgery presents with dyspnea and chest pain. ECG shows sinus tachycardia, S1Q3T3 pattern, and new RBBB.\n\nWhat is the most likely diagnosis?",
        "choices": ["A. Pulmonary embolism", "B. Acute MI", "C. Pericarditis", "D. Pneumothorax", "E. Aortic dissection"],
        "answer_key": "A",
        "explanation": "S1Q3T3 with new RBBB and sinus tachycardia is classic for PE, though nonspecific. CT angiography confirms.",
        "image_type": "ecg",
        "ecg_pattern": "pe"
    },
    {
        "diagnosis": "Hyperkalemia",
        "vignette": "A 70-year-old man with CKD presents with weakness. K+ is 7.2 mEq/L. ECG shows peaked T waves, widened QRS, and flattened P waves.\n\nWhat is the first treatment?",
        "choices": ["A. IV calcium gluconate", "B. IV insulin and glucose", "C. Sodium bicarbonate", "D. Kayexalate", "E. Dialysis"],
        "answer_key": "A",
        "explanation": "Calcium stabilizes cardiac membrane immediately. Insulin/glucose and other treatments lower K+ but take time.",
        "image_type": "ecg",
        "ecg_pattern": "hyperkalemia"
    },
    {
        "diagnosis": "Long QT syndrome",
        "vignette": "A 22-year-old woman with recurrent syncope has ECG showing QTc of 520ms. Family history of sudden death at young age.\n\nWhat is first-line treatment?",
        "choices": ["A. Beta-blocker", "B. ICD", "C. Pacemaker", "D. No treatment", "E. Calcium channel blocker"],
        "answer_key": "A",
        "explanation": "Beta-blockers are first-line for LQTS. ICD is reserved for high-risk patients or breakthrough events on therapy.",
        "image_type": "ecg",
        "ecg_pattern": "long_qt"
    },
    {
        "diagnosis": "Digoxin effect",
        "vignette": "An 80-year-old woman on digoxin has ECG showing scooped ST depression (Salvador Dali mustache), short QT, and mild PR prolongation.\n\nDoes this indicate toxicity?",
        "choices": ["A. No, this is digoxin effect, not toxicity", "B. Yes, discontinue immediately", "C. Yes, give digoxin immune fab", "D. Cannot determine from ECG", "E. Increase digoxin dose"],
        "answer_key": "A",
        "explanation": "Digoxin effect (ST scooping) is expected and not toxic. Toxicity shows arrhythmias (PAT with block, bidirectional VT).",
        "image_type": "ecg",
        "ecg_pattern": "digoxin_effect"
    },
]


def create_ecg_questions(db, dry_run: bool = False) -> int:
    """Create ECG questions in the database."""
    from app.models.models import Question

    created = 0
    for i, ecg_q in enumerate(ECG_QUESTIONS, 1):
        try:
            # Build the full vignette
            vignette = ecg_q["vignette"]

            question = Question(
                id=str(uuid.uuid4()),
                vignette=vignette,
                choices=ecg_q["choices"],
                answer_key=ecg_q["answer_key"],
                explanation={"brief": ecg_q["explanation"]},
                specialty="internal_medicine",
                difficulty_level="medium",
                source_type="ai_generated_ecg",
                content_status="active",
                image_type=ecg_q["image_type"],
                image_url=None,  # Will be populated with actual PhysioNet URLs later
                extra_data={
                    "diagnosis": ecg_q["diagnosis"],
                    "ecg_pattern": ecg_q["ecg_pattern"],
                    "system": "cardiovascular",
                    "task": "diagnosis",
                    "generator": "ecg_curation_script"
                }
            )

            if not dry_run:
                db.add(question)
                created += 1
                logger.info(f"[{i}/{len(ECG_QUESTIONS)}] Created: {ecg_q['diagnosis']}")
            else:
                logger.info(f"[{i}/{len(ECG_QUESTIONS)}] [DRY RUN] Would create: {ecg_q['diagnosis']}")
                created += 1

        except Exception as e:
            logger.error(f"Error creating {ecg_q['diagnosis']}: {e}")
            continue

    if not dry_run:
        try:
            db.commit()
            logger.info(f"Committed {created} ECG questions to database")
        except Exception as e:
            logger.error(f"Commit failed: {e}")
            db.rollback()
            return 0

    return created


def main():
    parser = argparse.ArgumentParser(description="Create ECG questions for IM shelf")
    parser.add_argument("--dry-run", action="store_true", help="Preview only, don't save")
    args = parser.parse_args()

    # Setup database
    db_path = (backend_path / 'shelfsense.db').resolve()
    db_url = f"sqlite:///{db_path}"
    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)
    db = Session()

    logger.info(f"Database: {db_url}")

    print("\n" + "=" * 60)
    print("ECG QUESTION CURATION")
    print("=" * 60)
    print(f"  Total ECG questions to create: {len(ECG_QUESTIONS)}")
    print(f"  Mode: {'DRY RUN' if args.dry_run else 'CREATE'}")
    print("=" * 60 + "\n")

    try:
        created = create_ecg_questions(db, dry_run=args.dry_run)
    finally:
        db.close()

    print("\n" + "=" * 60)
    print("CURATION COMPLETE")
    print("=" * 60)
    print(f"  Questions created: {created}")
    print("=" * 60)


if __name__ == "__main__":
    main()
