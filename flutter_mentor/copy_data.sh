#!/bin/bash

set -euo pipefail

ROOT_DATA_DIR="../data"
ASSETS_DIR="assets/data"

echo "Copying .txt data files from ${ROOT_DATA_DIR} to ${ASSETS_DIR}..."
mkdir -p "${ASSETS_DIR}"

shopt -s nullglob
files=("${ROOT_DATA_DIR}"/*.txt)
shopt -u nullglob

if [ ${#files[@]} -eq 0 ]; then
  echo "No .txt files found in ${ROOT_DATA_DIR}"
  exit 1
fi

for file_path in "${files[@]}"; do
  file_name="$(basename "${file_path}")"
  cp "${file_path}" "${ASSETS_DIR}/${file_name}"
  echo "Copied ${file_name}"
done

echo "Done."
