# LLM Structured Output

Activate the environment using `source .venv/bin/activate`

Update the `user_query` in `classifier.py` and run using `python classifier.py`.

To run the tests, make sure to set the environment variable `PYTHONPATH=$(pwd)` before running the tests.

To run evaluations, use `python evaluation_runner.py run` and it will create the file `evaluation_results.json`.

To print mismatches in evaluation outputs (priority), use `python evaluation_runner.py mismatches` which reads from the evaluation results file.

## Evaluation iteration

- Reviewed run `2026-10-13T030159Z`.
- Clarified cancellation priority in `prompt_v2.md`.
- Changed password-reset priority to medium.
- Changed privacy-question priority to low.
- Added a next-month deadline to the trial-cancellation example.
- Reduced ambiguity between low and medium priority.
