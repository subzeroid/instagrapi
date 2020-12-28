#!/usr/bin/env bash
set -e

# If no arguments, drop into a bash shell.
# If arguments are passed and the first argument is "test", run the test suite,
# otherwise execute what was passed.
if [[ $# == 0 ]]; then
  /bin/bash
elif [[ $1 == "test" ]]; then
  shift
  source docker/entrypoints/run_tests.sh "$@"
else
  exec "$@"
fi
