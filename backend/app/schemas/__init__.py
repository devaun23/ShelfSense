"""
ShelfSense Schemas Package

Pydantic models for request/response validation and data structures.
"""

from app.schemas.explanation import (
    # Enums
    ExplanationType,
    DifficultyLevel,
    ReasoningComplexity,
    LearnerStage,

    # Components
    DistractorExplanation,
    StepByStep,
    DeepDive,
    MemoryHooks,
    CommonTrap,
    VisualAid,
    DifficultyFactors,

    # Main schemas
    EnhancedExplanation,
    QuickExplanation,
    StandardExplanation,
    FullExplanation,

    # Tracking
    ExplanationEffectiveness,

    # Migration
    LegacyExplanation,
    is_legacy_explanation,
)

__all__ = [
    # Enums
    "ExplanationType",
    "DifficultyLevel",
    "ReasoningComplexity",
    "LearnerStage",

    # Components
    "DistractorExplanation",
    "StepByStep",
    "DeepDive",
    "MemoryHooks",
    "CommonTrap",
    "VisualAid",
    "DifficultyFactors",

    # Main schemas
    "EnhancedExplanation",
    "QuickExplanation",
    "StandardExplanation",
    "FullExplanation",

    # Tracking
    "ExplanationEffectiveness",

    # Migration
    "LegacyExplanation",
    "is_legacy_explanation",
]
