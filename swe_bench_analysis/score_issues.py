#!/usr/bin/env python3
"""
SWE-bench Lite Issue Scorer for Claim Extraction
=================================================
Run this on your UMD cluster to analyze and rank issues by suitability
for claim extraction experiments.

Usage:
    python score_issues.py --output scored_issues.json
    python score_issues.py --top 50 --output top50.json
"""

import json
import re
import argparse
from collections import defaultdict
from dataclasses import dataclass, asdict
from typing import List, Dict, Tuple

# Try to import datasets, provide fallback instructions
try:
    from datasets import load_dataset
except ImportError:
    print("Install datasets: pip install datasets")
    exit(1)


@dataclass
class IssueScore:
    instance_id: str
    repo: str
    score: int  # 0-100, higher = easier
    patch_lines: int
    files_modified: int
    has_explicit_behavior: bool
    has_code_examples: bool
    has_exception_mention: bool
    testability: str  # high/medium/low
    tier: int  # 1=easy, 2=medium, 3=hard
    reasons: List[str]


# Repo difficulty tiers
REPO_TIERS = {
    # Tier 1: Easy - explicit requirements, high testability
    'pytest-dev/pytest': 1,
    'pylint-dev/pylint': 1,
    'psf/requests': 1,
    'pallets/flask': 1,
    
    # Tier 2: Medium - semi-explicit, reasonable testability  
    'django/django': 2,
    'astropy/astropy': 2,
    'pydata/xarray': 2,
    'mwaskom/seaborn': 2,
    
    # Tier 3: Hard - implicit requirements, difficult to test
    'matplotlib/matplotlib': 3,
    'scikit-learn/scikit-learn': 3,
    'sympy/sympy': 3,
    'sphinx-doc/sphinx': 3,
}

# Django submodule difficulty
DJANGO_EASY_MODULES = [
    'django.conf', 'django.forms', 'django.core.validators',
    'django.utils', 'django.template', 'django.contrib.auth',
]
DJANGO_HARD_MODULES = [
    'django.db.models', 'django.db.migrations', 'django.db.backends',
]


def count_patch_lines(patch: str) -> int:
    """Count meaningful changed lines in patch"""
    if not patch:
        return 0
    lines = patch.split('\n')
    changed = sum(1 for l in lines if l.startswith('+') or l.startswith('-'))
    # Exclude headers
    changed -= patch.count('+++') + patch.count('---')
    return max(0, changed)


def count_files(patch: str) -> int:
    """Count files modified in patch"""
    if not patch:
        return 0
    return patch.count('diff --git')


def extract_django_module(patch: str) -> str:
    """Extract Django module from patch path"""
    match = re.search(r'diff --git a/(django/\w+)', patch)
    if match:
        return match.group(1)
    return ''


def has_explicit_behavior_keywords(text: str) -> Tuple[bool, List[str]]:
    """Check for explicit behavioral requirement keywords"""
    text_lower = text.lower()
    
    keywords = {
        'strong': ['should return', 'should raise', 'must return', 'must raise',
                   'should not', 'must not', 'expected to return', 'expected to raise'],
        'medium': ['returns', 'raises', 'TypeError', 'ValueError', 'KeyError',
                   'AttributeError', 'expected behavior', 'expected output',
                   'instead of', 'rather than', 'incorrectly'],
        'weak': ['should be', 'must be', 'bug:', 'fix:', 'error:']
    }
    
    found = []
    for strength, kws in keywords.items():
        for kw in kws:
            if kw in text_lower:
                found.append(f"{strength}:{kw}")
    
    has_explicit = any(f.startswith('strong') for f in found) or len(found) >= 2
    return has_explicit, found


def has_code_examples(text: str) -> bool:
    """Check for code examples in problem statement"""
    indicators = [
        '```',           # Markdown code block
        '>>>',           # Doctest
        '    def ',      # Indented function
        '    class ',    # Indented class
        'Traceback',     # Stack trace
    ]
    return any(ind in text for ind in indicators)


