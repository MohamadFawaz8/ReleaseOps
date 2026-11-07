# Deployment

## 1. Prepare Windows and Ubuntu

1. Install [VS Code](https://code.visualstudio.com/download), its Microsoft WSL
   extension and [Docker Desktop](https://docs.docker.com/desktop/setup/install/windows-install/).
   This personal project uses no paid cloud subscription.
2. On Windows, install WSL/Ubuntu if absent with `wsl --install -d Ubuntu-22.04`
   from an administrator PowerShell, restart if requested, then create a personal
   Ubuntu user. Do not reinstall an existing distribution.
3. Start Docker Desktop. Under Settings → General select the WSL 2 engine. Under
   Resources → WSL Integration enable **Ubuntu-22.04**, then Apply & restart.
4. In VS Code select **WSL: Connect to WSL using Distro** → Ubuntu-22.04. Open the
   repository folder. In its Ubuntu terminal confirm:

   ```bash
   whoami
   cat /etc/os-release
   docker version
   docker compose version
   ```

   Docker must show a Server section. A Windows `PS C:\...>` prompt is PowerShell;
   the commands below require the Ubuntu shell, such as `mohamad@MSI:...$`.
5. Clone if necessary using `git clone https://github.com/MohamadFawaz8/ReleaseOps.git`
   and enter the resulting directory. A Linux-home checkout improves I/O compared
   with `/mnt/c`; the existing Windows-mounted checkout also works.
6. Install [uv](https://docs.astral.sh/uv/getting-started/installation/) using its
   official standalone installer, reopen the terminal and run `uv --version`.
   The project uses uv 0.13.5 and Python 3.14.9; `uv python install` reads the
   project's Python selection. Leave Ubuntu's system Python in place.

## 2. Start the application

From the repository root:

```bash
bash scripts/local-secrets.sh
uv python install
bash scripts/check.sh
bash scripts/build.sh
docker compose up -d --wait
docker compose ps -a
docker compose exec -T -e BASE_URL=http://web:8080 api python - < scripts/smoke.py
```

Stop at the first error and inspect it before continuing. `local-secrets.sh`
creates `.env` with random credentials and refuses to overwrite an existing file.
Do not publish `.env` or resolved Compose output containing passwords. The schema
initializer should exit 0; the long-running services should be up.

Open [the application](http://127.0.0.1:8080). PostgreSQL and Redis are internal
services with no host-published ports. `docker compose down` retains data.
Use `logs --tail=80 SERVICE` for startup problems.

## 3. Add monitoring

```bash
docker compose --profile monitoring up -d
docker compose --profile monitoring ps
```

- [Prometheus targets](http://127.0.0.1:9090/targets): API and worker should be up.
- [Grafana](http://127.0.0.1:3000): use `GRAFANA_ADMIN_USER` and the generated
  `GRAFANA_ADMIN_PASSWORD` from the ignored `.env`. Open the ReleaseOps dashboard.
- [Alertmanager](http://127.0.0.1:9093): local groups; no external notifications.

Run `bash scripts/recovery-check.sh` to exercise worker/database recovery. See the
[operations runbook](OPERATIONS.md) for backups and failure diagnosis.

## 4. Use GitHub Actions

The workflow runs for pushes to `main`, pull requests targeting `main`, and a
manual dispatch. A feature branch needs a pull request to trigger its PR checks.
Open Actions → ReleaseOps CI → run → checks to inspect each command.

It creates a fresh runner environment, installs locked dependencies, checks code,
builds disposable containers, verifies order completion, and scans runtime images.
No AWS credentials, Docker Hub login or laptop-cluster credentials are needed.
The disposable test project deletes its own volumes on completion. Public standard
hosted runners are used; do not select a larger billed runner.

## 5. Start local Jenkins

Allow disk space for Java, agent, Docker engine and caches. On a 16 GB computer,
run the Kubernetes and Jenkins environments separately.

```bash
bash scripts/jenkins-setup.sh
cat .secrets/jenkins-admin-password
```

Open [Jenkins](http://127.0.0.1:8081), sign in as `releaseops` with that local
password. Wait for `releaseops-agent` to be online, open `releaseops-ci`, then
**Build with Parameters**. Leave `DEPLOY_PREVIEW` false for verification, or select
it to deploy to [the preview](http://127.0.0.1:8083). The initial job definition
already registers this parameter before the first build.

The controller schedules jobs with zero executors. Its agent runs checks/builds
against explicitly mounted source. This is a trusted local-workspace job, not an
untrusted public-PR runner or automatic webhook integration. Restart the controller
after changing Jenkinsfile so its initialized job definition updates. The isolated
privileged Docker engine uses mutual TLS on an internal network; neither the host
socket nor the Docker API is published.

For management commands load the local credential into the Ubuntu shell first:

```bash
export JENKINS_ADMIN_PASSWORD="$(cat .secrets/jenkins-admin-password)"
docker compose -f compose.jenkins.yaml logs --tail=80 jenkins agent engine
docker compose -f compose.jenkins.yaml down
unset JENKINS_ADMIN_PASSWORD
```

Stopping preserves Jenkins and preview data. Deleting this project's volumes
deletes its job/build records, preview database and Docker cache.

## 6. Create the separate local Kubernetes deployment

Use Ubuntu. Prerequisites: working Docker engine, curl, unzip and project images.
The installer downloads pinned Linux binaries and verifies published checksums
before installation into `~/.local/bin` without sudo.

```bash
bash scripts/install-platform-tools.sh
export PATH="$HOME/.local/bin:$PATH"
bash scripts/cluster-up.sh
terraform -chdir=infra/terraform init
terraform -chdir=infra/terraform fmt -check
terraform -chdir=infra/terraform validate
terraform -chdir=infra/terraform plan -out=platform.tfplan
terraform -chdir=infra/terraform apply platform.tfplan
bash scripts/k8s-secrets.sh
bash scripts/k8s-deploy.sh
bash scripts/k8s-smoke.sh
```

Inspect the plan: only the `releaseops` namespace, quota, limit defaults and service
account should be created. Terraform uses the named `kind-releaseops` kubeconfig
context and local state. It does not create AWS resources or create the cluster.
kind owns the local node container; Kustomize owns workloads. Do not manage the
same objects with both tools.

The secret script generates namespace-local credentials outside Terraform state.
Workloads load local `0.1.0` images, wait for PostgreSQL, initialize schema and verify
rollouts. Access the Kubernetes deployment on localhost:8082 as instructed by the
smoke script; keep port forwarding active for browser access.

If an official release host returns a regional/connectivity error, installation
must fail rather than use an unchecked download. Inspect the URL and use an
official-image fallback where available; do not substitute an arbitrary mirror.
First-time node/image/provider downloads can take time.

The separate **ReleaseOps Platform** Actions workflow verifies this sequence on
an ephemeral runner-local cluster. It does not deploy to your laptop. See the
verification record for hosted results and the separate local registry limitation.

```bash
kubectl --context kind-releaseops -n releaseops get pods,svc,pvc
kubectl --context kind-releaseops -n releaseops get events --sort-by=.lastTimestamp
kubectl --context kind-releaseops -n releaseops logs deployment/worker
```

Before cleanup back up required data. `terraform destroy` deletes the namespace
and everything inside it; `bash scripts/cluster-down.sh` deletes the cluster and
its storage. These are destructive cleanup commands, not application restarts.
