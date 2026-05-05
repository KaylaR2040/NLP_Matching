#!/usr/bin/env python3
"""Rebuild and deploy the Flutter web frontends to Firebase Hosting."""

from __future__ import annotations

import argparse
import os
import shlex
import shutil
import subprocess
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_BACKEND_URL = "https://nlp-mentor-backend-55soihtqaq-uc.a.run.app"
DEFAULT_FIREBASE_PROJECT_ID = "nlp-mentor-2026-55d28"


def run(command: list[str], *, cwd: Path | None = None, env: dict[str, str] | None = None) -> None:
    print("+", " ".join(shlex.quote(part) for part in command))
    subprocess.run(command, cwd=cwd, env=env, check=True)


def require_command(command_name: str) -> None:
    if shutil.which(command_name) is None:
        raise SystemExit(f"ERROR: {command_name} CLI not found.")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Rebuild and redeploy Flutter web frontends to Firebase Hosting. "
        "Works for both first-time deploys and redeployments.",
    )
    parser.add_argument(
        "--backend-url",
        default=os.environ.get("BACKEND_API_BASE_URL", DEFAULT_BACKEND_URL),
        help="Backend API base URL baked into the Flutter build. Defaults to the live Cloud Run URL.",
    )
    parser.add_argument(
        "--wrapper-url",
        default=os.environ.get("WRAPPER_API_BASE_URL"),
        help="Wrapper API base URL for the admin app. Defaults to --backend-url.",
    )
    parser.add_argument(
        "--project-id",
        default=os.environ.get("FIREBASE_PROJECT_ID", DEFAULT_FIREBASE_PROJECT_ID),
        help="Firebase project ID to deploy to. Defaults to the live project.",
    )
    parser.add_argument(
        "--flutter-sdk-dir",
        default=os.environ.get("FLUTTER_SDK_DIR") or str(ROOT_DIR / ".flutter_sdk"),
        help="Path to a Flutter SDK install. Defaults to ./.flutter_sdk inside the repo.",
    )
    parser.add_argument(
        "--firebase-token",
        default=os.environ.get("FIREBASE_TOKEN"),
        help="Optional Firebase CI token. If omitted, the Firebase CLI login is used.",
    )
    args = parser.parse_args()

    backend_url = args.backend_url

    wrapper_url = args.wrapper_url or backend_url
    project_id = args.project_id
    flutter_sdk_dir = Path(args.flutter_sdk_dir).expanduser().resolve()
    flutter_bin = flutter_sdk_dir / "bin" / "flutter"

    require_command("firebase")

    if not flutter_bin.is_file():
        require_command("git")
        print(f"Cloning Flutter into {flutter_sdk_dir}")
        run([
            "git",
            "clone",
            "--depth",
            "1",
            "--branch",
            "stable",
            "https://github.com/flutter/flutter.git",
            str(flutter_sdk_dir),
        ], cwd=ROOT_DIR)

    env = os.environ.copy()
    env["PATH"] = f"{flutter_sdk_dir / 'bin'}:{env.get('PATH', '')}"

    run(["flutter", "config", "--enable-web"], cwd=ROOT_DIR, env=env)

    for project_dir, define_key, define_value in (
        ("wrapper/flutter_wrapper", "WRAPPER_API_BASE_URL", wrapper_url),
        ("flutter_mentor", "BACKEND_API_BASE_URL", backend_url),
        ("flutter_mentee", "BACKEND_API_BASE_URL", backend_url),
    ):
        project_path = ROOT_DIR / project_dir
        print(f"Building {project_dir} with {define_key}={define_value}")
        run(["flutter", "pub", "get"], cwd=project_path, env=env)
        run([
            "flutter",
            "build",
            "web",
            "--release",
            f"--dart-define={define_key}={define_value}",
        ], cwd=project_path, env=env)

    deploy_args = [
        "firebase",
        "deploy",
        "--only",
        "hosting:admin,hosting:mentor,hosting:mentee",
        "--non-interactive",
    ]
    if project_id:
        deploy_args.extend(["--project", project_id])
    if args.firebase_token:
        deploy_args.extend(["--token", args.firebase_token])

    run(deploy_args, cwd=ROOT_DIR, env=env)
    print("Firebase frontend deployment complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())