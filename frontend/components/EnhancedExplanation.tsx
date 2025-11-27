'use client';

import { useState, memo } from 'react';

interface StepByStep {
  step: number;
  action: string;
  rationale: string;
}

interface VisualAid {
  type: string;
  description: string;
  key_elements: string[];
}

interface MemoryHooks {
  analogy: string | null;
  mnemonic: string | null;
  clinical_story: string | null;
}

interface CommonTrap {
  trap: string;
  why_wrong: string;
  correct_thinking: string;
}

interface DeepDive {
  pathophysiology: string;
  differential_comparison: string;
  clinical_pearls: string[];
}

interface DifficultyFactors {
  content_difficulty: 'basic' | 'intermediate' | 'advanced';
  reasoning_complexity: 'single_step' | 'multi_step' | 'integration';
  common_error_rate: number;
}

interface EnhancedExplanationData {
  type?: string;
  quick_answer?: string;
  principle?: string;
  clinical_reasoning?: string;
  correct_answer_explanation?: string;
  distractor_explanations?: Record<string, string>;
  deep_dive?: DeepDive;
  step_by_step?: StepByStep[];
  visual_aid?: VisualAid;
  memory_hooks?: MemoryHooks;
  common_traps?: CommonTrap[];
  educational_objective?: string;
  concept?: string;
  related_topics?: string[];
  difficulty_factors?: DifficultyFactors;
}

interface EnhancedExplanationProps {
  explanation: EnhancedExplanationData;
  correctAnswer: string;
  userAnswer: string;
  isCorrect: boolean;
  mode?: 'full' | 'review' | 'compact';
}

const TYPE_LABELS: Record<string, { label: string; color: string }> = {
  TYPE_A_STABILITY: { label: 'Stability Assessment', color: 'text-red-400' },
  TYPE_B_TIME: { label: 'Time-Sensitive', color: 'text-orange-400' },
  TYPE_C_DIAGNOSTIC: { label: 'Diagnostic Sequence', color: 'text-blue-400' },
  TYPE_D_RISK: { label: 'Risk Stratification', color: 'text-purple-400' },
  TYPE_E_TREATMENT: { label: 'Treatment Hierarchy', color: 'text-green-400' },
  TYPE_F_DIFFERENTIAL: { label: 'Differential Diagnosis', color: 'text-yellow-400' },
};

const DIFFICULTY_COLORS: Record<string, string> = {
  basic: 'bg-green-500/20 text-green-400',
  intermediate: 'bg-yellow-500/20 text-yellow-400',
  advanced: 'bg-red-500/20 text-red-400',
};

