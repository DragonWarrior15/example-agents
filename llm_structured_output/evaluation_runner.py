"""Evaluation runner for Triage Agent outputs.

Read the dataset of user queries with ground truths and evaluate outputs
to calculate standard classification metrics.
"""

import argparse
import logging
from pathlib import Path

from helper import CategoryEnum, PriorityEnum, run_llm_loop
from pydantic import BaseModel, TypeAdapter

DATASET_PATH_EVALUATION_DATA = Path(__file__).with_name("evaluation_data.json")
DATASET_PATH_EVALUATION_RESULTS = Path(__file__).with_name(
    "evaluation_output.json"
)

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
    expected: EvaluationDataFields
    actual: EvaluationDataFields


def run_evaluation():
    # read the evaluation dataset
    evaluation_dataset = TypeAdapter(list[EvaluationData]).validate_json(
        DATASET_PATH_EVALUATION_DATA.read_text()
    )

    # for each case in the evaluation dataset, generate the outputs and build
    # the EvaluationResult instance
    evaluation_results: list[EvaluationResult] = []

    for case in evaluation_dataset:
        loop_output = run_llm_loop(case.input)

        if loop_output.response:
            case_result = EvaluationResult(
                id=case.id,
                expected=case.expected,
                actual=EvaluationDataFields(
                    category=loop_output.response.category,
                    priority=loop_output.response.priority,
                    requires_human_review=loop_output.response.requires_human_review,
                ),
            )

            evaluation_results.append(case_result)

    # save the results back to a json
    adapter = TypeAdapter(list[EvaluationResult])
    json_text = adapter.dump_json(evaluation_results, indent=2).decode()
    DATASET_PATH_EVALUATION_RESULTS.write_text(json_text)

    # get summary statistics, divide by len(evaluation_dataset) to account for
    # incorrect/failed responses also

    # category accuracy
    category_accuracy = sum(
        [
            case.expected.category == case.actual.category
            for case in evaluation_results
        ]
    ) / len(evaluation_dataset)
    logger.info(f"CATEGORY ACCURACY: {category_accuracy}")

    # priority accuracy
    priority_accuracy = sum(
        [
            case.expected.priority == case.actual.priority
            for case in evaluation_results
        ]
    ) / len(evaluation_dataset)
    logger.info(f"PRIORITY ACCURACY: {priority_accuracy}")

    # priority accuracy
    review_accuracy = sum(
        [
            case.expected.requires_human_review
            == case.actual.requires_human_review
            for case in evaluation_results
        ]
    ) / len(evaluation_dataset)
    logger.info(f"REQUIRES HUMAN REVIEW ACCURACY: {review_accuracy}")

def print_misclassified_examples():
    evaluation_results = TypeAdapter(list[EvaluationResult]).validate_json(
        DATASET_PATH_EVALUATION_RESULTS.read_text()
    )

    evaluation_dataset = TypeAdapter(list[EvaluationData]).validate_json(
        DATASET_PATH_EVALUATION_DATA.read_text()
    )

    for result in evaluation_results:
        if result.expected.priority != result.actual.priority:
            logger.info(
                f"PRIORITY MISMATCH at ID {result.id}: \n"
                f"User Query: {[dataset.input for dataset in evaluation_dataset if dataset.id == result.id]}\n"
                f"Expected {result.expected.priority}\n"
                f", got {result.actual.priority}"
            )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run or inspect the customer-support triage evaluation."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser(
        "run",
        help="Run the evaluation and save its results.",
    )
    subparsers.add_parser(
        "mismatches",
        help="Print priority mismatches from the saved evaluation results.",
    )

    args = parser.parse_args()

    if args.command == "run":
        run_evaluation()
    elif args.command == "mismatches":
        print_misclassified_examples()
    
