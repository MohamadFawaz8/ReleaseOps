terraform {
  required_version = "= 1.17.1"

  required_providers {
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.38.0"
    }
  }
}

provider "kubernetes" {
  config_path            = pathexpand("~/.kube/config")
  config_context         = var.expected_context
  config_context_cluster = var.expected_cluster
}
