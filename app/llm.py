"""Single entry point for all model calls. Provider and model come from the MODEL env var."""
import json
import os
import re
import time

from dotenv import load_dotenv

load_dotenv()


def _friendly(e: Exception) -> str:
    m = str(e).lower()
    if "no credits" in m or "insufficient_quota" in m or "billing" in m:
        return "Out of credits. Add billing at your provider, or switch MODEL in .env."
    if "missing" in m and "api key" in m or "api key not valid" in m or "authentication" in m:
        return "API key missing or invalid. Check the key line in .env."
    if "no longer available" in m or "not found" in m or "404" in m:
        return "Model not found or retired. Pick a current model and update MODEL in .env."
    if "503" in m or "unavailable" in m or "high demand" in m:
        return "Provider is overloaded (gave up after retries). Wait a few minutes or try another model."
    if "429" in m or "rate limit" in m:
        return "Rate limit reached. Wait a minute, or use a plan with higher limits."
    if "timeout" in m or "timed out" in m:
        return "The model call timed out. Try again."
    return f"Model call failed: {str(e)[:300]}"


def _complete(system: str, user: str):
    import litellm  # imported lazily so tests can run without it

    litellm.drop_params = True
    model = os.environ["MODEL"]
    extra = {} if model.startswith("gemini/") else {"temperature": 0}
    t = time.time()
    try:
        r = litellm.completion(
            model=model,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            num_retries=5,   # retries temporary errors (503, 429) with waiting between tries
            timeout=90,      # a stuck call fails instead of hanging forever
            **extra,
        )
    except Exception as e:
        raise RuntimeError(_friendly(e)) from None
    text = r.choices[0].message.content or ""
    usage = getattr(r, "usage", None)
    tokens = getattr(usage, "total_tokens", 0) if usage else 0
    try:
        cost = litellm.completion_cost(completion_response=r) or 0.0
    except Exception:
        cost = 0.0
    return text, {"tokens": tokens, "cost": round(cost, 6), "seconds": round(time.time() - t, 2)}


def parse_json(text: str) -> dict:
    """Extract a JSON object from model output, tolerating code fences, commentary, and minor formatting issues."""
    text = text.strip()
    # 1. Try raw text directly
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 2. Try extracting from markdown code block ```json ... ``` or ``` ... ```
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if match:
        block = match.group(1).strip()
        try:
            return json.loads(block)
        except json.JSONDecodeError:
            text = block

    # 3. Find outer braces
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end > start:
        snippet = text[start : end + 1]
        try:
            return json.loads(snippet)
        except json.JSONDecodeError:
            # 4. Attempt to strip trailing commas before closing braces/brackets
            cleaned = re.sub(r",\s*([\]}])", r"\1", snippet)
            try:
                return json.loads(cleaned)
            except json.JSONDecodeError:
                pass

    raise ValueError("No valid JSON object in model output")


def ask_json(system: str, user: str):
    """Call the model and return (data, meta). Retries once if the JSON is invalid."""
    text, meta = _complete(system, user)
    try:
        return parse_json(text), meta
    except ValueError:
        text2, meta2 = _complete(system, user + "\n\nReturn ONLY one valid JSON object, nothing else.")
        meta2["tokens"] = meta2.get("tokens", 0) + meta.get("tokens", 0)
        meta2["cost"] = round(meta2.get("cost", 0.0) + meta.get("cost", 0.0), 6)
        meta2["seconds"] = round(meta2.get("seconds", 0.0) + meta.get("seconds", 0.0), 2)
        return parse_json(text2), meta2
