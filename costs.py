import time

# Anthropic claude-sonnet-4-6 pricing
_ANTHROPIC_INPUT_COST_PER_TOKEN = 3.0 / 1_000_000   # $3 per million input tokens
_ANTHROPIC_OUTPUT_COST_PER_TOKEN = 15.0 / 1_000_000  # $15 per million output tokens

# Fly.io shared-cpu-1x 256MB pricing
_FLY_COST_PER_SECOND = 0.00000075  # $1.94/month

THRESHOLDS = [1.0, 5.0, 10.0]

_start_time = time.time()
_anthropic_cost = 0.0
_warned_thresholds: set = set()


def record_anthropic_usage(input_tokens: int, output_tokens: int):
    global _anthropic_cost
    _anthropic_cost += (
        input_tokens * _ANTHROPIC_INPUT_COST_PER_TOKEN
        + output_tokens * _ANTHROPIC_OUTPUT_COST_PER_TOKEN
    )


def _fly_cost() -> float:
    return (time.time() - _start_time) * _FLY_COST_PER_SECOND


def total_cost() -> float:
    return _anthropic_cost + _fly_cost()


def check_thresholds() -> float | None:
    """Returns the threshold just crossed, or None if no new threshold hit."""
    total = total_cost()
    for threshold in sorted(THRESHOLDS):
        if total >= threshold and threshold not in _warned_thresholds:
            _warned_thresholds.add(threshold)
            return threshold
    return None


def cost_summary() -> str:
    return (
        f"Anthropic: ${_anthropic_cost:.4f} | "
        f"Fly.io: ${_fly_cost():.4f} | "
        f"Total: ${total_cost():.4f}"
    )
