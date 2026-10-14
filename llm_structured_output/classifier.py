"""Customer support ticket triage loop example."""

from helper import run_llm_loop

user_query = "I was charged twice for my subscription."

# run a loop with exactly two steps, the second step executes if the first
# step/attempt is unable to parse the JSON correctly
loop_output = run_llm_loop(
    user_query, prompt_file_name="prompt_v1.md", model_name="qwen3.5:9b"
)


if loop_output.response is not None:
    print(f"SUCCESS: {loop_output.response!r}")
else:
    print(f"FAILURE: {loop_output.error_parsing!r}")
    print(f"Took {loop_output.loop_count!r} loops")
