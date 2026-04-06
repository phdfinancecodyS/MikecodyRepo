#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
TARGET_SCRIPT="${ROOT_DIR}/cody"
BIN_DIR="${HOME}/.local/bin"
LINK_PATH="${BIN_DIR}/cody"
ZSHRC="${HOME}/.zshrc"

if [[ ! -x "${TARGET_SCRIPT}" ]]; then
  echo "[install-cody] Missing executable launcher: ${TARGET_SCRIPT}"
  exit 1
fi

mkdir -p "${BIN_DIR}"
ln -sfn "${TARGET_SCRIPT}" "${LINK_PATH}"

if [[ -f "${ZSHRC}" ]]; then
  if ! grep -q 'export PATH="$HOME/.local/bin:$PATH"' "${ZSHRC}"; then
    {
      echo ""
      echo '# Ask Anyway cody command'
      echo 'export PATH="$HOME/.local/bin:$PATH"'
    } >> "${ZSHRC}"
  fi
else
  {
    echo '# Ask Anyway cody command'
    echo 'export PATH="$HOME/.local/bin:$PATH"'
  } > "${ZSHRC}"
fi

echo "[install-cody] Installed: ${LINK_PATH} -> ${TARGET_SCRIPT}"
echo "[install-cody] Open a new terminal, then run: cody"
