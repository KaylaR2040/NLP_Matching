#!/usr/bin/env python3
"""Build and deploy the Cloud Run backend."""

from __future__ import annotations

import argparse
import os
import shlex
import shutil
import subprocess
from datetime import datetime
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_PROJECT_ID = "project-36246763-0a0e-4a90-97c"
DEFAULT_ALLOWED_ORIGINS = "https://nlp-admin.web.app,https://nlp-mentor.web.app,https://nlp-mentee.web.app"
DEFAULT_NON_SECRET_ENV_VARS = (
    "^##^WRAPPER_MENTOR_STORAGE_MODE=postgres"
    "##WRAPPER_NLP_PROJECT_DIR=/app/nlp_project"
    "##WRAPPER_MATCH_TIMEOUT_SECONDS=270"
    "##WRAPPER_SCRIPT_TIMEOUT_SECONDS=180"
    "##WRAPPER_REQUIRE_HTTPS=true"
    "##WRAPPER_ALLOWED_ORIGINS={allowed_origins}"
)
DEFAULT_SECRET_ENV_VARS = (
    "DATABASE_URL=DATABASE_URL:latest,"
    "WRAPPER_TOKEN_SECRET=WRAPPER_TOKEN_SECRET:latest,"
    "WRAPPER_USER_USERNAME=WRAPPER_USER_USERNAME:latest,"
    "WRAPPER_USER_PASSWORD_HASH=WRAPPER_USER_PASSWORD_HASH:latest,"
    "WRAPPER_DEV_USERNAME=WRAPPER_DEV_USERNAME:latest,"
    "WRAPPER_DEV_PASSWORD_HASH=WRAPPER_DEV_PASSWORD_HASH:latest"
)


def run(command: list[str], *, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    print("+", " ".join(shlex.quote(part) for part in command))
    return subprocess.run(command, cwd=cwd, check=True, text=True, capture_output=True)


def run_stream(command: list[str], *, cwd: Path | None = None) -> None:
    print("+", " ".join(shlex.quote(part) for part in command))
    subprocess.run(command, cwd=cwd, check=True)


def require_command(command_name: str) -> None:
    if shutil.which(command_name) is None:
        raise SystemExit(f"ERROR: {command_name} CLI is required.")


def infer_project_id(explicit_project_id: str | None) -> str:
    if explicit_project_id:
        return explicit_project_id

    require_command("gcloud")
    result = run(["gcloud", "config", "get-value", "project"], cwd=ROOT_DIR)
    project_id = result.stdout.strip()
    if project_id and project_id != "(unset)":
        return project_id

    raise SystemExit("ERROR: Set PROJECT_ID or run: gcloud config set project <id>")


def git_short_sha_or_timestamp() -> str:
    try:
        result = run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT_DIR)
        value = result.stdout.strip()
        if value:
            return value
    except subprocess.CalledProcessError:
        pass

    return datetime.now().strftime("%Y%m%d%H%M%S")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build and deploy the Cloud Run backend. "
        "Docker does NOT need to be running locally — the image is built "
        "on Google Cloud Build.",
    )
    parser.add_argument("--project-id", default=os.environ.get("PROJECT_ID", DEFAULT_PROJECT_ID), help="GCP project ID.")
    parser.add_argument("--region", default=os.environ.get("REGION", "us-central1"), help="Cloud Run region.")
    parser.add_argument(
        "--service-name",
        default=os.environ.get("SERVICE_NAME", "nlp-mentor-backend"),
        help="Cloud Run service name.",
    )
    parser.add_argument(
        "--artifact-repo",
        default=os.environ.get("ARTIFACT_REPO", "cloud-run-images"),
        help="Artifact Registry repository used for the container image.",
    )
    parser.add_argument(
        "--allowed-origins",
        default=os.environ.get("WRAPPER_ALLOWED_ORIGINS", DEFAULT_ALLOWED_ORIGINS),
        help="Comma-separated CORS origins. Defaults to the three live Firebase sites.",
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Pass --no-cache to Cloud Build for a clean rebuild of the Docker image.",
    )
    args = parser.parse_args()

    require_command("gcloud")

    project_id = infer_project_id(args.project_id)
    region = args.region
    service_name = args.service_name
    artifact_repo = args.artifact_repo
    allowed_origins = args.allowed_origins
    image_tag = os.environ.get("IMAGE_TAG", git_short_sha_or_timestamp())
    image_uri = os.environ.get(
        "IMAGE_URI",
        f"{region}-docker.pkg.dev/{project_id}/{artifact_repo}/{service_name}:{image_tag}",
    )

    non_secret_env_vars = os.environ.get(
        "NON_SECRET_ENV_VARS",
        DEFAULT_NON_SECRET_ENV_VARS.format(allowed_origins=allowed_origins),
    )
    secret_env_vars = os.environ.get("SECRET_ENV_VARS", DEFAULT_SECRET_ENV_VARS)

    print("NOTE: Docker does not need to be running locally. Cloud Build handles the image build remotely.")
    print(f"Using PROJECT_ID={project_id} REGION={region} SERVICE_NAME={service_name}")
    print(f"Ensuring Artifact Registry repository '{artifact_repo}' exists...")

    repo_check = subprocess.run(
        [
            "gcloud",
            "artifacts",
            "repositories",
            "describe",
            artifact_repo,
            "--location",
            region,
            "--project",
            project_id,
        ],
        cwd=ROOT_DIR,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if repo_check.returncode != 0:
        run_stream(
            [
                "gcloud",
                "artifacts",
                "repositories",
                "create",
                artifact_repo,
                "--repository-format",
                "docker",
                "--location",
                region,
                "--description",
                "Container images for Cloud Run deployments",
                "--project",
                project_id,
            ],
            cwd=ROOT_DIR,
        )

    print(f"Building backend image on Cloud Build: {image_uri}")
    build_cmd = [
        "gcloud",
        "builds",
        "submit",
        "--project",
        project_id,
        "--config",
        "cloudbuild.image.yaml",
        "--substitutions",
        f"_IMAGE_URI={image_uri}",
        "--timeout=1800",
    ]
    if args.no_cache:
        build_cmd.append("--no-cache")
    build_cmd.append(".")
    run_stream(build_cmd, cwd=ROOT_DIR)

    print("Deploying Cloud Run service...")
    deploy_command = [
        "gcloud",
        "run",
        "deploy",
        service_name,
        "--project",
        project_id,
        "--region",
        region,
        "--platform",
        "managed",
        "--image",
        image_uri,
        "--allow-unauthenticated",
        "--ingress",
        "all",
        "--cpu",
        "1",
        "--memory",
        "4Gi",
        "--concurrency",
        "1",
        "--timeout",
        "300",
        "--min-instances",
        "0",
        "--max-instances",
        "3",
        "--set-env-vars",
        non_secret_env_vars,
    ]

    if secret_env_vars:
        deploy_command.extend(["--set-secrets", secret_env_vars])

    run_stream(deploy_command, cwd=ROOT_DIR)

    service_url_result = run(
        [
            "gcloud",
            "run",
            "services",
            "describe",
            service_name,
            "--project",
            project_id,
            "--region",
            region,
            "--format=value(status.url)",
        ],
        cwd=ROOT_DIR,
    )
    service_url = service_url_result.stdout.strip()
    print("Cloud Run deployment complete.")
    if service_url:
        print(f"Service URL: {service_url}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())