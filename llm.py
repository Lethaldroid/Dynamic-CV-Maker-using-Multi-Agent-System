import requests
import time
from config import BASE_URL, MODEL


def call_llm(messages: list[dict], temperature: float = 0.3, timeout: int = 120, max_retries: int = 3) -> str:
    url = f"{BASE_URL}/chat/completions"
    payload = {"model": MODEL, "messages": messages, "temperature": temperature}
    retry_statuses = {429, 500, 502, 503, 504}

    last_error: Exception | None = None

    for attempt in range(1, max_retries + 1):
        try:
            response = requests.post(
                url,
                headers={"Content-Type": "application/json"},
                json=payload,
                timeout=timeout,
            )

            if response.status_code == 403:
                deny = response.headers.get("x-deny-reason", "unknown")
                raise RuntimeError(f"Proxy rejected (403): {deny}.")

            if response.status_code in retry_statuses:
                body = response.text.strip()
                raise RuntimeError(
                    f"Transient proxy error {response.status_code} on attempt {attempt}/{max_retries}: "
                    f"{body or 'no response body'}"
                )

            response.raise_for_status()

            response_payload = response.json()
            try:
                return response_payload["choices"][0]["message"]["content"]
            except (KeyError, IndexError, TypeError) as exc:
                raise RuntimeError(f"Unexpected proxy response shape: {response_payload}") from exc

        except (requests.exceptions.RequestException, RuntimeError) as exc:
            last_error = exc
            if attempt < max_retries:
                time.sleep(2 ** (attempt - 1))
                continue
            break

    raise RuntimeError(f"LLM proxy request failed after {max_retries} attempts: {last_error}") from last_error