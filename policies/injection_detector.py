INJECTION_PATTERNS = [
    "ignore previous instructions",
    "system override",
    "reveal system prompt",
    "bypass safety",
]
 
def detect_injection(prompt: str) -> bool:
    prompt_lower = prompt.lower()
 
    for pattern in INJECTION_PATTERNS:
        if pattern in prompt_lower:
            return True
 
    return False
 