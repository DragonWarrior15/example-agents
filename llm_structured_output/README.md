# LLM Structured Output

Activate the environment using `source .venv/bin/activate`

Update the `user_query` in `classifier.py` and run using `python classifier.py`.

To run the tests, make sure to set the environment variable `PYTHONPATH=$(pwd)` before running the tests.

To run evaluations, use `python evaluation_runner.py run` and it will create the file `evaluation_results.json`.

To print mismatches in evaluation outputs (priority), use `python evaluation_runner.py mismatches` which reads from the evaluation results file.
