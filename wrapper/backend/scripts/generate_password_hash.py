#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import getpass
import hashlib
import secrets


def build_hash(password: str, iterations: int) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    salt_b64 = base64.urlsafe_b64encode(salt).decode("ascii").rstrip("=")
    digest_b64 = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
    return f"pbkdf2_sha256${iterations}${salt_b64}${digest_b64}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate PBKDF2 password hash for wrapper backend auth")
    parser.add_argument("--password", default="", help="Plaintext password (omit to be prompted securely)")
    parser.add_argument("--iterations", type=int, default=310000, help="PBKDF2 iterations (default: 310000)")
    args = parser.parse_args()

    password = args.password or getpass.getpass("Password: ")
    if not password:
        raise SystemExit("Password cannot be empty")

    print(build_hash(password=password, iterations=args.iterations))


if __name__ == "__main__":
    main()
