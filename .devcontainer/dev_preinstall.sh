#!/usr/bin/env bash
# Dev Pre-Install Script for Lucid RDP
# Path: .devcontainer/dev_preinstall.sh

set -euo pipefail

echo "[dev_preinstall] Updating apt..."
apt-get update -y

echo "[dev_preinstall] Installing system dependencies..."
DEBIAN_FRONTEND=noninteractive apt-get install -y \
  openjdk-17-jdk \
  git \
  curl \
  jq \
  netcat \
  tor

echo "[dev_preinstall] Upgrading pip..."
python -m pip install --upgrade pip

echo "[dev_preinstall] Installing Python dev requirements..."
if [[ -f ".devcontainer/requirements-dev.txt" ]]; then
  pip install -r .devcontainer/requirements-dev.txt
else
  echo "[dev_preinstall] WARNING: requirements-dev.txt not found!"
fi

echo "[dev_preinstall] Installing extra Python deps (Tor + Tron)..."
pip install torpy tronpy

echo "[dev_preinstall] Done. Installed:"
java -version || echo "Java not installed?"
python --version
pip list | grep -E 'torpy|tronpy'
