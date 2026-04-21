"""
Security CLI for AI-OS
Register agents, login, and manage access.
"""

import argparse
from datetime import datetime, timedelta

from kernel.security import (
    AgentIdentity,
    AuthFactor,
    AuthFactorType,
    SecurityManager,
    policy_2fa,
    policy_3fa,
)


def _parse_factors(factors_csv: str):
    if not factors_csv:
        return []
    items = [f.strip().lower() for f in factors_csv.split(",") if f.strip()]
    mapping = {
        "knowledge": AuthFactorType.KNOWLEDGE,
        "possession": AuthFactorType.POSSESSION,
        "biometric": AuthFactorType.BIOMETRIC,
        "behavioral": AuthFactorType.BEHAVIORAL,
    }
    factors = []
    now = datetime.utcnow()
    for item in items:
        if item not in mapping:
            continue
        factors.append(
            AuthFactor(
                factor_type=mapping[item],
                verified_at=now,
                expires_at=now + timedelta(minutes=10),
            )
        )
    return factors


def register_cmd(args):
    sec = SecurityManager()
    identity = AgentIdentity(
        agent_id=args.agent_id,
        user_name=args.user_name or args.agent_id,
        key_fingerprint=args.key_fingerprint or "",
    )
    if args.policy == "2fa":
        policy = policy_2fa(
            require_biometric=args.require_biometric,
            require_possession=args.require_possession,
        )
    elif args.policy == "3fa":
        policy = policy_3fa()
    else:
        policy = None
    sec.register_agent(identity, policy)
    print(f"[SECURITY] Registered agent {args.agent_id}")


def login_cmd(args):
    sec = SecurityManager()
    factors = _parse_factors(args.factors)
    session = sec.login(args.agent_id, factors)
    status = "OK" if session.authenticated else "DENIED"
    print(f"[SECURITY] Login {status} for {args.agent_id} ({session.reason})")


def lock_cmd(args):
    sec = SecurityManager()
    ok = sec.registry.lock_agent(args.agent_id)
    print(f"[SECURITY] Lock {'OK' if ok else 'FAILED'} for {args.agent_id}")


def unlock_cmd(args):
    sec = SecurityManager()
    ok = sec.registry.unlock_agent(args.agent_id)
    print(f"[SECURITY] Unlock {'OK' if ok else 'FAILED'} for {args.agent_id}")


def main():
    parser = argparse.ArgumentParser(description="AI-OS security CLI")
    sub = parser.add_subparsers(dest="cmd", required=True)

    reg = sub.add_parser("register", help="Register agent")
    reg.add_argument("agent_id")
    reg.add_argument("--user-name")
    reg.add_argument("--key-fingerprint")
    reg.add_argument("--policy", choices=["default", "2fa", "3fa"], default="default")
    reg.add_argument("--require-biometric", action="store_true")
    reg.add_argument("--require-possession", action="store_true")
    reg.set_defaults(func=register_cmd)

    login = sub.add_parser("login", help="Login agent")
    login.add_argument("agent_id")
    login.add_argument("--factors", default="knowledge", help="Comma list: knowledge,possession,biometric,behavioral")
    login.set_defaults(func=login_cmd)

    lock = sub.add_parser("lock", help="Lock agent")
    lock.add_argument("agent_id")
    lock.set_defaults(func=lock_cmd)

    unlock = sub.add_parser("unlock", help="Unlock agent")
    unlock.add_argument("agent_id")
    unlock.set_defaults(func=unlock_cmd)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
