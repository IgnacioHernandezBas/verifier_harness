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