def has_exception_mention(text: str) -> bool:
    """Check if specific exceptions are mentioned"""
    exceptions = [
        'TypeError', 'ValueError', 'KeyError', 'AttributeError',
        'RuntimeError', 'IndexError', 'ImportError', 'AssertionError',
        'Exception', 'Error'
    ]
    return any(exc in text for exc in exceptions)


def estimate_testability(text: str, repo: str) -> str:
    """Estimate how testable the issue behavior is"""
    text_lower = text.lower()
    
    # High testability indicators
    high = ['return', 'raise', 'exception', 'output', 'result', 'assert', 'equal']
    # Low testability indicators
    low = ['performance', 'memory', 'speed', 'slow', 'visual', 'plot', 
           'figure', 'image', 'display', 'render', 'ui', 'gui']
    
    high_count = sum(1 for h in high if h in text_lower)
    low_count = sum(1 for l in low if l in text_lower)
    
    # Repo-specific adjustments
    if repo in ['matplotlib/matplotlib']:
        low_count += 2
    if repo in ['pytest-dev/pytest', 'pylint-dev/pylint']:
        high_count += 1
    
    if high_count >= 3 and low_count == 0:
        return 'high'
    elif low_count >= 2 or (low_count > 0 and high_count < 2):
        return 'low'
    return 'medium'


def score_issue(instance: Dict) -> IssueScore:
    """Score an issue for claim extraction suitability"""
    ps = instance.get('problem_statement', '') or ''
    patch = instance.get('patch', '') or ''
    repo = instance.get('repo', '')
    instance_id = instance.get('instance_id', '')
    
    score = 50  # Baseline
    reasons = []
    
    # Patch complexity
    patch_lines = count_patch_lines(patch)
    files_modified = count_files(patch)
    
    if patch_lines <= 15:
        score += 15
        reasons.append("+15: very small patch")
    elif patch_lines <= 30:
        score += 10
        reasons.append("+10: small patch")
    elif patch_lines <= 50:
        score += 5
        reasons.append("+5: medium patch")
    elif patch_lines > 100:
        score -= 15
        reasons.append("-15: large patch")
    
    if files_modified > 1:
        score -= 10
        reasons.append("-10: multi-file patch")
    
    # Explicit behavior keywords
    has_explicit, keywords = has_explicit_behavior_keywords(ps)
    if has_explicit:
        score += 15
        reasons.append(f"+15: explicit behavior ({len(keywords)} keywords)")
    elif len(keywords) >= 1:
        score += 5
        reasons.append(f"+5: some behavior keywords")
    else:
        score -= 10
        reasons.append("-10: no behavior keywords")
    
    # Code examples
    has_code = has_code_examples(ps)
    if has_code:
        score += 10
        reasons.append("+10: has code examples")
    
    # Exception mentions
    has_exc = has_exception_mention(ps)
    if has_exc:
        score += 5
        reasons.append("+5: mentions exceptions")
    
    # Testability
    testability = estimate_testability(ps, repo)
    if testability == 'high':
        score += 10
        reasons.append("+10: high testability")
    elif testability == 'low':
        score -= 15
        reasons.append("-15: low testability")
    
    # Repo tier
    repo_tier = REPO_TIERS.get(repo, 2)
    if repo_tier == 1:
        score += 10
        reasons.append("+10: tier-1 repo")
    elif repo_tier == 3:
        score -= 10
        reasons.append("-10: tier-3 repo")
    
    # Django submodule check
    if repo == 'django/django':
        module = extract_django_module(patch)
        if any(easy in module for easy in DJANGO_EASY_MODULES):
            score += 5
            reasons.append(f"+5: easy django module ({module})")
        elif any(hard in module for hard in DJANGO_HARD_MODULES):
            score -= 5
            reasons.append(f"-5: hard django module ({module})")
    
    # Clamp score
    score = max(0, min(100, score))
    
    # Determine tier based on final score
    if score >= 70:
        tier = 1
    elif score >= 50:
        tier = 2
    else:
        tier = 3
    
    return IssueScore(
        instance_id=instance_id,
        repo=repo,
        score=score,
        patch_lines=patch_lines,
        files_modified=files_modified,
        has_explicit_behavior=has_explicit,
        has_code_examples=has_code,
        has_exception_mention=has_exc,
        testability=testability,
        tier=tier,
        reasons=reasons
    )


