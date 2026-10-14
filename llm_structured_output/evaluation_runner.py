"""Evaluation runner for Triage Agent outputs.

Read the dataset of user queries with ground truths and evaluate outputs
to calculate standard classification metrics.
"""

import argparse
import hashlib
import logging
from datetime import datetime, timezone
from pathlib import Path

from helper import (
    CategoryEnum,
    PriorityEnum,
    get_system_prompt,
    read_evaluation_data,
    run_llm_loop,
)
from pydantic import BaseModel, TypeAdapter

RUNS_DIRECTORY = Path(__file__).with_name("runs")
MANIFEST_FILE_NAME = "manifest.json"
EVALUATION_RESULTS_FILE_NAME = "evaluation_results.jsonl"
SUMMARY_FILE_NAME = "summary.json"

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)


class EvaluationDataFields(BaseModel):
    category: CategoryEnum
    priority: PriorityEnum
    requires_human_review: bool


class EvaluationData(BaseModel):
    id: str
    input: str
    expected: EvaluationDataFields


class EvaluationResult(BaseModel):
    id: str
    input: str
    expected: EvaluationDataFields
    actual: EvaluationDataFields | None
    loop_count: int | None
    error: str | None


class EvaluationSummary(BaseModel):
    total_cases: int
    evaluated_cases: int
    pending_cases: int
    valid_results: int
    terminal_failures: int
    first_attempt_successes: int
    retry_successes: int
    unknown_attempt_counts: int
    category_accuracy: float
    priority_accuracy: float
    human_review_accuracy: float


class Manifest(BaseModel):
    run_id: str
    prompt_file: str
    model: str
    dataset_file: str
    max_attempts: int
    prompt_hash: str
    dataset_hash: str
    started_at: str
    status: str
    completed_at: str | None = None
    notes: str = ""


def build_and_save_manifest(
    prompt_file_name: str, model_name: str, evaluation_data_file_name: str
) -> Manifest:
    """Build and saves the manifest."""
    # fix the time
    now_dt = datetime.now(timezone.utc)

    # read the prompt and eval data
    prompt = get_system_prompt(prompt_file_name)
    eval_data = read_evaluation_data(evaluation_data_file_name)

    manifest = Manifest(
        run_id=now_dt.strftime("%Y-%m-%dT%H%M%SZ"),
        prompt_file=prompt_file_name,
        model=model_name,
        dataset_file=evaluation_data_file_name,
        max_attempts=2,
        prompt_hash=hashlib.sha256(prompt.encode()).hexdigest(),
        dataset_hash=hashlib.sha256(eval_data.encode()).hexdigest(),
        started_at=now_dt.isoformat(),
        status="running",
    )

    run_directory = RUNS_DIRECTORY / manifest.run_id
    run_directory.mkdir(parents=True, exist_ok=False)
    (run_directory / MANIFEST_FILE_NAME).write_text(
        manifest.model_dump_json(indent=2)
    )

    # return the manifest for downstream consumption
    return manifest


def read_evaluation_results(manifest: Manifest) -> list[EvaluationResult]:
    """Read all persisted case results for a run."""
    results_path = (
        RUNS_DIRECTORY / manifest.run_id / EVALUATION_RESULTS_FILE_NAME
    )
    if not results_path.exists():
        return []

    return [
        EvaluationResult.model_validate_json(line)
        for line in results_path.read_text().splitlines()
        if line.strip()
    ]


def run_evaluation(manifest: Manifest) -> None:
    """Run inference and persist each case result incrementally."""
    # read the evaluation dataset
    evaluation_dataset = TypeAdapter(list[EvaluationData]).validate_json(
        read_evaluation_data(manifest.dataset_file)
    )

    # for each case in the evaluation dataset, generate the outputs and build
    # the EvaluationResult instance
    run_directory = RUNS_DIRECTORY / manifest.run_id
    results_path = run_directory / EVALUATION_RESULTS_FILE_NAME

    with results_path.open("a") as results_file:
        for case in evaluation_dataset:
            loop_output = run_llm_loop(
                case.input, manifest.prompt_file, manifest.model
            )

            actual = None
            if loop_output.response is not None:
                actual = EvaluationDataFields(
                    category=loop_output.response.category,
                    priority=loop_output.response.priority,
                    requires_human_review=loop_output.response.requires_human_review,
                )

            case_result = EvaluationResult(
                id=case.id,
                input=case.input,
                expected=case.expected,
                actual=actual,
                loop_count=loop_output.loop_count,
                error=loop_output.error_parsing,
            )
            # Persist each result immediately so interrupted runs retain their
            # completed cases. Each line is an independent JSON document.
            results_file.write(case_result.model_dump_json() + "\n")
            results_file.flush()


