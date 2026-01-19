variable "project_id" { type = string }
variable "region" { type = string }
variable "environment" { type = string } # dev|test|prod
variable "service_name" { type = string }
variable "runtime_sa_email" { type = string }
variable "image" { type = string } # ...@sha256:...

variable "allow_unauthenticated" {
  type    = bool
  default = true
}
