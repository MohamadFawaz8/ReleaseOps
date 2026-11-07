output "namespace" {
  description = "Namespace shared by Terraform platform policy and Kustomize workloads."
  value       = kubernetes_namespace_v1.releaseops.metadata[0].name
}

output "workload_service_account" {
  description = "Least-privilege identity for application pods; it has no API permissions."
  value       = kubernetes_service_account_v1.workload.metadata[0].name
}