def build_and_save_summary(manifest: Manifest) -> EvaluationSummary:
    """Calculate and persist summary statistics for an existing run."""
    run_directory = RUNS_DIRECTORY / manifest.run_id
    evaluation_dataset = TypeAdapter(list[EvaluationData]).validate_json(
        read_evaluation_data(manifest.dataset_file)
    )
    evaluation_results = read_evaluation_results(manifest)
    total_cases = len(evaluation_dataset)
    if total_cases == 0:
        raise ValueError("Cannot summarize an empty evaluation dataset.")

    category_accuracy = sum(
        [
            case.actual is not None
            and case.expected.category == case.actual.category
            for case in evaluation_results
        ]
    ) / total_cases
    logger.info(f"CATEGORY ACCURACY: {category_accuracy}")

    priority_accuracy = sum(
        [
            case.actual is not None
            and case.expected.priority == case.actual.priority
            for case in evaluation_results
        ]
    ) / total_cases
    logger.info(f"PRIORITY ACCURACY: {priority_accuracy}")

    review_accuracy = sum(
        [
            case.actual is not None
            and case.expected.requires_human_review
            == case.actual.requires_human_review
            for case in evaluation_results
        ]
    ) / total_cases
    logger.info(f"REQUIRES HUMAN REVIEW ACCURACY: {review_accuracy}")

    valid_results = sum(
        result.actual is not None for result in evaluation_results
    )
    evaluated_cases = len(evaluation_results)
    summary = EvaluationSummary(
        total_cases=total_cases,
        evaluated_cases=evaluated_cases,
        pending_cases=max(total_cases - evaluated_cases, 0),
        valid_results=valid_results,
        terminal_failures=sum(
            result.actual is None for result in evaluation_results
        ),
        first_attempt_successes=sum(
            result.actual is not None and result.loop_count == 1
            for result in evaluation_results
        ),
        retry_successes=sum(
            result.actual is not None
            and result.loop_count is not None
            and result.loop_count > 1
            for result in evaluation_results
        ),
        unknown_attempt_counts=sum(
            result.loop_count is None for result in evaluation_results
        ),
        category_accuracy=category_accuracy,
        priority_accuracy=priority_accuracy,
        human_review_accuracy=review_accuracy,
    )
    (run_directory / SUMMARY_FILE_NAME).write_text(
        summary.model_dump_json(indent=2)
    )

    expected_ids = {case.id for case in evaluation_dataset}
    result_ids = [result.id for result in evaluation_results]
    run_is_complete = (
        len(result_ids) == len(set(result_ids))
        and set(result_ids) == expected_ids
    )
    completed_manifest = manifest.model_copy(
        update={
            "status": "completed" if run_is_complete else "incomplete",
            "completed_at": (
                datetime.now(timezone.utc).isoformat()
                if run_is_complete
                else None
            ),
        }
    )
    (run_directory / MANIFEST_FILE_NAME).write_text(
        completed_manifest.model_dump_json(indent=2)
    )
    logger.info(f"RUN ARTIFACTS: {run_directory}")
    return summary


def print_misclassified_examples(run_id: str):
    run_directory = RUNS_DIRECTORY / run_id
    manifest = Manifest.model_validate_json(
        (run_directory / MANIFEST_FILE_NAME).read_text()
    )
    evaluation_results = read_evaluation_results(manifest)

    for result in evaluation_results:
        if result.actual is None:
            logger.info(
                f"TERMINAL FAILURE at ID {result.id}: {result.error}"
            )
        elif result.expected.priority != result.actual.priority:
            logger.info(
                f"PRIORITY MISMATCH at ID {result.id}: \n"
                f"User Query: {result.input}\n"
                f"Expected {result.expected.priority}\n"
                f", got {result.actual.priority}"
            )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run or inspect the customer-support triage evaluation."
    )

    parser.add_argument(
        "--run-type",
        choices=["run", "mismatches"],
        help="Run type, must be one of run or mismatches. "
        "Use run to run evaluation and save results, use mismatches to print "
        "priority mismatches from the saved evaluation results.",
        required=True,
    )

    parser.add_argument(
        "--prompt-file-name",
        choices=["prompt_v1.md", "prompt_v2.md"],
        help="Prompt file name, must be one of [prompt_v1.md, prompt_v2.md]",
        required=False,
    )

    parser.add_argument(
        "--evaluation-data-file-name",
        choices=["evaluation_data_v1.json"],
        help="Evaluation data file name, must be one of "
        "[evaluation_data_v1.json]",
        required=False,
    )

    parser.add_argument(
        "--model-name",
        choices=["qwen3.5:9b"],
        help="Model name, must be one of [qwen3.5:9b], default is qwen3.5:9b",
        default="qwen3.5:9b",
        required=False,
    )

    parser.add_argument(
        "--run-id",
        help="Existing run ID to inspect when --run-type=mismatches.",
        required=False,
    )

    args = parser.parse_args()

    if args.run_type == "run":
        if not args.prompt_file_name or not args.evaluation_data_file_name:
            parser.error(
                "--prompt-file-name and --evaluation-data-file-name are "
                "required when --run-type=run"
            )
        manifest = build_and_save_manifest(
            prompt_file_name=args.prompt_file_name,
            model_name=args.model_name,
            evaluation_data_file_name=args.evaluation_data_file_name,
        )
        run_evaluation(manifest)
        build_and_save_summary(manifest)
    elif args.run_type == "mismatches":
        if not args.run_id:
            parser.error("--run-id is required when --run-type=mismatches")
        print_misclassified_examples(args.run_id)
