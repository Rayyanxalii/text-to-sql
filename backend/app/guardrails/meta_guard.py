from transformers import pipeline

MODEL_ID = "protectai/deberta-v3-base-prompt-injection-v2"

# Initialize pipeline once so it is reused across requests
classifier = pipeline(
    "text-classification",
    model=MODEL_ID,
)


def check_meta_guard(text: str, threshold: float = 0.5) -> dict:
    """
    Classify whether input text contains a prompt injection using DeBERTa.
    Returns:
        dict: {
            "is_safe": bool,
            "label": str,
            "score": float,
            "reason": str | None,
        }
    """
    if not isinstance(text, str) or not text.strip():
        return {
            "is_safe": True,
            "label": "SAFE",
            "score": 1.0,
            "reason": None,
        }

    try:
        results = classifier(text, truncation=True, max_length=512)
        top = results[0]
        label = str(top["label"]).upper()
        score = float(top["score"])

        is_injection = (label == "INJECTION" and score >= threshold)

        return {
            "is_safe": not is_injection,
            "label": label,
            "score": score,
            "reason": f"Prompt injection detected by model ({score:.1%} confidence)." if is_injection else None,
        }
    except Exception as e:
        print(f"[MetaGuard] Classifier execution error: {e}")
        # Default to safe if model fails so transient errors don't crash requests
        return {
            "is_safe": True,
            "label": "ERROR",
            "score": 0.0,
            "reason": None,
        }