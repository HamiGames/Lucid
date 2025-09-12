# Cluster A stub: defined API but not wired (Cluster C will provide real impl).
# We avoid placeholders in configs; these functions are unused until Cluster C.

from typing import Dict


def make_tokens_stub(subject: str) -> Dict[str, str]:
    # Deterministic, clearly-nonsecure tokens for early integration tests only.
    # Replaced in Cluster C with signed JWTs.
    return {
        "access_token": f"dev-access-{subject}",
        "refresh_token": f"dev-refresh-{subject}",
    }
