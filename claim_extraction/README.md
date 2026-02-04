# Claim Extraction (v2.1)

This package contains the modular claim extractor used by the Streamlit demo and
the Slurm workflows. The pipeline expects an `instances.json` file where each
entry bundles the GitHub issue text, metadata, patch, and **buggy code context**.

## 1. Prepare `instances.json`

Use the helper CLI to pull SWE-bench Lite samples and build the prompt context:

```bash
cd /fs/nexus-scratch/ihbas/verifier_harness

python -m claim_extraction.prepare_instances \
  --dataset princeton-nlp/SWE-bench_Lite \
  --split test \
  --repo "astropy/astropy" \
  --limit 5 \
  --output claim_extraction/instances.json \
  --repos-dir /fs/nexus-scratch/ihbas/repos_claim_cache
```

Key flags:

| Flag | Description |
|------|-------------|
| `--instances-file FILE` | Optional newline-delimited list of instance IDs to include |
| `--repo SUBSTR` | Only keep issues whose `repo` contains the substring |
| `--tier TIER` | Filter by SWE-bench tier (`instance["tier"]` or `metadata["tier"]`) |
| `--code-lines-before/after` | Control how many lines surround each diff hunk |
| `--max-code-chars` | Enforce an upper bound per-instance for the prompt context |
| `--repos-dir PATH` | Cache clones per `(repo, base_commit)` to avoid refetching |
| `--keep-repos` | Keep the cached clones after finishing (default: remove clones created during the run) |
| `--dry-run` | Skip cloning/writing and just list which instances would be processed |

The output file is a JSON **list** (or can be wrapped in `{"instances": [...]}`) so that
`claim_extraction.cli` and the sbatch scripts can ingest it directly.

## 2. Run the extractor (local)

```bash
python -m claim_extraction.cli \
  --config claim_extraction/configs/claim_extraction.yaml \
  --input claim_extraction/instances.json \
  --out claim_extraction/claims_out \
  --limit 20
```

Set `CLAIM_LLM_BACKEND`, `CLAIM_LLM_ENDPOINT`, and `CLAIM_LLM_MODEL` in the
environment to point at your running LLM service (the config defaults to a
local vLLM endpoint).

## 3. Run on Slurm with vLLM

For end-to-end runs on the UMD cluster:

1. Submit the GPU job that starts the vLLM server:
   ```bash
   sbatch claim_extraction/scripts_slurm/start_vllm_server.sbatch
   ```
2. Use the hostname printed in that job’s log to fill `VLLM_HOST`, then submit
   the CPU-only extraction job:
   ```bash
   VLLM_HOST=gammagpu01 sbatch claim_extraction/scripts_slurm/extract_claims.sbatch
   ```

The all-in-one helper (`start_vllm_claim_extractor.sbatch`) runs both the vLLM
server and the extractor steps on the same GPU node, ideal for small batches.

## Schema versions (v2.1 vs v2.2)

- **v2.1** (default): `claim_extraction/configs/claim_extraction.yaml` keeps the
  original zero-shot pipeline and uses `claim_prompt_v2_1.jinja`. Use this when
  you need the exact legacy behavior (no new fields in the JSON output).
- **v2.2**: `claim_extraction/configs/claim_extraction_v2_2.yaml` switches the
  schema version to 2.2, sets `claim_prompt_v2_2.jinja`, and enables a
  deterministic `issue_context` bundle plus per-claim `issue_context_refs`.

Run v2.2 by pointing the CLI to the new config, e.g.:

```bash
python -m claim_extraction.cli \
  --config claim_extraction/configs/claim_extraction_v2_2.yaml \
  --input claim_extraction/instances.json \
  --out claim_extraction/claims_out_v2_2
```

When using v2.2 each instance JSON gains:

- `schema_version: "2.2"`
- `issue_context`: a single per-instance object that captures fenced code
  blocks, CLI commands, expected output snippets, stack traces, and inline code
  references parsed directly from the problem statement.
- `issue_context_refs` inside each claim, providing arrays of IDs that reference
  the relevant `issue_context` entries (`cli_command_ids`,
  `expected_output_block_ids`, `code_block_ids`, `traceback_ids`). Claims only
  store these pointers—there is no duplication of large blocks in each claim.
