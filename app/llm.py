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


def _version_sort_key(name: str) -> float:
    match = re.search(r"(\d+(?:\.\d+)?)", name)
    return float(match.group(1)) if match else 0.0


def get_model_cascade(primary_model: str) -> list[str]:
    """Return an ordered cascade of models with similar capabilities, prioritizing modern versions."""
    if not (primary_model.startswith("gemini/") or "gemini" in primary_model):
        return [primary_model]

    raw_primary = primary_model.replace("gemini/", "")
    discovered = discover_gemini_models()

    if not discovered:
        # Fallback list if discovery request fails or offline
        fallback_names = [
            "gemini-3.8-flash",
            "gemini-3.7-flash",
            "gemini-3.6-flash",
            "gemini-3.5-flash-lite",
            "gemini-2.5-flash",
        ]
    else:
        is_flash = "flash" in raw_primary or "lite" in raw_primary
        flash_models = [m for m in discovered if "flash" in m or "lite" in m]
        pro_models = [m for m in discovered if "pro" in m]
        flash_models.sort(key=_version_sort_key, reverse=True)
        pro_models.sort(key=_version_sort_key, reverse=True)

        if is_flash:
            fallback_names = flash_models + pro_models
        else:
            fallback_names = pro_models + flash_models

    # Ensure primary model is first, and all candidates are unique and prefixed with gemini/
    ordered = [raw_primary] + [m for m in fallback_names if m != raw_primary]
    final_cascade = [f"gemini/{m}" if not m.startswith("gemini/") else m for m in ordered[:5]]
    return final_cascade