def main():
    parser = argparse.ArgumentParser(description='Score SWE-bench Lite issues')
    parser.add_argument('--output', '-o', default='scored_issues.json',
                        help='Output JSON file')
    parser.add_argument('--top', '-n', type=int, default=None,
                        help='Only output top N issues')
    parser.add_argument('--tier', '-t', type=int, choices=[1, 2, 3],
                        help='Filter by tier')
    parser.add_argument('--repo', '-r', type=str,
                        help='Filter by repo (substring match)')
    parser.add_argument('--min-score', type=int, default=0,
                        help='Minimum score threshold')
    args = parser.parse_args()
    
    print("Loading SWE-bench Lite...")
    dataset = load_dataset("princeton-nlp/SWE-bench_Lite", split="test")
    print(f"Loaded {len(dataset)} instances")
    
    print("Scoring issues...")
    scores = [score_issue(inst) for inst in dataset]
    
    # Sort by score descending
    scores.sort(key=lambda x: x.score, reverse=True)
    
    # Apply filters
    if args.tier:
        scores = [s for s in scores if s.tier == args.tier]
    if args.repo:
        scores = [s for s in scores if args.repo.lower() in s.repo.lower()]
    if args.min_score:
        scores = [s for s in scores if s.score >= args.min_score]
    if args.top:
        scores = scores[:args.top]
    
    # Statistics
    by_repo = defaultdict(list)
    for s in scores:
        by_repo[s.repo].append(s)
    
    print("\n" + "="*70)
    print("SUMMARY BY REPOSITORY")
    print("="*70)
    
    for repo in sorted(by_repo.keys()):
        repo_scores = by_repo[repo]
        avg = sum(s.score for s in repo_scores) / len(repo_scores)
        t1 = sum(1 for s in repo_scores if s.tier == 1)
        t2 = sum(1 for s in repo_scores if s.tier == 2)
        t3 = sum(1 for s in repo_scores if s.tier == 3)
        print(f"\n{repo}")
        print(f"  Count: {len(repo_scores)}, Avg Score: {avg:.1f}")
        print(f"  Tier 1/2/3: {t1}/{t2}/{t3}")
        if t1 > 0:
            easy = [s.instance_id for s in repo_scores if s.tier == 1][:3]
            print(f"  Easy examples: {', '.join(easy)}")
    
    print("\n" + "="*70)
    print(f"TOP {min(20, len(scores))} ISSUES FOR CLAIM EXTRACTION")
    print("="*70)
    
    for i, s in enumerate(scores[:20], 1):
        print(f"\n{i}. {s.instance_id}")
        print(f"   Score: {s.score} | Tier: {s.tier} | "
              f"Patch: {s.patch_lines} lines | Testability: {s.testability}")
        print(f"   Explicit: {s.has_explicit_behavior} | "
              f"Code: {s.has_code_examples} | Exceptions: {s.has_exception_mention}")
    
    # Save to JSON
    output = {
        'metadata': {
            'total_scored': len(scores),
            'filters_applied': {
                'tier': args.tier,
                'repo': args.repo,
                'min_score': args.min_score,
                'top_n': args.top
            }
        },
        'by_repo_summary': {
            repo: {
                'count': len(issues),
                'avg_score': sum(s.score for s in issues) / len(issues),
                'tier_1_count': sum(1 for s in issues if s.tier == 1),
                'tier_2_count': sum(1 for s in issues if s.tier == 2),
                'tier_3_count': sum(1 for s in issues if s.tier == 3),
            }
            for repo, issues in by_repo.items()
        },
        'issues': [asdict(s) for s in scores]
    }
    
    with open(args.output, 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"\n✅ Results saved to {args.output}")
    print(f"   Total issues: {len(scores)}")
    print(f"   Tier 1 (easy): {sum(1 for s in scores if s.tier == 1)}")
    print(f"   Tier 2 (medium): {sum(1 for s in scores if s.tier == 2)}")
    print(f"   Tier 3 (hard): {sum(1 for s in scores if s.tier == 3)}")


if __name__ == '__main__':
    main()
