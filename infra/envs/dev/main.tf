module "cloudrun" {
  source = "../../modules/cloudrun"

  project_id            = var.project_id
  region                = var.region
  environment           = var.environment
  service_name          = var.service_name
  runtime_sa_email      = var.runtime_sa_email
  image                 = var.image
  allow_unauthenticated = var.allow_unauthenticated

  labels = {
    environment = var.environment
  }
}
