import os, time
import jwt  # PyJWT
from typing import List, Dict

ALG = "RS256"

def _load_private_key():
    pem = os.getenv("POLICY_SIGNING_PRIVATE_KEY_FILE")
    if not pem or not os.path.exists(pem):
        raise RuntimeError("POLICY_SIGNING_PRIVATE_KEY_FILE missing or unreadable")
    return open(pem, "rb").read()

def sign_policy_ticket(tenant_id: str, roles_allowed: List[str], tools_allowed: List[str],
                       ttl_seconds: int, canary: Dict, dh_tags: List[str], sissa_gate: str) -> str:
    now = int(time.time())
    payload = {
        "iss": "AgentHospital", "aud": "AML-University",
        "iat": now, "nbf": now, "exp": now + ttl_seconds,
        "tenant_id": tenant_id,
        "roles_allowed": roles_allowed,
        "tools_allowed": tools_allowed,
        "canary": canary,
        "dh_tags": dh_tags,
        "sissa_gate": sissa_gate,
        "v": 1
    }
    key = _load_private_key()
    return jwt.encode(payload, key, algorithm=ALG)

def verify_policy_ticket(token: str, public_key_pem: bytes) -> dict:
    return jwt.decode(token, public_key_pem, algorithms=[ALG], audience="AML-University", issuer="AgentHospital")