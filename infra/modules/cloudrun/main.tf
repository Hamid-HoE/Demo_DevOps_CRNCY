resource "google_cloud_run_v2_service" "svc" {
  name     = var.service_name
  location = var.region
  project  = var.project_id

  labels = merge(
    {
      app = "crncy-api"
      env = var.environment
    },
    var.labels
  )

  ingress = var.ingress

  template {
    service_account = var.runtime_sa_email

    scaling {
      min_instance_count = var.min_instances
      max_instance_count = var.max_instances
    }

    containers {
      image = var.image

      resources {
        limits = {
          cpu    = var.cpu
          memory = var.memory
        }
      }
    }

    max_instance_request_concurrency = var.concurrency
    timeout                          = "${var.timeout_seconds}s"
  }

  lifecycle {
    ignore_changes = [
      # evita drift por cambios automáticos de Google en algunos metadatos
      client,
      client_version
    ]
  }
}

resource "google_cloud_run_v2_service_iam_member" "public_invoker" {
  count    = var.allow_unauthenticated ? 1 : 0
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.svc.name

  role   = "roles/run.invoker"
  member = "allUsers"
}
