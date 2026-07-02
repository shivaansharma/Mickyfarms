#!/bin/bash

SITE=$1

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
BENCH_DIR="$(dirname "$(dirname "$(dirname "$SCRIPT_DIR")")")"

cd "$BENCH_DIR"

git -C apps/assignment pull origin main
bench --site "$SITE" migrate
bench build
bench restart