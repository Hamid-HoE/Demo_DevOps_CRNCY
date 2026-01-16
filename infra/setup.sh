#!/usr/bin/env bash
set -euo pipefail

ENVIRONMENT="${1:?ENV required: dev|test|prod}"
PROJECT_ID="${2:?PROJECT_ID required}"
REGION="${3:?REGION required}"
SERVICE_NAME="${4:?SERVICE_NAME required}"
RUNTIME_SA="${5:?RUNTIME_SA email required}"
IMAGE="${6:?IMAGE digest required (recommended) or tag}"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_DIR="${ROOT_DIR}/envs/${ENVIRONMENT}"

TF_STATE_BUCKET="${PROJECT_ID}-tfstate-crncy"
TF_STATE_PREFIX="cloudrun/${ENVIRONMENT}"

echo "==> Enabling APIs (safe if already enabled)"
gcloud services enable \
  run.googleapis.com \
  iam.googleapis.com \
  cloudresourcemanager.googleapis.com \
  --project "${PROJECT_ID}" >/dev/null

echo "==> Ensuring state bucket exists: gs://${TF_STATE_BUCKET}"
if ! gcloud storage buckets describe "gs://${TF_STATE_BUCKET}" --project "${PROJECT_ID}" >/dev/null 2>&1; then
  gcloud storage buckets create "gs://${TF_STATE_BUCKET}" \
    --project "${PROJECT_ID}" \
    --location "${REGION}" \
    --uniform-bucket-level-access >/dev/null
fi

echo "==> Terraform init/apply (${ENVIRONMENT})"
terraform -chdir="${ENV_DIR}" init -upgrade \
  -backend-config="bucket=${TF_STATE_BUCKET}" \
  -backend-config="prefix=${TF_STATE_PREFIX}" >/dev/null

terraform -chdir="${ENV_DIR}" apply -auto-approve \
  -var="project_id=${PROJECT_ID}" \
  -var="region=${REGION}" \
  -var="environment=${ENVIRONMENT}" \
  -var="service_name=${SERVICE_NAME}" \
  -var="runtime_sa_email=${RUNTIME_SA}" \
  -var="image=${IMAGE}"

echo "==> Done (${ENVIRONMENT})"
