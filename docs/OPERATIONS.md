# Operations

Run commands in an Ubuntu terminal from the repository root. Compose and kind are
separate deployments with separate data. Record the environment before changing it.

## Diagnose a failure

1. Record user impact, start time, request path and the last working image/commit.
2. Follow the request: browser → Nginx → API → PostgreSQL → worker. Redis is a
   notification service; PostgreSQL contains the durable order queue.
3. Capture evidence before restarting:

   ```bash
   docker compose ps -a
   docker compose logs --since=10m web api worker db redis
   curl -i http://127.0.0.1:8080/health
   curl -i http://127.0.0.1:8080/ready
   docker stats --no-stream
   ```

4. Stabilize with a reversible change. Preserve database volumes and backups.
5. Verify a fresh order, an idempotent retry, completion and dependency readiness.
6. Record impact, timeline, cause, recovery and a specific preventive action.

| Symptom | Evidence and next action |
| --- | --- |
| Docker named pipe or socket missing | Start Docker Desktop; verify WSL integration and both Client/Server in `docker version` before rebuilding |
| Nginx 502 | Inspect API startup, DNS name `api`, port 8000 and readiness; recreate web after an upstream address changes |
| Nginx 504 or latency increase | Compare the same request before/after release; inspect dependency times, resource pressure and p95 metrics |
| Orders stay queued | Inspect worker logs, heartbeat, database access and queue depth; API health alone cannot detect this failure |
| Container restarts without a traceback | Inspect exit code and OOMKilled using `docker inspect`; on Kubernetes inspect events and `logs --previous` |
| CI fails without workflow changes | Identify the first failing step; inspect lock file, runner/tool versions, registries and new vulnerability findings |
| `/ready` 503 but orders complete | Redis may be unavailable while database polling still completes accepted work; restore Redis and verify readiness |

## Recovery checks

`bash scripts/recovery-check.sh` stops the worker and Redis, creates an order,
restarts the worker while Redis remains unavailable, verifies completion through
database polling, then restores Redis and readiness. Run against the main Compose
deployment only. It creates synthetic data and uses a trap to restart dependencies.

For a worker outage, stop `worker`, submit a few orders, observe the backlog,
then start `worker` and record recovery time. Preserve logs and observed timings.

## Backups and restoration

```bash
bash scripts/backup.sh
bash scripts/restore.sh --backup .backups/REPLACE_WITH_DUMP_FILENAME.dump
bash scripts/restore.sh --backup .backups/REPLACE_WITH_DUMP_FILENAME.dump --apply
```

The first restore command validates the dump and prints a plan. `--apply` creates
a **new** database and restores there; it does not replace the application's live
database. Record the reported order count and compare records with the source.
The script refuses an existing target. Backups and state belong outside Git and
need an independent copy for protection against computer/disk failure.

## Release and rollback

1. Record the change goal, commit/image tag, risk, dependencies and owner.
2. Run checks, disposable integration and vulnerability scans. Review findings.
3. Back up PostgreSQL and verify the compatible rollback version.
4. Build/promote an explicit image version; deploy to the selected environment.
5. Run the smoke check, inspect logs and monitor completion/latency/error metrics.
6. Record the outcome and any follow-up work.

Jenkins exposes the optional preview at `127.0.0.1:8083` only after successful
pipeline stages and an explicit `DEPLOY_PREVIEW` selection. It does not release to
AWS or automatically deploy to kind. The current tag is `0.1.0`; use unique
immutable tags/digests for multiple release revisions.

For Kubernetes:

```bash
kubectl --context kind-releaseops -n releaseops rollout status deployment/api --timeout=120s
kubectl --context kind-releaseops -n releaseops get pods,events
kubectl --context kind-releaseops -n releaseops rollout undo deployment/api
```

`rollout undo` requires a previous Deployment revision. It does not reverse
database changes. Update the desired manifest to the accepted image afterward.
The current schema command creates missing tables; incompatible schema evolution
requires versioned expand/contract migrations before release.

## Monitoring

Prometheus scrapes API and worker metrics; Grafana provisions the ReleaseOps
dashboard. Alertmanager groups local alerts without emailing or paging anyone.
Inspect target health before trusting an empty graph. Backlog, worker heartbeat,
errors and HTTP latency cover different failure modes. The configured thresholds
are operational starting points, not measured service-level guarantees.

Measure user-visible success and time to completion over a defined window before
setting an SLO. There is no external SLA for this local deployment.

## Maintenance, tickets and handovers

Review library/base-image updates, rebuild, rescan and test before promotion.
Assess exposure and remediation for findings; do not disable the security gate to
make it green. Pin reviewed inputs and keep credentials out of logs.

| Record | Required content |
| --- | --- |
| Change | Goal, revision, risk, test evidence, backup, rollback, release window, owner and verification |
| Incident | Impact, severity, start/end, timeline, actions, evidence and recovery |
| Service request | Requested task/access, requester, authorization and completion |
| Handover | Current health, open alerts, latest release, next action and responsible person |

Before Terraform apply, inspect the plan and confirm `kind-releaseops`. Keep local
state and backups private. The local backend supports this single-operator setup;
a team needs a deliberately configured shared backend, locking and access control.
Do not force-unlock an active operation or edit state as a first troubleshooting step.
