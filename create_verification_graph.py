#!/usr/bin/env python3
"""
Create visualization comparing our baseline test results with official SWE-bench results.
Excludes instances that failed due to Docker rate limiting.
"""

import json
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path
from collections import defaultdict

# Load official results
official_file = "/fs/nexus-scratch/ihbas/generated_patches/experiments/evaluation/lite/20250911_isea_claude-3.5-sonnet-20241022/results/results.json"
with open(official_file) as f:
    official_data = json.load(f)

official_resolved = set(official_data["resolved"])

# Collect our results (excluding rate-limited instances)
results_dir = Path("/fs/nexus-scratch/ihbas/podman_test_results/20250911_isea_claude-3.5-sonnet-20241022")
our_results = {}

for instance_dir in sorted(results_dir.iterdir()):
    if not instance_dir.is_dir():
        continue

    status_file = instance_dir / "status.txt"
    if not status_file.exists():
        continue

    instance_id = instance_dir.name
    status = status_file.read_text().strip()

    # Only include valid results (not rate limited or other errors)
    if status in ["PASS", "FAIL"]:
        our_results[instance_id] = status

# Categorize by repo
repo_data = defaultdict(lambda: {"total": 0, "tested": 0, "our_pass": 0, "our_fail": 0,
                                  "official_pass": 0, "match": 0, "mismatch": 0})

for instance_id, our_status in our_results.items():
    repo = instance_id.rsplit('-', 1)[0]
    repo_data[repo]["tested"] += 1

    official_status = "PASS" if instance_id in official_resolved else "FAIL"

    if our_status == "PASS":
        repo_data[repo]["our_pass"] += 1
    else:
        repo_data[repo]["our_fail"] += 1

    if official_status == "PASS":
        repo_data[repo]["official_pass"] += 1

    if our_status == official_status:
        repo_data[repo]["match"] += 1
    else:
        repo_data[repo]["mismatch"] += 1

# Calculate totals
total_tested = len(our_results)
total_match = sum(r["match"] for r in repo_data.values())
total_mismatch = sum(r["mismatch"] for r in repo_data.values())
accuracy = total_match / total_tested * 100 if total_tested > 0 else 0

print(f"Total instances tested: {total_tested}")
print(f"Total matches: {total_match}")
print(f"Total mismatches: {total_mismatch}")
print(f"Overall accuracy: {accuracy:.1f}%")

# Create figure with multiple subplots
fig = plt.figure(figsize=(18, 12))

# 1. Overall accuracy pie chart
ax1 = fig.add_subplot(2, 3, 1)
colors = ['#2ecc71', '#e74c3c']
sizes = [total_match, total_mismatch]
labels = [f'Match\n({total_match})', f'Mismatch\n({total_mismatch})']
wedges, texts, autotexts = ax1.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%',
                                    startangle=90, explode=(0.05, 0.05), textprops={'fontsize': 12, 'weight': 'bold'})
ax1.set_title(f'Overall Accuracy: {accuracy:.1f}%\n({total_tested} instances tested)', fontsize=14, fontweight='bold')

# 2. Per-repo accuracy bar chart
ax2 = fig.add_subplot(2, 3, 2)
repos = sorted(repo_data.keys(), key=lambda x: repo_data[x]["tested"], reverse=True)
repo_names = [r.replace("__", "\n") for r in repos]
accuracies = [repo_data[r]["match"] / repo_data[r]["tested"] * 100 for r in repos]
tested_counts = [repo_data[r]["tested"] for r in repos]

bars = ax2.bar(range(len(repos)), accuracies, color=['#27ae60' if a == 100 else '#3498db' for a in accuracies])
ax2.set_xticks(range(len(repos)))
ax2.set_xticklabels(repo_names, rotation=45, ha='right', fontsize=9)
ax2.set_ylabel('Accuracy (%)', fontsize=11)
ax2.set_title('Per-Repository Accuracy', fontsize=14, fontweight='bold')
ax2.set_ylim(0, 110)
ax2.axhline(y=100, color='green', linestyle='--', alpha=0.5, linewidth=2, label='100% accuracy')
ax2.grid(axis='y', alpha=0.3)
ax2.legend()

# Add count labels on bars
for i, (bar, count) in enumerate(zip(bars, tested_counts)):
    ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 2,
             f'n={count}', ha='center', va='bottom', fontsize=8, fontweight='bold')

# 3. Comparison: Our results vs Official results
ax3 = fig.add_subplot(2, 3, 3)
our_pass = sum(1 for s in our_results.values() if s == "PASS")
our_fail = sum(1 for s in our_results.values() if s == "FAIL")
official_pass = sum(1 for i in our_results.keys() if i in official_resolved)
official_fail = len(our_results) - official_pass

x = np.arange(2)
width = 0.35

bars1 = ax3.bar(x - width/2, [our_pass, our_fail], width, label='Our Results', color=['#27ae60', '#c0392b'])
bars2 = ax3.bar(x + width/2, [official_pass, official_fail], width, label='Official SWE-bench',
                color=['#2ecc71', '#e74c3c'], alpha=0.7, hatch='//')

ax3.set_ylabel('Number of Instances', fontsize=11)
ax3.set_title('Our Results vs Official SWE-bench Results', fontsize=14, fontweight='bold')
ax3.set_xticks(x)
ax3.set_xticklabels(['PASS', 'FAIL'], fontsize=11)
ax3.legend(fontsize=10)
ax3.grid(axis='y', alpha=0.3)

# Add value labels
for bar in bars1:
    ax3.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 2,
             str(int(bar.get_height())), ha='center', va='bottom', fontweight='bold', fontsize=11)
for bar in bars2:
    ax3.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 2,
             str(int(bar.get_height())), ha='center', va='bottom', fontsize=10)

