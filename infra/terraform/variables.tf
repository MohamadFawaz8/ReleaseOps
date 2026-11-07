variable "expected_context" {
  description = "Exact local kind context Terraform is allowed to use."
  type        = string
  default     = "kind-releaseops"
  validation {
    condition     = var.expected_context == "kind-releaseops"
    error_message = "This configuration manages only the kind-releaseops context."
  }
}

variable "expected_cluster" {
  description = "Kubeconfig cluster entry associated with the local kind cluster."
  type        = string
  default     = "kind-releaseops"
  validation {
    condition     = var.expected_cluster == "kind-releaseops"
    error_message = "This configuration manages only the kind-releaseops cluster entry."
  }
}

variable "namespace" {
  description = "Dedicated namespace shared by Terraform and Kustomize."
  type        = string
  default     = "releaseops"
  validation {
    condition     = var.namespace == "releaseops"
    error_message = "Application manifests are intentionally scoped to releaseops."
  }
}
