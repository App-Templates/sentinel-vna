"""
Shared LLM retry utility with exponential backoff.
Wraps Anthropic SDK calls for all agents.
"""

import time
from typing import Optional

from backend.utils.logger import get_logger

logger = get_logger("utils.llm_retry")


def call_llm_with_retry(
    model: str,
    prompt: str,
    system: Optional[str] = None,
    max_tokens: int = 1024,
    max_retries: int = 3,
    base_delay: float = 1.0,
    timeout: float = 30.0,
) -> Optional[str]:
    """Call Anthropic API with exponential backoff retry.

    Returns the text response, or None if all retries fail.
    Raises no exceptions -- caller should handle None return.
    """
    from anthropic import Anthropic, APIError, APITimeoutError, RateLimitError

    client = Anthropic(timeout=timeout)

    kwargs = {
        "model": model,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}],
    }
    if system:
        kwargs["system"] = system

    for attempt in range(max_retries):
        try:
            response = client.messages.create(**kwargs)
            return response.content[0].text
        except RateLimitError as e:
            delay = base_delay * (2 ** attempt)
            logger.warning(
                "Rate limited (attempt %d/%d), retrying in %.1fs: %s",
                attempt + 1, max_retries, delay, e,
            )
            time.sleep(delay)
        except APITimeoutError as e:
            delay = base_delay * (2 ** attempt)
            logger.warning(
                "API timeout (attempt %d/%d), retrying in %.1fs: %s",
                attempt + 1, max_retries, delay, e,
            )
            time.sleep(delay)
        except APIError as e:
            if e.status_code and e.status_code >= 500:
                delay = base_delay * (2 ** attempt)
                logger.warning(
                    "Server error %d (attempt %d/%d), retrying in %.1fs",
                    e.status_code, attempt + 1, max_retries, delay,
                )
                time.sleep(delay)
            else:
                logger.error("Non-retryable API error: %s", e)
                return None
        except Exception as e:
            logger.error("Unexpected error calling LLM: %s", e)
            return None

    logger.error("All %d retry attempts exhausted", max_retries)
    return None
