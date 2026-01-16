project_id = "crncy-apps-preview"
region     = "us-central1"

environment      = "dev"
service_name     = "demo-devops-api-dev"
runtime_sa_email = "demo-devops-crncy-runtime@crncy-apps-preview.iam.gserviceaccount.com"

allow_unauthenticated = true

# OJO: usa DIGEST (recomendado para rollback)
image = "us-central1-docker.pkg.dev/crncy-apps-preview/demo-devops-hamid/crncy-api:2891e7168fc7ae1079078ddc0a51dc6cb0eb8ef0"