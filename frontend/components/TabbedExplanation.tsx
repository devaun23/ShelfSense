'use client';

import { useState } from 'react';
import { Tabs, TabsList, Tab, TabContent } from './ui/Tabs';
import CollapsibleSection from './ui/CollapsibleSection';

interface StepByStep {
  step: number;
  action: string;
  rationale: string;
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
  memory_hooks?: MemoryHooks;
  common_traps?: CommonTrap[];
  educational_objective?: string;
  concept?: string;
  related_topics?: string[];
  difficulty_factors?: DifficultyFactors;
}

interface TabbedExplanationProps {
  explanation: EnhancedExplanationData;
  correctAnswer: string;
  userAnswer: string;
  isCorrect: boolean;
  choices: string[];
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

export default function TabbedExplanation({
  explanation,
  correctAnswer,
  userAnswer,
  isCorrect,
  choices
}: TabbedExplanationProps) {
  const [activeTab, setActiveTab] = useState('explanation');

  const typeInfo = explanation.type ? TYPE_LABELS[explanation.type] || {
    label: explanation.type,
    color: 'text-gray-400'
  } : null;

  // Generate choice letters A-E
  const choiceLetters = ['A', 'B', 'C', 'D', 'E'];

  return (
    <div className="space-y-4">
      {/* Header with type badge and difficulty */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          {typeInfo && (
            <span className={`text-sm font-medium ${typeInfo.color}`}>
              {typeInfo.label}
            </span>
          )}
          {explanation.concept && (
            <span className="text-gray-600 text-xs">
              {explanation.concept}
            </span>
          )}
        </div>
        {explanation.difficulty_factors && (
          <span className={`text-xs px-2 py-1 rounded-full ${DIFFICULTY_COLORS[explanation.difficulty_factors.content_difficulty]}`}>
            {explanation.difficulty_factors.content_difficulty}
          </span>
        )}
      </div>

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab} defaultValue="explanation">
        <TabsList>
          <Tab value="explanation">Explanation</Tab>
          <Tab value="wrong">Why Each Wrong</Tab>
          <Tab value="pearl">Clinical Pearl</Tab>
          <Tab value="highyield">High-Yield</Tab>
        </TabsList>

        {/* Tab 1: Explanation */}
        <TabContent value="explanation">
          <div className="space-y-4">
            {/* Quick Answer */}
            {explanation.quick_answer && (
              <div className="bg-[#4169E1]/10 border border-[#4169E1]/30 rounded-xl p-4">
                <p className="text-gray-200 font-medium leading-relaxed">
                  {explanation.quick_answer}
                </p>
              </div>
            )}

            {/* Core Explanation */}
            <div className="bg-gray-900/50 border border-gray-800 rounded-xl p-5 space-y-4">
              {/* Principle */}
              {explanation.principle && (
                <CollapsibleSection title="Key Principle" defaultOpen={true}>
                  <p className="text-gray-100 font-medium leading-relaxed">
                    {explanation.principle}
                  </p>
                </CollapsibleSection>
              )}

              {/* Clinical Reasoning */}
              {explanation.clinical_reasoning && (
                <CollapsibleSection title="Clinical Reasoning" defaultOpen={true}>
                  <p className="text-gray-300 leading-relaxed whitespace-pre-wrap">
                    {explanation.clinical_reasoning}
                  </p>
                </CollapsibleSection>
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
              {!isCorrect && userAnswer && explanation.distractor_explanations?.[userAnswer] && (
                <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4">
                  <h4 className="text-xs font-semibold text-red-400 uppercase tracking-wider mb-2">
                    Why {userAnswer} is Incorrect
                  </h4>
                  <p className="text-gray-300 leading-relaxed">
                    {explanation.distractor_explanations[userAnswer]}
                  </p>
                </div>
              )}
            </div>

            {/* Educational Objective */}
            {explanation.educational_objective && (
              <div className="text-sm text-gray-500 italic">
                <span className="font-medium text-gray-400">Learning Objective: </span>
                {explanation.educational_objective}
              </div>
            )}
          </div>
        </TabContent>

        {/* Tab 2: Why Each Wrong */}
        <TabContent value="wrong">
          <div className="bg-gray-900/50 border border-gray-800 rounded-xl overflow-hidden">
            <table className="w-full">
              <thead>
                <tr className="bg-gray-800/50">
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-400 uppercase tracking-wider w-16">
                    Choice
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-400 uppercase tracking-wider">
                    Answer
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-400 uppercase tracking-wider">
                    Explanation
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-800">
                {choiceLetters.slice(0, choices.length).map((letter, idx) => {
                  const isCorrectChoice = letter === correctAnswer;
                  const isUserChoice = letter === userAnswer;
                  const explanation_text = explanation.distractor_explanations?.[letter] || '';

                  return (
                    <tr
                      key={letter}
                      className={`
                        ${isCorrectChoice ? 'bg-emerald-500/5' : ''}
                        ${isUserChoice && !isCorrectChoice ? 'bg-red-500/5' : ''}
                      `}
                    >
                      <td className="px-4 py-3">
                        <span className={`
                          inline-flex items-center justify-center w-8 h-8 rounded-full text-sm font-bold
                          ${isCorrectChoice
                            ? 'bg-emerald-500/20 text-emerald-400 ring-2 ring-emerald-500/50'
                            : isUserChoice
                              ? 'bg-red-500/20 text-red-400 ring-2 ring-red-500/50'
                              : 'bg-gray-800 text-gray-400'
                          }
                        `}>
                          {letter}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-300">
                        {choices[idx]}
                      </td>
                      <td className="px-4 py-3 text-sm">
                        {isCorrectChoice ? (
                          <span className="text-emerald-400 font-medium">Correct answer</span>
                        ) : explanation_text ? (
                          <span className="text-gray-400">{explanation_text}</span>
                        ) : (
                          <span className="text-gray-600 italic">No explanation available</span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </TabContent>

        {/* Tab 3: Clinical Pearl */}
        <TabContent value="pearl">
          <div className="space-y-4">
            {/* Pathophysiology */}
            {explanation.deep_dive?.pathophysiology && (
              <CollapsibleSection title="Pathophysiology" defaultOpen={true}>
                <p className="text-gray-300 leading-relaxed">
                  {explanation.deep_dive.pathophysiology}
                </p>
              </CollapsibleSection>
            )}

            {/* Differential Comparison */}
            {explanation.deep_dive?.differential_comparison && (
              <CollapsibleSection title="Differential Comparison" defaultOpen={true}>
                <p className="text-gray-300 leading-relaxed">
                  {explanation.deep_dive.differential_comparison}
                </p>
              </CollapsibleSection>
            )}

            {/* Clinical Pearls */}
            {explanation.deep_dive?.clinical_pearls && explanation.deep_dive.clinical_pearls.length > 0 && (
              <CollapsibleSection title="Clinical Pearls" defaultOpen={true}>
                <ul className="space-y-2">
                  {explanation.deep_dive.clinical_pearls.map((pearl, idx) => (
                    <li key={idx} className="flex items-start gap-2 text-gray-300">
                      <span className="text-[#4169E1] mt-1">•</span>
                      <span>{pearl}</span>
                    </li>
                  ))}
                </ul>
              </CollapsibleSection>
            )}

            {/* Step-by-Step */}
            {explanation.step_by_step && explanation.step_by_step.length > 0 && (
              <CollapsibleSection title="Step-by-Step Approach" defaultOpen={false}>
                <div className="space-y-3">
                  {explanation.step_by_step.map((step) => (
                    <div key={step.step} className="flex gap-3">
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
              </CollapsibleSection>
            )}

            {/* No content fallback */}
            {!explanation.deep_dive?.pathophysiology &&
             !explanation.deep_dive?.differential_comparison &&
             (!explanation.deep_dive?.clinical_pearls || explanation.deep_dive.clinical_pearls.length === 0) &&
             (!explanation.step_by_step || explanation.step_by_step.length === 0) && (
              <div className="text-center text-gray-500 py-8">
                No clinical pearl data available for this question.
              </div>
            )}
          </div>
        </TabContent>

        {/* Tab 4: High-Yield */}
        <TabContent value="highyield">
          <div className="space-y-4">
            {/* Memory Hooks */}
            {explanation.memory_hooks && (explanation.memory_hooks.analogy || explanation.memory_hooks.mnemonic) && (
              <div className="bg-purple-500/10 border border-purple-500/30 rounded-xl p-4">
                <h4 className="text-xs font-semibold text-purple-400 uppercase tracking-wider mb-3">
                  Memory Hooks
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

            {/* Common Traps */}
            {explanation.common_traps && explanation.common_traps.length > 0 && (
              <CollapsibleSection title="Common Traps to Avoid" defaultOpen={true}>
                <div className="space-y-3">
                  {explanation.common_traps.map((trap, idx) => (
                    <div key={idx} className="bg-orange-500/10 border border-orange-500/30 rounded-lg p-4">
                      <p className="text-orange-400 font-medium mb-2">{trap.trap}</p>
                      <p className="text-gray-400 text-sm mb-2">
                        <span className="font-medium">Why wrong: </span>
                        {trap.why_wrong}
                      </p>
                      <p className="text-gray-300 text-sm">
                        <span className="font-medium text-emerald-400">Correct thinking: </span>
                        {trap.correct_thinking}
                      </p>
                    </div>
                  ))}
                </div>
              </CollapsibleSection>
            )}

            {/* Related Topics */}
            {explanation.related_topics && explanation.related_topics.length > 0 && (
              <div>
                <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
                  Related Topics
                </h4>
                <div className="flex flex-wrap gap-2">
                  {explanation.related_topics.map((topic, idx) => (
                    <span
                      key={idx}
                      className="px-3 py-1 bg-gray-800 text-gray-400 text-sm rounded-full"
                    >
                      {topic}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* No content fallback */}
            {(!explanation.memory_hooks || (!explanation.memory_hooks.analogy && !explanation.memory_hooks.mnemonic)) &&
             (!explanation.common_traps || explanation.common_traps.length === 0) &&
             (!explanation.related_topics || explanation.related_topics.length === 0) && (
              <div className="text-center text-gray-500 py-8">
                No high-yield data available for this question.
              </div>
            )}
          </div>
        </TabContent>
      </Tabs>
    </div>
  );
}
