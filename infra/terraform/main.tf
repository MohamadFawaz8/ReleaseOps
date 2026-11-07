resource "kubernetes_namespace_v1" "releaseops" {
  metadata {
    name = var.namespace
    labels = {
      "app.kubernetes.io/managed-by" = "terraform"
      "app.kubernetes.io/part-of"    = "releaseops"
    }
  }
}

resource "kubernetes_resource_quota_v1" "releaseops" {
  metadata {
    name      = "releaseops-budget"
    namespace = kubernetes_namespace_v1.releaseops.metadata[0].name
  }
  spec {
    hard = {
      "requests.cpu"           = "2"
      "requests.memory"        = "3Gi"
      "limits.cpu"             = "4"
      "limits.memory"          = "5Gi"
      "pods"                   = "20"
      "persistentvolumeclaims" = "3"
      "requests.storage"       = "6Gi"
    }
  }
}

resource "kubernetes_limit_range_v1" "releaseops" {
  metadata {
    name      = "releaseops-container-defaults"
    namespace = kubernetes_namespace_v1.releaseops.metadata[0].name
  }
  spec {
    limit {
      type = "Container"
      default = {
        cpu    = "500m"
        memory = "512Mi"
      }
      default_request = {
        cpu    = "100m"
        memory = "128Mi"
      }
      max = {
        cpu    = "2"
        memory = "2Gi"
      }
    }
  }
}

resource "kubernetes_service_account_v1" "workload" {
  metadata {
    name      = "releaseops-workload"
    namespace = kubernetes_namespace_v1.releaseops.metadata[0].name
  }
  automount_service_account_token = false
}
