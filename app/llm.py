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


_DISCOVERED_GEMINI_MODELS: list[str] | None = None


def discover_gemini_models() -> list[str]:
    """Dynamically query Google API to find all text generation models this key has access to."""
    global _DISCOVERED_GEMINI_MODELS
    if _DISCOVERED_GEMINI_MODELS is not None:
        return _DISCOVERED_GEMINI_MODELS

    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        _DISCOVERED_GEMINI_MODELS = []
        return []

    try:
        import urllib.request
        req = urllib.request.Request(
            "https://generativelanguage.googleapis.com/v1beta/models",
            headers={"x-goog-api-key": key},
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            models = []
            for m in data.get("models", []):
                name = m.get("name", "").replace("models/", "")
                methods = m.get("supportedGenerationMethods", [])
                if "generateContent" not in methods:
                    continue
                # Filter out specialized audio/vision-only/preview artifacts
                if any(x in name for x in ["tts", "image", "imagen", "embedding", "clip", "transcribe", "banana", "robotics", "computer-use"]):
                    continue
                models.append(name)
            _DISCOVERED_GEMINI_MODELS = models
            return models
    except Exception:
        _DISCOVERED_GEMINI_MODELS = []
        return []


def get_model_cascade(primary_model: str) -> list[str]:
    """Return an ordered cascade of models with similar capabilities."""
    if not (primary_model.startswith("gemini/") or "gemini" in primary_model):
        return [primary_model]

    raw_primary = primary_model.replace("gemini/", "")
    discovered = discover_gemini_models()

    if not discovered:
        # Fallback list if discovery request fails or offline
        fallback_names = [
            "gemini-2.5-flash",
            "gemini-flash-latest",
            "gemini-2.5-flash-lite",
            "gemini-flash-lite-latest",
            "gemini-2.5-pro",
        ]
    else:
        is_flash = "flash" in raw_primary or "lite" in raw_primary
        if is_flash:
            # Prioritize similar fast flash models, then pro models
            flash_models = [m for m in discovered if "flash" in m or "lite" in m]
            pro_models = [m for m in discovered if "pro" in m]
            fallback_names = flash_models + pro_models
        else:
            # Prioritize deep reasoning pro models, then flash models
            pro_models = [m for m in discovered if "pro" in m]
            flash_models = [m for m in discovered if "flash" in m or "lite" in m]
            fallback_names = pro_models + flash_models

    # Ensure primary model is first, and all candidates are unique and prefixed with gemini/
    ordered = [raw_primary] + [m for m in fallback_names if m != raw_primary]
    final_cascade = [f"gemini/{m}" if not m.startswith("gemini/") else m for m in ordered[:4]]
    return final_cascade


def _complete(system: str, user: str):
    import litellm  # imported lazily so tests can run without it

    litellm.drop_params = True
    primary_model = os.environ.get("MODEL", "gemini/gemini-2.5-flash")
    candidates = get_model_cascade(primary_model)
    t = time.time()
    last_err = None

    for i, model in enumerate(candidates):
        extra = {} if model.startswith("gemini/") else {"temperature": 0}
        try:
            r = litellm.completion(
                model=model,
                messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                num_retries=2,   # Fast retry per candidate before cascading
                timeout=60,      # A stuck call fails quickly so cascade can try next model
                **extra,
            )
            text = r.choices[0].message.content or ""
            usage = getattr(r, "usage", None)
            tokens = getattr(usage, "total_tokens", 0) if usage else 0
            try:
                cost = litellm.completion_cost(completion_response=r) or 0.0
            except Exception:
                cost = 0.0
            return text, {
                "tokens": tokens,
                "cost": round(cost, 6),
                "seconds": round(time.time() - t, 2),
                "model": model,
            }
        except Exception as e:
            last_err = e
            m_err = str(e).lower()
            is_overloaded = any(
                code in m_err
                for code in ("503", "unavailable", "overloaded", "high demand", "429", "rate limit", "rate_limit", "resource_exhausted")
            )
            if is_overloaded and i < len(candidates) - 1:
                next_model = candidates[i + 1]
                print(f"\n[!] Model '{model}' is temporarily overloaded ({_friendly(e)}).")
                print(f"[*] Dynamically cascading to similar model '{next_model}'...")
                continue
            else:
                raise RuntimeError(_friendly(e)) from None

    raise RuntimeError(_friendly(last_err)) if last_err else RuntimeError("Model call failed")


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
