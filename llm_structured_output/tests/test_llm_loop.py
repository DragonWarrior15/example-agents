"""Tests for the bounded LLM retry loop."""

from unittest.mock import Mock

import helper

VALID_RESPONSE = """{
    "reason": "The customer reports a duplicate charge.",
    "category": "billing",
    "priority": "medium",
    "requires_human_review": false
}"""


def test_valid_response_succeeds_on_first_attempt(monkeypatch):
    mock_llm = Mock(return_value=VALID_RESPONSE)
    monkeypatch.setattr(helper, "run_llm_and_get_response_content", mock_llm)

    result = helper.run_llm_loop("I was charged twice for my subscription.")

    assert result.response is not None
    assert result.response.category == helper.CategoryEnum.billing
    assert result.error_parsing is None
    assert result.loop_count == 1
    assert mock_llm.call_count == 1


def test_invalid_response_is_retried_with_validation_feedback(monkeypatch):
    mock_llm = Mock(side_effect=["not valid JSON", VALID_RESPONSE])
    monkeypatch.setattr(helper, "run_llm_and_get_response_content", mock_llm)

    result = helper.run_llm_loop("I was charged twice for my subscription.")

    assert result.response is not None
    assert result.response.category == helper.CategoryEnum.billing
    assert result.error_parsing is None
    assert result.loop_count == 2
    assert mock_llm.call_count == 2

    retry_messages = mock_llm.call_args_list[1].args[0]
    assert any(
        message["role"] == "system"
        and "last attempt had the following error" in message["content"]
        and "not valid JSON" in message["content"]
        for message in retry_messages
    )


def test_two_invalid_responses_return_explicit_failure(monkeypatch):
    mock_llm = Mock(side_effect=["not valid JSON", "still not valid JSON"])
    monkeypatch.setattr(helper, "run_llm_and_get_response_content", mock_llm)

    result = helper.run_llm_loop("I was charged twice for my subscription.")

    assert result.response is None
    assert result.error_parsing is not None
    assert "still not valid JSON" in result.error_parsing
    assert result.loop_count == 2
    assert mock_llm.call_count == 2