export default memo(function EnhancedExplanation({
  explanation,
  correctAnswer,
  userAnswer,
  isCorrect,
  mode = 'full'
}: EnhancedExplanationProps) {
  const [showDeepDive, setShowDeepDive] = useState(false);
  const [showSteps, setShowSteps] = useState(false);
  const [showTraps, setShowTraps] = useState(false);

  // Handle missing or empty explanation
  if (!explanation || Object.keys(explanation).length === 0) {
    return (
      <div className="bg-gray-900/50 border border-gray-800 rounded-xl p-4">
        <p className="text-gray-400 text-sm">Explanation not available for this question.</p>
      </div>
    );
  }

  // Get type info with fallback
  const typeInfo = explanation.type ? (TYPE_LABELS[explanation.type] || {
    label: explanation.type.replace(/_/g, ' ').replace('TYPE ', ''),
    color: 'text-gray-400'
  }) : null;

  // Derive concept from principle if not provided
  const displayConcept = explanation.concept || '';

  // Create a quick answer from principle if not provided
  const displayQuickAnswer = explanation.quick_answer || explanation.principle || '';

  // Get distractor explanations with fallback
  const distractorExplanations = explanation.distractor_explanations || {};

  // Review mode - just show quick answer
  if (mode === 'review') {
    return (
      <div className="bg-gray-900/50 border border-gray-800 rounded-xl p-4">
        <p className="text-gray-300 text-sm leading-relaxed">
          {displayQuickAnswer || explanation.correct_answer_explanation || 'No explanation available.'}
        </p>
      </div>
    );
  }

  // Compact mode - principle + correct answer only
  if (mode === 'compact') {
    return (
      <div className="bg-gray-900/50 border border-gray-800 rounded-xl p-4 space-y-3">
        {typeInfo && (
          <div className="flex items-center gap-2 text-xs">
            <span className={typeInfo.color}>{typeInfo.label}</span>
          </div>
        )}
        {explanation.principle && (
          <p className="text-gray-200 font-medium">{explanation.principle}</p>
        )}
        <p className="text-gray-400 text-sm">
          {explanation.correct_answer_explanation || displayQuickAnswer || 'The correct answer is based on clinical guidelines.'}
        </p>
      </div>
    );
  }

  // Full mode - all sections with progressive disclosure
  return (
    <div className="space-y-4">
      {/* Header with type badge - only show if we have type or concept */}
      {(typeInfo || displayConcept || explanation.difficulty_factors) && (
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            {typeInfo && (
              <span className={`text-sm font-medium ${typeInfo.color}`}>
                {typeInfo.label}
              </span>
            )}
            {displayConcept && (
              <span className="text-gray-600 text-xs">
                {displayConcept}
              </span>
            )}
          </div>
          {explanation.difficulty_factors && (
            <span className={`text-xs px-2 py-1 rounded-full ${DIFFICULTY_COLORS[explanation.difficulty_factors.content_difficulty]}`}>
              {explanation.difficulty_factors.content_difficulty}
            </span>
          )}
        </div>
      )}

      {/* Quick Answer - Always visible when available */}
      {displayQuickAnswer && (
        <div className="bg-[#4169E1]/10 border border-[#4169E1]/30 rounded-xl p-4">
          <p className="text-gray-200 font-medium leading-relaxed">
            {displayQuickAnswer}
          </p>
        </div>
      )}

      {/* Core Explanation - only show if we have content */}
      {(explanation.principle || explanation.clinical_reasoning || explanation.correct_answer_explanation) && (
        <div className="bg-gray-900/50 border border-gray-800 rounded-xl p-5 space-y-4">
          {/* Principle */}
          {explanation.principle && (
            <div>
              <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
                Key Principle
              </h4>
              <p className="text-gray-100 font-medium leading-relaxed">
                {explanation.principle}
              </p>
            </div>
          )}

          {/* Clinical Reasoning */}
          {explanation.clinical_reasoning && (
            <div>
              <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
                Clinical Reasoning
              </h4>
              <p className="text-gray-300 leading-relaxed">
                {explanation.clinical_reasoning}
              </p>
            </div>
          )}

          {/* Correct Answer Explanation */}
          {explanation.correct_answer_explanation && (
            <div className="bg-emerald-500/10 border border-emerald-500/30 rounded-lg p-4">
              <h4 className="text-xs font-semibold text-emerald-400 uppercase tracking-wider mb-2">
                Why {correctAnswer} is Correct
              </h4>
              <p className="text-gray-300 leading-relaxed">
                {explanation.correct_answer_explanation}
              </p>
            </div>
          )}

          {/* User's Wrong Answer Explanation */}
          {!isCorrect && userAnswer && distractorExplanations[userAnswer] && (
            <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4">
              <h4 className="text-xs font-semibold text-red-400 uppercase tracking-wider mb-2">
                Why {userAnswer} is Incorrect
              </h4>
              <p className="text-gray-300 leading-relaxed">
                {distractorExplanations[userAnswer]}
              </p>
            </div>
          )}
        </div>
      )}

      {/* Memory Hooks */}
      {explanation.memory_hooks && (explanation.memory_hooks.analogy || explanation.memory_hooks.mnemonic) && (
        <div className="bg-purple-500/10 border border-purple-500/30 rounded-xl p-4">
          <h4 className="text-xs font-semibold text-purple-400 uppercase tracking-wider mb-3">
            Memory Hook
          </h4>
          {explanation.memory_hooks.analogy && (
            <p className="text-gray-300 leading-relaxed mb-2">
              <span className="text-purple-400 font-medium">Analogy: </span>
              {explanation.memory_hooks.analogy}
            </p>
          )}
          {explanation.memory_hooks.mnemonic && (
            <p className="text-gray-300 leading-relaxed">
              <span className="text-purple-400 font-medium">Mnemonic: </span>
              {explanation.memory_hooks.mnemonic}
            </p>
          )}
        </div>
      )}

      {/* Expandable Sections */}
      <div className="space-y-2">
        {/* Step-by-Step */}
        {explanation.step_by_step && explanation.step_by_step.length > 0 && (
          <div className="border border-gray-800 rounded-xl overflow-hidden">
            <button
              onClick={() => setShowSteps(!showSteps)}
              className="w-full px-4 py-3 flex items-center justify-between hover:bg-gray-900/50 transition-colors"
            >
              <span className="text-sm font-medium text-gray-300">
                Step-by-Step Approach
              </span>
              <svg
                className={`w-5 h-5 text-gray-500 transition-transform ${showSteps ? 'rotate-180' : ''}`}
                fill="none" stroke="currentColor" viewBox="0 0 24 24"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </button>
            <div className={`motion-safe:transition-all motion-safe:duration-200 ease-out overflow-hidden ${showSteps ? 'max-h-[2000px] opacity-100' : 'max-h-0 opacity-0'}`}>
              <div className="px-4 pb-4 space-y-3 border-t border-gray-800">
                {explanation.step_by_step.map((step) => (
                  <div key={step.step} className="flex gap-3 pt-3">
                    <div className="flex-shrink-0 w-6 h-6 rounded-full bg-[#4169E1] flex items-center justify-center text-xs font-bold text-white">
                      {step.step}
                    </div>
                    <div>
                      <p className="text-gray-200 font-medium">{step.action}</p>
                      <p className="text-gray-500 text-sm mt-1">{step.rationale}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Deep Dive */}
        {explanation.deep_dive && (
          <div className="border border-gray-800 rounded-xl overflow-hidden">
            <button
              onClick={() => setShowDeepDive(!showDeepDive)}
              className="w-full px-4 py-3 flex items-center justify-between hover:bg-gray-900/50 transition-colors"
            >
              <span className="text-sm font-medium text-gray-300">
                Deep Dive
              </span>
              <svg
                className={`w-5 h-5 text-gray-500 transition-transform ${showDeepDive ? 'rotate-180' : ''}`}
                fill="none" stroke="currentColor" viewBox="0 0 24 24"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </button>
            <div className={`motion-safe:transition-all motion-safe:duration-200 ease-out overflow-hidden ${showDeepDive ? 'max-h-[2000px] opacity-100' : 'max-h-0 opacity-0'}`}>
              <div className="px-4 pb-4 space-y-4 border-t border-gray-800 pt-4">
                {explanation.deep_dive.pathophysiology && (
                  <div>
                    <h5 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
                      Pathophysiology
                    </h5>
                    <p className="text-gray-400 text-sm leading-relaxed">
                      {explanation.deep_dive.pathophysiology}
                    </p>
                  </div>
                )}
                {explanation.deep_dive.differential_comparison && (
                  <div>
                    <h5 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
                      Differential Comparison
                    </h5>
                    <p className="text-gray-400 text-sm leading-relaxed">
                      {explanation.deep_dive.differential_comparison}
                    </p>
                  </div>
                )}
                {explanation.deep_dive.clinical_pearls && explanation.deep_dive.clinical_pearls.length > 0 && (
                  <div>
                    <h5 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
                      Clinical Pearls
                    </h5>
                    <ul className="space-y-1">
                      {explanation.deep_dive.clinical_pearls.map((pearl, i) => (
                        <li key={i} className="text-gray-400 text-sm flex items-start gap-2">
                          <span className="text-[#4169E1]">•</span>
                          {pearl}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Common Traps */}
        {explanation.common_traps && explanation.common_traps.length > 0 && (
          <div className="border border-gray-800 rounded-xl overflow-hidden">
            <button
              onClick={() => setShowTraps(!showTraps)}
              className="w-full px-4 py-3 flex items-center justify-between hover:bg-gray-900/50 transition-colors"
            >
              <span className="text-sm font-medium text-gray-300">
                Common Traps to Avoid
              </span>
              <svg
                className={`w-5 h-5 text-gray-500 transition-transform ${showTraps ? 'rotate-180' : ''}`}
                fill="none" stroke="currentColor" viewBox="0 0 24 24"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </button>
            <div className={`motion-safe:transition-all motion-safe:duration-200 ease-out overflow-hidden ${showTraps ? 'max-h-[2000px] opacity-100' : 'max-h-0 opacity-0'}`}>
              <div className="px-4 pb-4 space-y-3 border-t border-gray-800 pt-4">
                {explanation.common_traps.map((trap, i) => (
                  <div key={i} className="bg-orange-500/10 border border-orange-500/30 rounded-lg p-3">
                    <p className="text-orange-400 font-medium text-sm mb-2">
                      {trap.trap}
                    </p>
                    <p className="text-gray-400 text-sm mb-2">
                      <span className="text-gray-500">Why it fails: </span>
                      {trap.why_wrong}
                    </p>
                    <p className="text-emerald-400 text-sm">
                      <span className="text-gray-500">Correct approach: </span>
                      {trap.correct_thinking}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Educational Objective - only show if available */}
      {explanation.educational_objective && (
        <div className="text-center py-4 border-t border-gray-800">
          <p className="text-gray-500 text-xs uppercase tracking-wider mb-1">
            Learning Objective
          </p>
          <p className="text-gray-400 text-sm">
            {explanation.educational_objective}
          </p>
        </div>
      )}

      {/* Related Topics */}
      {explanation.related_topics && explanation.related_topics.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {explanation.related_topics.map((topic, i) => (
            <span
              key={i}
              className="px-3 py-1 bg-gray-800 text-gray-400 text-xs rounded-full"
            >
              {topic}
            </span>
          ))}
        </div>
      )}
    </div>
  );
});
