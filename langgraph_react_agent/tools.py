"""Custom tools for testing ReAct Agent."""

from langchain.tools import tool

@tool
def add_numbers(nums: list[int]) -> int:
    """Adds a list of numbers and returns their sum."""
    return sum(nums)

@tool
def multiply_numbers(nums: list[int]) -> int:
    """Multiplies a list of numbers and returns thier product."""
    ans = 1
    for num in nums:
        ans *= num
    return ans
