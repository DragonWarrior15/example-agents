"""Trace a few simple functions in phoenix."""

from phoenix.otel import register

tracer_provider = register(protocol="http/protobuf", project_name="sample-phoenix-trace")
tracer = tracer_provider.get_tracer(__name__)

@tracer.chain
def add_two_numbers(a: int, b: int) -> int:
    return a + b


@tracer.chain
def calculate_sum_of_list(nums: list[int]):
    if not nums:
        return 0
    if len(nums) == 1:
        return nums[0]
    if len(nums) == 2:
        return add_two_numbers(nums[0], nums[1])
    return add_two_numbers(
        add_two_numbers(nums[0], nums[1]), calculate_sum_of_list(nums[2:])
    )

if __name__ == "__main__":
    _ = calculate_sum_of_list([15, 23, 41, 37])
