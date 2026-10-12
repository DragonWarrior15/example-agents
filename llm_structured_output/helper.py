"""Helper utilities for classifier."""

from enum import Enum

from ollama import ChatResponse, chat
from pydantic import BaseModel, Field

TRIAGE_PROMPT = """
You are an expert customer support triage agent. Given a customer support request, produce the following in a structured JSON format

- reason
    - short explanation
- category
    - billing
    - technical
    - account_access
    - cancellation
    - other
- priority
    - low
    - medium
    - high
- requires_human_review
    - boolean

Useful semantic rules:
- other should require human review.
- Suspected account compromise should be high priority.
- Cancellation does not automatically mean high priority.
- The reason must be present but short.

You will be provided the user query next.
"""


class CategoryEnum(str, Enum):
    billing = "billing"
    technical = "technical"
    account_access = "account_access"
    cancellation = "cancellation"
    other = "other"


class PriorityEnum(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


class TriageOutput(BaseModel):
    reason: str = Field(max_length=50)
    category: CategoryEnum
    priority: PriorityEnum
    requires_human_review: bool


class LoopOutput(BaseModel):
    response: TriageOutput | None
    error_parsing: str | None
    loop_count: int


def parse_output(str_to_parse: str) -> tuple[TriageOutput | None, str | None]:
    """Utility to try to parse agent output as a valid JSON.

    Returns the Triage Output and the error"""

    input_original = str_to_parse

    try:
        # first check for markdown tags
        if str_to_parse.startswith("```"):
            # remove the first and last lines
            str_to_parse = str_to_parse.split("\n")
            str_to_parse = str_to_parse[1:-1]
            str_to_parse = "\n".join(str_to_parse)

        # next, directly parse into a pydantic model
        triage_output = TriageOutput.model_validate_json(str_to_parse)

        # enforce further rules on the output
        if validate_triage_output_values(triage_output):
            return triage_output, None

    except Exception as e:
        error_str = (
            f"Did not find a valid JSON in the input: {input_original}"
            f", got error {str(e)}"
        )
        return None, error_str


def validate_triage_output_values(triage_output: TriageOutput) -> bool:
    """Apply hard constraints on TriageOutput."""

    if (
        triage_output.category == CategoryEnum.other
        and not triage_output.requires_human_review
    ):
        raise ValueError(
            "Violated: Category is other but requires human review is set to False."
        )

    return True


def form_messages(user_query: str, error_parsing: str | None) -> list[dict]:
    """Helper to form the messages for chat input."""
    return (
        [
            {
                "role": "system",
                "content": TRIAGE_PROMPT,
            }
        ]
        + (
            [
                {
                    "role": "system",
                    "content": f"The last attempt had the following error {error_parsing}",
                }
            ]
            if error_parsing
            else []
        )
        + [
            {
                "role": "user",
                "content": user_query,
            }
        ]
    )


def run_llm_and_get_response_content(messages: list) -> str:
    """Run the messages through LLM and parse the output."""
    response: ChatResponse = chat(
        model="qwen3.5:9b",
        messages=messages,
        stream=False,
    )

    return response.message.content


def run_llm_loop(user_query: str) -> LoopOutput:
    """Run the loop for getting the triage output."""

    loop_output = None
    error_parsing = None

    for step in [1, 2]:
        messages = form_messages(user_query, error_parsing)

        chat_response = run_llm_and_get_response_content(messages)

        response_parsed, error_parsing = parse_output(chat_response)

        loop_output = LoopOutput(
            response=response_parsed,
            error_parsing=error_parsing,
            loop_count=step,
        )

        # break the loop if we got a successful parse
        if response_parsed:
            break

    return loop_output
