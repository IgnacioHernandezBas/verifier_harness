#!/usr/bin/env python3
"""
Load the 5 validation issues from SWE-bench Lite and save them locally.
"""

import json
from datasets import load_dataset

# Issues to load
VALIDATION_ISSUES = [
    'astropy__astropy-7746',
    'psf__requests-2148',
    'pylint-dev__pylint-5859',
    'pylint-dev__pylint-6506',
    'pylint-dev__pylint-7114'
]

def main():
    print("Loading SWE-bench Lite dataset...")
    dataset = load_dataset('princeton-nlp/SWE-bench_Lite', split='test')

    validation_set = {}

    for instance in dataset:
        instance_id = instance['instance_id']
        if instance_id in VALIDATION_ISSUES:
            print(f"Found: {instance_id}")
            validation_set[instance_id] = {
                'instance_id': instance_id,
                'repo': instance['repo'],
                'base_commit': instance['base_commit'],
                'problem_statement': instance['problem_statement'],
                'patch': instance['patch'],
                'test_patch': instance.get('test_patch', ''),
                'hints_text': instance.get('hints_text', ''),
                'created_at': instance.get('created_at', ''),
                'FAIL_TO_PASS': instance.get('FAIL_TO_PASS', ''),
                'PASS_TO_PASS': instance.get('PASS_TO_PASS', '')
            }

    # Save to JSON
    output_file = 'validation_issues.json'
    with open(output_file, 'w') as f:
        json.dump(validation_set, f, indent=2)

    print(f"\n✅ Saved {len(validation_set)} issues to {output_file}")

    # Print summary
    print("\n" + "="*70)
    print("VALIDATION SET SUMMARY")
    print("="*70)
    for instance_id, data in validation_set.items():
        ps_len = len(data['problem_statement'])
        patch_lines = data['patch'].count('\n')
        print(f"\n{instance_id}")
        print(f"  Repo: {data['repo']}")
        print(f"  Problem statement: {ps_len} chars")
        print(f"  Patch: {patch_lines} lines")

if __name__ == '__main__':
    main()
