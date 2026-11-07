# Verification record

Local validation on 2026-11-07, Windows 11 with Ubuntu 22.04 under WSL 2,
Docker Desktop Linux engine 29.9.2, Compose 5.6.1, Python 3.14.9 and uv 0.13.5.
Results below distinguish executed checks from configuration awaiting integration.

| Check | Result |
| --- | --- |
| `bash scripts/check.sh` | Passed: locked dependencies, Ruff lint, formatting, 14 pytest cases |
| API runtime image build | Passed: `releaseops-api:0.1.0` |
| Nginx/browser image build | Passed: `releaseops-web:0.1.0` |
| API runtime identity | Passed: UID 10001 in the actual image |
| Live API + separate worker, SQLite | Passed: health 200, submission 202, duplicate-key retry returns the same ID, worker completes persisted order with Redis unavailable |
| Bash configuration scripts | Passed: syntax checks |
| Base and Jenkins Compose models | Passed: `docker compose config --quiet` |
| Kubernetes manifests | Passed: local Kustomize rendering; API-server validation is still pending |
| kind CLI | Installed: 0.33.0; official release SHA-256 verified |
| kubectl | Docker Desktop supplied Linux client 1.36.1 |
| Terraform CLI and formatting | Installed: 1.17.1; `fmt -check` passes |
| Terraform provider initialization | Blocked: registry discovery returns HTTP 404 with `x-amzn-waf-reason: geo` and a regional access message |
| Terraform validate/plan/apply | Pending provider initialization and a ready local cluster |
| PostgreSQL/Redis Compose integration | Pending first-time image downloads |
| Redis/worker recovery against Compose | Pending healthy full Compose deployment |
| Database backup and separate-database restore | Pending healthy PostgreSQL container |
| Image vulnerability scans | Pending scanner/image/database downloads; no clean-scan claim |
| Jenkins agent connection and pipeline | Pending first-time engine/controller/agent downloads and startup |
| Kubernetes rollout and smoke check | Pending node image download, cluster readiness and platform provisioning |
| Monitoring targets/dashboard/alert behavior | Configuration supplied; live checks pending |
| Updated hosted GitHub Actions workflow | Not yet run for this revision; older foundation workflow results do not validate the expanded pipeline |

The live image check used an ephemeral SQLite database inside the container and
removed the container afterward. It verifies packaging, non-root execution, HTTP
and separate-worker behavior; it does not substitute for PostgreSQL concurrency,
Redis connectivity, Nginx routing or cluster validation.

## Environment findings

- Starting Docker Desktop and enabling Ubuntu-22.04 WSL integration restored the
  Linux Docker socket and Client/Server connectivity before builds.
- Downloads on this connection were slow: the API dependency layer took about
  572 seconds and the Nginx base image about 699 seconds. There is no measured
  deployment-time or availability claim derived from these first downloads.
- HashiCorp's release site and provider registry returned a regional block. The
  CLI was extracted from the official digest-pinned HashiCorp OCI image; no
  unofficial provider mirror, region bypass or fabricated lock file was used.
- The initial kind node tag was unavailable. The configuration now selects
  `v1.36.4` with the exact digest from the
  [kind 0.33.0 release](https://github.com/kubernetes-sigs/kind/releases/tag/v0.33.0).

## Complete the remaining checks

Follow [deployment](DEPLOYMENT.md), stopping at a failed prerequisite. Once image
downloads finish, validate full Compose integration and recovery, restore a backup
into a new database, confirm monitoring targets and dashboard provisioning, then
run the real Jenkins pipeline. For Kubernetes, successful Terraform provider
initialization/validation and a reviewed plan precede apply and workload rollout.

Record exact revision, command, outcome and meaningful measurements when updating
this file. Configuration presence, a running process, and verified user-visible
behavior are different levels of evidence.
