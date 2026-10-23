# Project: ReleaseOps

Status: selected; the learner created https://github.com/MohamadFawaz8/ReleaseOps .
The architecture and sequence below remain a staged roadmap, not an instruction
to build all components immediately.

## Product idea
A small order-processing platform. Users submit an order and track its status.
Start with one Python API and a simple browser interface. Later add PostgreSQL,
a Redis work queue, and a separate background worker so dependency failures,
retries, duplicate processing, and queue backlogs become observable exercises.
Use synthetic data and simulated fulfillment; no real payments or customers.

The portfolio focus is reliable delivery and operations: tests, reproducibility,
security checks, controlled releases, monitoring, incident diagnosis, and recovery.

## Proposed architecture and ownership
- Windows host with existing WSL 2 Ubuntu for Linux practice.
- Docker images package services; Compose first runs them together locally.
- Nginx serves the simple interface and reverse proxies API traffic.
- kind bootstraps a real local Kubernetes cluster using container nodes.
- kubectl inspects and operates the cluster.
- Terraform manages selected platform resources in the existing cluster, such as
  namespaces, quotas, RBAC, and selected Helm releases. Teach plan/apply/state,
  dependencies, import, drift, and recovery through actual local resources.
- Application manifests use Kustomize for environment differences. A given resource
  must have one owner; Terraform and Flux must not manage the same objects.
- GitHub Actions begins with one simple workflow, then tests, image builds, Trivy
  scanning, GHCR publication, and temporary-cluster deployment verification.
- Jenkins is a required hands-on component, explicitly requested on 2026-10-23.
  Introduce it after the initial GitHub Actions and Docker lessons. Run it locally
  and build a Jenkinsfile pipeline using shared test/build scripts for the same
  application. Teach controller/agents, credentials, triggers, logs, and failure
  diagnosis. Define a single release owner to avoid competing deployments. Account
  for local RAM limits; the complete stack need not run simultaneously.
- Persistent local deployments are manual first. Later Flux pulls approved Git
  configuration into the local cluster; GitHub-hosted runners do not inherently
  have access to the learner's private local Kubernetes API.
- Prometheus collects metrics; Grafana displays dashboards; Alertmanager routes
  local alerts. Begin with application/container logs before adding any log stack.
- Helm installs packaged platform components when introduced; explain chart values.
- Use GitHub Issues/templates to simulate incident, change, and service request
  workflows. Clearly distinguish this from operating an enterprise ITSM platform.
- Use one cluster with logical environments initially. This is not independent
  production isolation or cloud high availability. Add workloads within RAM limits.

## Learning sequence
1. Validate existing setup; learn Linux shell, processes, permissions, logs,
   ports, DNS, HTTP, Git commits, branches, pull requests, and merge conflicts.
2. Run a minimal API; understand requests, responses, tests, and health endpoints.
3. Learn GitHub Actions YAML, triggers, jobs, runners, steps, failures, and CI checks.
4. Learn Dockerfiles, images, containers, networking, volumes, Compose, and Nginx;
   extend CI to build, scan, and publish versioned images.
   Then install Jenkins locally and reproduce the core CI checks in a Jenkinsfile,
   comparing its operation and maintenance with GitHub Actions.
5. Deploy to kind; learn Pods, Deployments, Services, configuration, secrets,
   probes, requests/limits, persistence, rollouts, rollback, and scaling.
6. Add Terraform platform management; keep cluster creation and in-cluster resources
   in distinct lifecycle steps. Learn state protection and locking limitations.
7. Add controlled delivery, environment promotion, and Flux reconciliation;
   distinguish continuous delivery from continuous deployment.
8. Add dashboards, actionable alerts, load tests, security hardening, and backups;
   introduce basic security practices throughout earlier stages too.
9. Run incidents, release rehearsals, handovers, patching, and restore drills.
10. Document architecture and results; practice interviews; produce the demo and
    LinkedIn post with explicit lab and AWS-experience boundaries.

## Screenshot scenario exercises
- Intermittent timeouts despite healthy application checks: trace the request path.
- Deployment raises latency from 200 ms to 3 seconds: compare before/after evidence.
- CI starts failing without workflow changes: investigate runners, dependencies,
  credentials, quotas, networks, registries, and external services.
- Partially failed deployment leaves mixed versions: stabilize, assess compatibility,
  recover, and validate; include database migration and rollback limitations.
- Container restarts without application errors: inspect events, exit codes,
  prior logs, OOM termination, probes, and node pressure.
- Green dashboards conflict with user reports: examine coverage, percentiles,
  affected paths, dependencies, and synthetic/user-facing checks.
- Adopt existing resources into Terraform without disruptive recreation.
- Respond to a critical image vulnerability: assess exposure, patch, rebuild,
  scan, promote, verify, and document prevention.

## Interview topic coverage
- Linux services/systemd/journalctl, users/groups/sudo, permissions, processes and
  signals, filesystems, storage/mounts, resource usage, networking, Bash automation.
  Some system administration exercises need a systemd-capable WSL environment;
  containers alone do not reproduce a full Linux host.
- CI/CD explanation, credentials and least privilege, pipeline failure diagnosis,
  release controls, and hands-on Jenkins pipelines alongside GitHub Actions.
- Docker image/container differences, layers, builds, security, networking, volumes.
- Kubernetes architecture, workloads, Pods versus containers versus DaemonSets,
  deployments/services/configuration, probes, automatic recovery, rollbacks,
  routing/Ingress concepts, scaling, logging, and stateful-app/WordPress designs.
- Terraform state creation/backends, dependencies, drift, refresh-only workflows,
  count versus for_each, import, destruction safeguards, locking/concurrent applies,
  state backup/recovery, and CI integration.
- AWS design study: IAM/OIDC, VPCs, public/private subnets, routing, NAT, peering,
  security groups versus NACLs, multi-AZ, EKS versus ECS/Fargate, ECR, ALB,
  Route 53, CloudWatch, RDS, database upgrades, and autoscaling.
- Explain tools used, daily activities, architecture decisions, and incident stories
  using evidence from completed work rather than memorized answers.

## Cost policy
Use existing hardware, local open-source tools, Docker Personal for eligible personal
learning, GitHub Free, a public repository, standard hosted runners, and public GHCR
images. Keep artifacts/cache within included allowances and recheck service terms.
No cloud account, credit card, paid runner, hosted database, domain purchase, paid
monitoring, or trial requiring later payment is part of the plan.

Official references checked on 2026-10-23:
- https://docs.github.com/en/billing/concepts/product-billing/github-actions
- https://docs.github.com/en/billing/concepts/product-billing/github-packages
- https://www.docker.com/products/personal/
- https://kind.sigs.k8s.io/
- https://fluxcd.io/flux/faq/
- https://docs.hashicorp.com/terraform/tutorials/kubernetes/kubernetes-provider
- https://learn.microsoft.com/en-us/windows/wsl/install
