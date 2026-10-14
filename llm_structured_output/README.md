# LLM Structured Output

From the repository root, activate the environment using `source .venv/bin/activate`, then run `cd llm_structured_output`.

Update the `user_query` in `classifier.py` and run using `python classifier.py`.

Run the tests using `PYTHONPATH=$(pwd) pytest tests/test_llm_loop.py -q`.

Run an evaluation using:

```bash
python evaluation_runner.py --run-type run \
  --prompt-file-name prompt_v2.md \
  --evaluation-data-file-name evaluation_data_v1.json \
  --model-name qwen3.5:9b
```

Artifacts are saved under `runs/<run-id>/`, including `manifest.json`, `evaluation_results.jsonl`, and `summary.json`.

Print priority mismatches for a completed run using:

```bash
python evaluation_runner.py --run-type mismatches \
  --run-id 2026-10-14T072557Z
```

## Evaluation iteration

- Reviewed run `2026-10-13T030159Z`.
- Clarified cancellation priority in `prompt_v2.md`.
- Changed password-reset priority to medium.
- Changed privacy-question priority to low.
- Added a next-month deadline to the trial-cancellation example.
- Reduced ambiguity between low and medium priority.

Reran evaluations with `prompt_v2.md`

- Reviewed run `2026-10-14T072557Z`.
- Priority accuracy increased from `0.7` to `0.9` after prompt clarification and dataset-label changes.
- Still two mismatches, which on evaluation, can be resolved by better prompt clarity. With more and more examples in evaluation, this exercise can just continue forever.

Reran evaluations with a smaller model

- Run `2026-10-14T073709Z` and Prompt `prompt_v2.md`.
- Category accuracy dropped from `0.95` to `0.85`.
- The misclassifications cluster around the `other` category. The smaller model may struggle with category boundaries and require more explicit prompts.