def _complete(system: str, user: str, json_mode: bool = False):
    import litellm  # imported lazily so tests can run without it

    litellm.drop_params = True
    primary_model = os.environ.get("MODEL", "gemini/gemini-3.8-flash")
    candidates = get_model_cascade(primary_model)
    t = time.time()
    last_err = None

    for i, model in enumerate(candidates):
        extra = {} if model.startswith("gemini/") else {"temperature": 0}
        if json_mode:
            extra["response_format"] = {"type": "json_object"}
        try:
            r = litellm.completion(
                model=model,
                messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                num_retries=1,   # Fast failover to healthy models in cascade
                timeout=90,      # Generous timeout so large code generations do not fail prematurely
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
            is_failover_candidate = any(
                code in m_err
                for code in (
                    "503",
                    "unavailable",
                    "overloaded",
                    "high demand",
                    "429",
                    "rate limit",
                    "rate_limit",
                    "resource_exhausted",
                    "timeout",
                    "timed out",
                    "not_found",
                    "404",
                    "no longer available",
                )
            )
            if is_failover_candidate and i < len(candidates) - 1:
                next_model = candidates[i + 1]
                print(f"\n[!] Model '{model}' unavailable or timed out ({_friendly(e)}).")
                print(f"[*] Dynamically cascading to similar model '{next_model}'...")
                continue
            else:
                raise RuntimeError(_friendly(e)) from None

    raise RuntimeError(_friendly(last_err)) if last_err else RuntimeError("Model call failed")


def _clean_json_str(s: str) -> str:
    """Clean common JSON formatting flaws produced by LLMs."""
    # 1. Strip trailing commas before closing braces/brackets
    s = re.sub(r",\s*([\]}])", r"\1", s)
    # 2. Escape unescaped backslashes (e.g. \033 ANSI codes, Windows paths) that are not valid JSON escapes
    # Valid JSON escapes are \", \\, \/, \b, \f, \n, \r, \t, \uXXXX
    s = re.sub(r'\\(?![/\\bfnrtu"U])', r"\\\\", s)
    return s


def parse_json(text: str) -> dict:
    """Extract a JSON object from model output, tolerating code fences, commentary, ANSI codes, and formatting issues."""
    import ast

    text = text.strip()

    def _try_load(candidate: str):
        # A. Try json.loads with strict=False (allows unescaped newlines and control characters)
        try:
            return json.loads(candidate, strict=False)
        except Exception:
            pass
        # B. Try cleaned candidate (commas + backslashes)
        cleaned = _clean_json_str(candidate)
        try:
            return json.loads(cleaned, strict=False)
        except Exception:
            pass
        # C. Try ast.literal_eval (tolerates single quotes, True/False/None)
        try:
            val = ast.literal_eval(candidate)
            if isinstance(val, dict):
                return val
        except Exception:
            pass
        return None

    # 1. Try raw text directly
    res = _try_load(text)
    if res is not None:
        return res

    # 2. Try extracting from markdown code block ```json ... ``` or ``` ... ```
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if match:
        block = match.group(1).strip()
        res = _try_load(block)
        if res is not None:
            return res
        text = block

    # 3. Find outer braces
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end > start:
        snippet = text[start : end + 1]
        res = _try_load(snippet)
        if res is not None:
            return res

    # 4. Fallback field extraction for structured agent outputs (Reviewer, Planner)
    if '"approved"' in text or "'approved'" in text:
        salvaged = {}
        app_match = re.search(r'["\']approved["\']\s*:\s*(true|false|True|False)', text)
        if app_match:
            salvaged["approved"] = app_match.group(1).lower() == "true"
        for field in ("summary", "feedback", "user_explanation"):
            f_match = re.search(rf'["\']{field}["\']\s*:\s*["\']([\s\S]*?)["\']\s*[,}}]', text)
            if f_match:
                salvaged[field] = f_match.group(1)
        if "approved" in salvaged:
            return salvaged

    preview = (text[:200] + "...") if len(text) > 200 else text
    raise ValueError(f"No valid JSON object in model output. Preview: {preview}")


def ask_json(system: str, user: str, schema_cls: Any = None, max_retries: int = 2) -> tuple[dict, dict]:
    """Call the model with native JSON constraints and reflective self-correction.

    If parsing or schema validation fails, feeds the exact error diagnostic and previous output
    back to the model so it reflectively self-heals instead of failing blindly.
    """
    from app.schemas import validate_schema

    total_tokens = 0
    total_cost = 0.0
    total_seconds = 0.0
    last_meta = {}

    current_prompt = user

    for attempt in range(max_retries + 1):
        try:
            text, meta = _complete(system, current_prompt, json_mode=True)
        except TypeError:
            text, meta = _complete(system, current_prompt)
        total_tokens += meta.get("tokens", 0)
        total_cost += meta.get("cost", 0.0)
        total_seconds += meta.get("seconds", 0.0)
        last_meta = meta

        # 1. Parse JSON
        try:
            data = parse_json(text)
            parse_err = None
        except Exception as e:
            data = None
            parse_err = str(e)

        # 2. Schema validation if schema provided and parse succeeded
        schema_err = None
        if data is not None and schema_cls is not None:
            data, schema_err = validate_schema(data, schema_cls)

        # Success if parsed and schema validated
        if data is not None and not schema_err:
            combined_meta = {
                **last_meta,
                "tokens": total_tokens,
                "cost": round(total_cost, 6),
                "seconds": round(total_seconds, 2),
                "attempts": attempt + 1,
            }
            return data, combined_meta

        # If failed and attempts remain, construct reflective feedback
        if attempt < max_retries:
            err_reason = parse_err or schema_err
            print(f"\n[!] Model output format issue ({err_reason}). Initiating reflective self-correction (Attempt {attempt+2}/{max_retries+1})...")
            current_prompt = (
                f"{user}\n\n"
                f"CRITICAL: Your previous response could not be validated. Error details:\n"
                f"--> {err_reason}\n\n"
                f"PREVIOUS OUTPUT SNIPPET:\n"
                f"{(text[:800] + '...') if len(text) > 800 else text}\n\n"
                f"Please reflect on this error, correct your formatting, and return a single valid JSON object."
            )

    raise ValueError(f"Failed to obtain valid JSON after {max_retries + 1} attempts. Last error: {parse_err or schema_err}")

