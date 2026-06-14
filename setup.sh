#!/usr/bin/env bash
# setup.sh — bootstrap a native Nix + flakes environment for this repo on WSL2/Linux.
#
# Goal: run `bash setup.sh` once, then `nix develop --accept-flake-config`
#       to drop into the dev shell and run your code.
#
# Safe to re-run (idempotent): it skips anything already in place.
#
# Why single-user Nix (--no-daemon)?
#   On WSL2 this is the path of least resistance:
#     * non-interactive  -> `bash setup.sh` finishes without prompts
#     * no systemd needed -> works on any WSL distro
#     * YOU own /nix, so you're a *trusted user* -> `--accept-flake-config`
#       actually honors the flake's m-labs binary cache instead of silently
#       falling back to building ARTIQ from source.
#   Trade-off: weaker build isolation than the daemon install. Irrelevant here,
#   since we fetch from a cache and run simulations rather than building a
#   shared multi-user store.

set -euo pipefail

log()  { printf '\033[1;34m==>\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[!]\033[0m  %s\n' "$*"; }
die()  { printf '\033[1;31m[x]\033[0m  %s\n' "$*" >&2; exit 1; }

# --- 0. sanity checks ------------------------------------------------------
[ "$(uname -s)" = "Linux" ]  || die "Linux/WSL2 only (got $(uname -s)). Run this *inside* Ubuntu, not PowerShell."
[ "$(uname -m)" = "x86_64" ] || die "Need x86_64 (got $(uname -m))."

# Functional userns check — the authoritative test the sandbox depends on.
# (The kernel.unprivileged_userns_clone sysctl doesn't exist under WSL's
#  Microsoft kernel; trust the behavioral check, not the config flag.)
if ! unshare -U -r true 2>/dev/null; then
  die "User namespaces are blocked. On Ubuntu 24.04 this is AppArmor — reinstall as Ubuntu-22.04."
fi

# --- 1. OS prerequisites ---------------------------------------------------
if command -v apt-get >/dev/null 2>&1; then
  log "Installing prerequisites (git curl ca-certificates xz-utils)…"
  sudo apt-get update -qq
  sudo apt-get install -y -qq git curl ca-certificates xz-utils
else
  warn "Non-apt distro: ensure git, curl, ca-certificates, xz are present."
fi

# --- 2. install Nix (only if absent) --------------------------------------
if command -v nix >/dev/null 2>&1; then
  log "Nix already installed: $(nix --version)"
else
  log "Installing Nix (single-user)…"
  curl --proto '=https' --tlsv1.2 -L https://nixos.org/nix/install | sh -s -- --no-daemon
fi

# --- 3. load Nix into THIS shell ------------------------------------------
# The installer appends a source line to your ~/.profile / ~/.bashrc for future
# shells, but those aren't loaded yet in this run — so source it manually.
if [ -e "$HOME/.nix-profile/etc/profile.d/nix.sh" ]; then
  . "$HOME/.nix-profile/etc/profile.d/nix.sh"                        # single-user
elif [ -e /nix/var/nix/profiles/default/etc/profile.d/nix-daemon.sh ]; then
  . /nix/var/nix/profiles/default/etc/profile.d/nix-daemon.sh        # multi-user (if pre-existing)
fi
command -v nix >/dev/null 2>&1 || die "Nix installed but not on PATH. Open a fresh shell and re-run."

# --- 4. enable flakes + nix-command ---------------------------------------
NIX_CONF_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/nix"
mkdir -p "$NIX_CONF_DIR"
if ! grep -qs 'experimental-features.*flakes' "$NIX_CONF_DIR/nix.conf" 2>/dev/null; then
  log "Enabling experimental-features = nix-command flakes…"
  echo 'experimental-features = nix-command flakes' >> "$NIX_CONF_DIR/nix.conf"
fi

# --- 5. done ---------------------------------------------------------------
log "Nix ready: $(nix --version)"
cat <<'EOF'

────────────────────────────────────────────────────────────────────────────
Setup complete. Next, from the repo root:

    nix develop --accept-flake-config        # enter the dev shell
    cd qubit_control && bash start_experiment.sh

First `nix develop` pulls the closure from the m-labs + nixos.org caches
(1–3 GB, ~5–15 min). --accept-flake-config lets the flake supply its own
binary cache, so ARTIQ is *fetched*, not rebuilt from source.

To stop typing the flag each time, add the m-labs substituter to nix.conf
permanently — copy the exact substituter URL + public key from the flake's
own `nixConfig` block (authoritative source) into ~/.config/nix/nix.conf as:
    extra-substituters = <url from flake>
    extra-trusted-public-keys = <key from flake>
Then plain `nix develop` works.
────────────────────────────────────────────────────────────────────────────
EOF
