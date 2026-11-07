#!/usr/bin/env bash
set -euo pipefail

# Install pinned Linux amd64 binaries in ~/.local/bin without sudo.
if [[ "$(uname -s)" != Linux || "$(uname -m)" != x86_64 ]]; then
  echo "This installer supports Linux x86_64 only (run it in Ubuntu/WSL)." >&2
  exit 1
fi

bin_dir="$HOME/.local/bin"
mkdir -p "$bin_dir"
export PATH="$bin_dir:$PATH"
work_dir="$(mktemp -d)"
trap 'rm -rf "$work_dir"' EXIT

install_from_manifest() {
  local name="$1" version="$2" base_url="$3" asset="$4" manifest="$5"
  local binary="$work_dir/$asset" expected actual
  curl --fail --location --silent --show-error "$base_url/$asset" -o "$binary"
  curl --fail --location --silent --show-error "$base_url/$manifest" -o "$work_dir/$manifest"
  expected="$(awk -v file="$asset" '$2 == file || $2 == "*" file {print $1; exit} NF == 1 && length($1) == 64 {print $1; exit}' "$work_dir/$manifest")"
  if [[ ! "$expected" =~ ^[[:xdigit:]]{64}$ ]]; then
    echo "Could not find a SHA-256 entry for $asset in $manifest ($name $version)." >&2
    exit 1
  fi
  actual="$(sha256sum "$binary" | awk '{print $1}')"
  if [[ "$actual" != "$expected" ]]; then
    echo "SHA-256 mismatch for $name $version; refusing installation." >&2
    exit 1
  fi
  if [[ "$asset" == *.zip ]]; then
    unzip -q "$binary" -d "$work_dir/unpacked"
    install -m 0755 "$work_dir/unpacked/$name" "$bin_dir/$name"
  else
    install -m 0755 "$binary" "$bin_dir/$name"
  fi
  echo "Installed $name $version and verified its published SHA-256."
}

# Release versions are pinned intentionally; change them only after reviewing upstream releases.
if command -v terraform >/dev/null && terraform version | head -1 | grep -Fxq 'Terraform v1.17.1'; then
  echo 'Terraform 1.17.1 is already installed.'
elif curl --fail --silent --head --max-time 20 https://releases.hashicorp.com/terraform/1.17.1/terraform_1.17.1_linux_amd64.zip >/dev/null; then
  install_from_manifest terraform 1.17.1 \
    https://releases.hashicorp.com/terraform/1.17.1 \
    terraform_1.17.1_linux_amd64.zip terraform_1.17.1_SHA256SUMS
else
  # The release host can be region-blocked. Use only the official, digest-pinned
  # HashiCorp OCI image, whose layers Docker verifies, instead of an unknown mirror.
  image=hashicorp/terraform:1.17.1@sha256:a5d5a5a892c98f60fcbfa81eac2a40fc19e7b3fa7719bccae10ff6111d22524a
  echo 'Release host unavailable; extracting Terraform from the official digest-pinned image.'
  docker pull "$image"
  extract_container="$(docker create "$image")"
  if ! docker cp "$extract_container:/bin/terraform" "$work_dir/terraform"; then
    docker rm "$extract_container" >/dev/null
    exit 1
  fi
  docker rm "$extract_container" >/dev/null
  install -m 0755 "$work_dir/terraform" "$bin_dir/terraform"
fi
if command -v kind >/dev/null && kind version | grep -q '^kind v0.33.0 '; then
  echo 'kind 0.33.0 is already installed.'
else
  install_from_manifest kind 0.33.0 \
    https://kind.sigs.k8s.io/dl/v0.33.0 \
    kind-linux-amd64 kind-linux-amd64.sha256sum
fi
if command -v kubectl >/dev/null && kubectl version --client | head -1 | grep -Eq 'v1\.(36|37)\.'; then
  echo 'Reusing a compatible kubectl 1.36/1.37 client (Docker Desktop may supply it).'
else
  install_from_manifest kubectl 1.37.1 \
    https://dl.k8s.io/v1.37.1/bin/linux/amd64 \
    kubectl kubectl.sha256
fi

echo "Add $bin_dir to PATH if needed: export PATH=\"$bin_dir:\$PATH\""
terraform version
kind version
kubectl version --client