# 4. Confusion matrix style visualization
ax4 = fig.add_subplot(2, 3, 4)

# Calculate confusion matrix values
true_pos = sum(1 for i, s in our_results.items() if s == "PASS" and i in official_resolved)
true_neg = sum(1 for i, s in our_results.items() if s == "FAIL" and i not in official_resolved)
false_pos = sum(1 for i, s in our_results.items() if s == "PASS" and i not in official_resolved)
false_neg = sum(1 for i, s in our_results.items() if s == "FAIL" and i in official_resolved)

cm = np.array([[true_pos, false_neg], [false_pos, true_neg]])
im = ax4.imshow(cm, cmap='RdYlGn', aspect='auto', vmin=0, vmax=max(cm.flatten()) * 1.1)

ax4.set_xticks([0, 1])
ax4.set_yticks([0, 1])
ax4.set_xticklabels(['Official PASS', 'Official FAIL'], fontsize=10)
ax4.set_yticklabels(['Our PASS', 'Our FAIL'], fontsize=10)
ax4.set_xlabel('Official SWE-bench Result', fontsize=11)
ax4.set_ylabel('Our Result', fontsize=11)
ax4.set_title('Agreement Matrix', fontsize=14, fontweight='bold')

# Add text annotations
for i in range(2):
    for j in range(2):
        color = 'white' if cm[i, j] > max(cm.flatten()) / 2 else 'black'
        ax4.text(j, i, str(cm[i, j]), ha='center', va='center', color=color, fontsize=24, fontweight='bold')

# Add colorbar
cbar = plt.colorbar(im, ax=ax4)
cbar.set_label('Count', fontsize=10)

# 5. Repos with 100% accuracy
ax5 = fig.add_subplot(2, 3, 5)
perfect_repos = [r for r in repos if repo_data[r]["match"] == repo_data[r]["tested"]]
perfect_counts = [repo_data[r]["tested"] for r in perfect_repos]
perfect_names = [r.replace("__", "\n") for r in perfect_repos]

bars5 = ax5.barh(range(len(perfect_repos)), perfect_counts, color='#27ae60')
ax5.set_yticks(range(len(perfect_repos)))
ax5.set_yticklabels(perfect_names, fontsize=9)
ax5.set_xlabel('Number of Instances', fontsize=11)
ax5.set_title(f'Repositories with 100% Accuracy ({len(perfect_repos)} repos)', fontsize=14, fontweight='bold')
ax5.grid(axis='x', alpha=0.3)

# Add value labels
for i, (bar, count) in enumerate(zip(bars5, perfect_counts)):
    ax5.text(bar.get_width() + 1, bar.get_y() + bar.get_height()/2,
             str(count), ha='left', va='center', fontweight='bold', fontsize=9)

# 6. Summary statistics table
ax6 = fig.add_subplot(2, 3, 6)
ax6.axis('off')

summary_data = [
    ['Metric', 'Value'],
    ['─' * 30, '─' * 15],
    ['Total Tested', f'{total_tested}'],
    ['Total Match', f'{total_match}'],
    ['Total Mismatch', f'{total_mismatch}'],
    ['Overall Accuracy', f'{accuracy:.1f}%'],
    ['', ''],
    ['True Positives', f'{true_pos}'],
    ['True Negatives', f'{true_neg}'],
    ['False Positives', f'{false_pos}'],
    ['False Negatives', f'{false_neg}'],
    ['', ''],
    ['Repos with 100%', f'{len(perfect_repos)}/{len(repos)}'],
    ['Total Repos', f'{len(repos)}'],
]

table = ax6.table(cellText=summary_data, cellLoc='left', loc='center',
                  colWidths=[0.6, 0.4])
table.auto_set_font_size(False)
table.set_fontsize(11)
table.scale(1, 2.5)

# Style header row
for i in range(2):
    table[(0, i)].set_facecolor('#3498db')
    table[(0, i)].set_text_props(weight='bold', color='white')

# Style data rows
for i in range(2, len(summary_data)):
    if summary_data[i][0] == '':
        continue
    table[(i, 0)].set_text_props(weight='bold')

ax6.set_title('Summary Statistics', fontsize=14, fontweight='bold', pad=20)

# Add overall title
fig.suptitle('SWE-bench Baseline Test Verification Results\n' +
             'Comparing Our Implementation vs Official SWE-bench Results\n' +
             '(Excluding Docker Rate-Limited Instances)',
             fontsize=16, fontweight='bold', y=0.98)

plt.tight_layout(rect=[0, 0, 1, 0.96])
output_file = '/fs/nexus-scratch/ihbas/swebench_verification_results.png'
plt.savefig(output_file, dpi=150, bbox_inches='tight')
print(f"\n✓ Graph saved to: {output_file}")

# Print detailed breakdown
print("\n" + "="*70)
print("DETAILED BREAKDOWN BY REPOSITORY")
print("="*70)
for repo in repos:
    data = repo_data[repo]
    acc = data["match"] / data["tested"] * 100
    status = "✓ 100%" if acc == 100 else f"  {acc:.1f}%"
    print(f"{status} {repo:40s}: {data['match']:3d}/{data['tested']:3d} match "
          f"({data['our_pass']:3d} PASS, {data['our_fail']:3d} FAIL)")

print("\n" + "="*70)
print("KEY FINDINGS")
print("="*70)
print(f"• {len(perfect_repos)} out of {len(repos)} repositories have 100% accuracy")
print(f"• Overall accuracy: {accuracy:.1f}% across {total_tested} instances")
print(f"• {total_match} instances match official results exactly")
print(f"• {false_pos} false positives (we say PASS, official says FAIL)")
print(f"• {false_neg} false negatives (we say FAIL, official says PASS)")
