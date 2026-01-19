output "service_name" {
  value = google_cloud_run_v2_service.svc.name
}

output "service_uri" {
  value = google_cloud_run_v2_service.svc.uri
}

output "latest_ready_revision" {
  value = google_cloud_run_v2_service.svc.latest_ready_revision
}
