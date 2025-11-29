#!/usr/bin/env python3
"""
Monitor Internal Medicine Question Generation Progress
Tracks progress against IM_QUESTION_GENERATION_MANIFEST.md targets

Usage:
    python scripts/monitor_generation_progress.py
    python scripts/monitor_generation_progress.py --export report.json
"""

import sys
import os
import json
import argparse
from datetime import datetime
from typing import Dict, List

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from sqlalchemy import func
from app.database import SessionLocal
from app.models.models import Question

# Import targets from batch generator
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
from batch_generate_im import (
    SUBSPECIALTY_TARGETS,
    TASK_TYPE_PERCENTAGES,
    DIFFICULTY_PERCENTAGES,
)


class ProgressMonitor:
    """Monitor generation progress against manifest targets"""

    def __init__(self, db):
        self.db = db
        self.targets = SUBSPECIALTY_TARGETS
        self.task_targets = TASK_TYPE_PERCENTAGES
        self.diff_targets = DIFFICULTY_PERCENTAGES

    def get_subspecialty_distribution(self) -> Dict:
        """Get current subspecialty distribution"""
        results = self.db.query(
            func.json_extract(Question.extra_data, '$.subspecialty').label('subspecialty'),
            func.count(Question.id).label('count')
        ).filter(
            Question.specialty == 'internal_medicine',
            Question.source.like('%AI Generated%')
        ).group_by('subspecialty').all()

        distribution = {r.subspecialty: r.count for r in results if r.subspecialty}

        # Add missing subspecialties with 0 count
        for subspecialty in self.targets.keys():
            if subspecialty not in distribution:
                distribution[subspecialty] = 0

        return distribution

    def get_task_distribution(self) -> Dict:
        """Get current task type distribution"""
        results = self.db.query(
            func.json_extract(Question.extra_data, '$.task_type').label('task_type'),
            func.count(Question.id).label('count')
        ).filter(
            Question.specialty == 'internal_medicine',
            Question.source.like('%AI Generated%')
        ).group_by('task_type').all()

        distribution = {r.task_type: r.count for r in results if r.task_type}

        # Add missing tasks
        for task in self.task_targets.keys():
            if task not in distribution:
                distribution[task] = 0

        return distribution

    def get_difficulty_distribution(self) -> Dict:
        """Get current difficulty distribution"""
        results = self.db.query(
            Question.difficulty_level,
            func.count(Question.id).label('count')
        ).filter(
            Question.specialty == 'internal_medicine',
            Question.source.like('%AI Generated%'),
            Question.difficulty_level.isnot(None)
        ).group_by(Question.difficulty_level).all()

        distribution = {r.difficulty_level: r.count for r in results}

        # Add missing difficulties
        for difficulty in self.diff_targets.keys():
            if difficulty not in distribution:
                distribution[difficulty] = 0

        return distribution

    def get_total_count(self) -> int:
        """Get total IM AI-generated questions"""
        return self.db.query(func.count(Question.id)).filter(
            Question.specialty == 'internal_medicine',
            Question.source.like('%AI Generated%')
        ).scalar()

    def calculate_gaps(self) -> Dict:
        """Calculate gaps for all dimensions"""
        total = self.get_total_count()
        target_total = sum(self.targets.values())

        subspecialty_dist = self.get_subspecialty_distribution()
        task_dist = self.get_task_distribution()
        diff_dist = self.get_difficulty_distribution()

        # Subspecialty gaps
        subspecialty_gaps = []
        for subspecialty, target in self.targets.items():
            current = subspecialty_dist.get(subspecialty, 0)
            gap = target - current
            percentage = (current / target * 100) if target > 0 else 0

            subspecialty_gaps.append({
                "subspecialty": subspecialty,
                "current": current,
                "target": target,
                "gap": gap,
                "percentage": round(percentage, 1),
                "priority": self._calculate_priority(gap, target)
            })

        # Sort by gap size
        subspecialty_gaps.sort(key=lambda x: -x["gap"])

        # Task type gaps
        task_gaps = []
        for task, target_pct in self.task_targets.items():
            target_count = int(total * target_pct / 100)
            current = task_dist.get(task, 0)
            gap = target_count - current
            percentage = (current / target_count * 100) if target_count > 0 else 0

            task_gaps.append({
                "task_type": task,
                "current": current,
                "target": target_count,
                "gap": gap,
                "percentage": round(percentage, 1),
                "priority": self._calculate_priority(gap, target_count)
            })

        task_gaps.sort(key=lambda x: -x["gap"])

        # Difficulty gaps
        diff_gaps = []
        for difficulty, target_pct in self.diff_targets.items():
            target_count = int(total * target_pct / 100)
            current = diff_dist.get(difficulty, 0)
            gap = target_count - current
            percentage = (current / target_count * 100) if target_count > 0 else 0

            diff_gaps.append({
                "difficulty": difficulty,
                "current": current,
                "target": target_count,
                "gap": gap,
                "percentage": round(percentage, 1),
                "priority": self._calculate_priority(gap, target_count)
            })

        diff_gaps.sort(key=lambda x: -x["gap"])

        return {
            "total": {
                "current": total,
                "target": target_total,
                "gap": target_total - total,
                "percentage": round(total / target_total * 100, 1) if target_total > 0 else 0
            },
            "subspecialty_gaps": subspecialty_gaps,
            "task_gaps": task_gaps,
            "difficulty_gaps": diff_gaps,
            "analysis_date": datetime.now().isoformat()
        }

    def _calculate_priority(self, gap: int, target: int) -> str:
        """Calculate gap priority"""
        if gap <= 0:
            return "COMPLETE"
        elif gap > target * 0.5:
            return "HIGH"
        elif gap > target * 0.25:
            return "MEDIUM"
        else:
            return "LOW"

    def print_report(self):
        """Print formatted progress report"""
        gaps = self.calculate_gaps()

        print("\n" + "="*100)
        print("INTERNAL MEDICINE QUESTION GENERATION PROGRESS REPORT")
        print("="*100)

        # Overall progress
        total = gaps["total"]
        print(f"\n📊 OVERALL PROGRESS")
        print(f"   Current: {total['current']:,} / {total['target']:,} questions ({total['percentage']}%)")
        print(f"   Remaining: {total['gap']:,} questions")

        # Progress bar
        bar_length = 50
        filled = int(bar_length * total['current'] / total['target']) if total['target'] > 0 else 0
        bar = "█" * filled + "░" * (bar_length - filled)
        print(f"   [{bar}]")

        # Subspecialty breakdown
        print(f"\n📚 SUBSPECIALTY DISTRIBUTION")
        print(f"   {'Subspecialty':<30} {'Current':>8} {'Target':>8} {'Gap':>8} {'%':>7} {'Priority':<8}")
        print(f"   {'-'*80}")

        for item in gaps["subspecialty_gaps"]:
            status_symbol = "✓" if item["gap"] <= 0 else "⚠" if item["priority"] == "HIGH" else "○"
            print(f"   {status_symbol} {item['subspecialty']:<28} {item['current']:>8} {item['target']:>8} "
                  f"{item['gap']:>8} {item['percentage']:>6}% {item['priority']:<8}")

        # Task type breakdown
        print(f"\n📋 TASK TYPE DISTRIBUTION")
        print(f"   {'Task Type':<30} {'Current':>8} {'Target':>8} {'Gap':>8} {'%':>7} {'Priority':<8}")
        print(f"   {'-'*80}")

        for item in gaps["task_gaps"]:
            status_symbol = "✓" if item["gap"] <= 0 else "⚠" if item["priority"] == "HIGH" else "○"
            print(f"   {status_symbol} {item['task_type']:<28} {item['current']:>8} {item['target']:>8} "
                  f"{item['gap']:>8} {item['percentage']:>6}% {item['priority']:<8}")

        # Difficulty breakdown
        print(f"\n🎯 DIFFICULTY DISTRIBUTION")
        print(f"   {'Difficulty':<30} {'Current':>8} {'Target':>8} {'Gap':>8} {'%':>7} {'Priority':<8}")
        print(f"   {'-'*80}")

        for item in gaps["difficulty_gaps"]:
            status_symbol = "✓" if item["gap"] <= 0 else "⚠" if item["priority"] == "HIGH" else "○"
            print(f"   {status_symbol} {item['difficulty']:<28} {item['current']:>8} {item['target']:>8} "
                  f"{item['gap']:>8} {item['percentage']:>6}% {item['priority']:<8}")

        # Recommendations
        print(f"\n💡 NEXT STEPS")
        high_priority_subspecialties = [
            item for item in gaps["subspecialty_gaps"]
            if item["priority"] == "HIGH" and item["gap"] > 0
        ]

        high_priority_tasks = [
            item for item in gaps["task_gaps"]
            if item["priority"] == "HIGH" and item["gap"] > 0
        ]

        if high_priority_subspecialties:
            print(f"   1. Focus on high-priority subspecialties:")
            for item in high_priority_subspecialties[:3]:
                print(f"      - {item['subspecialty']}: {item['gap']} questions needed")

        if high_priority_tasks:
            print(f"   2. Focus on high-priority task types:")
            for item in high_priority_tasks[:3]:
                print(f"      - {item['task_type']}: {item['gap']} questions needed")

        # Estimated completion
        avg_daily_rate = 60  # From manifest
        days_remaining = total['gap'] / avg_daily_rate if total['gap'] > 0 else 0
        print(f"\n⏱️  ESTIMATED COMPLETION")
        print(f"   At {avg_daily_rate} questions/day: {days_remaining:.1f} days remaining")

        print(f"\n{'='*100}\n")

        return gaps

    def export_json(self, filepath: str):
        """Export gaps to JSON file"""
        gaps = self.calculate_gaps()

        with open(filepath, 'w') as f:
            json.dump(gaps, f, indent=2)

        print(f"✓ Progress report exported to {filepath}")


def main():
    parser = argparse.ArgumentParser(
        description="Monitor IM question generation progress"
    )
    parser.add_argument(
        "--export",
        type=str,
        help="Export progress report to JSON file"
    )

    args = parser.parse_args()

    db = SessionLocal()

    try:
        monitor = ProgressMonitor(db)
        monitor.print_report()

        if args.export:
            monitor.export_json(args.export)

    finally:
        db.close()


if __name__ == "__main__":
    main()
