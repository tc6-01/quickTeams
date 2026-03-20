#!/usr/bin/env bash
set -u

required_tools="git openspec"
required_paths=".claude/commands/opsx .claude/skills openspec/config.yaml openspec/changes/reliable-agent-team-workflow"
required_change_files="openspec/changes/reliable-agent-team-workflow/proposal.md openspec/changes/reliable-agent-team-workflow/design.md openspec/changes/reliable-agent-team-workflow/tasks.md"
change_name="reliable-agent-team-workflow"

failures=0

info() {
  printf '[INFO] %s\n' "$1"
}

pass() {
  printf '[PASS] %s\n' "$1"
}

fail() {
  printf '[FAIL] %s\n' "$1"
  failures=$((failures + 1))
}

check_command() {
  name="$1"

  if command -v "$name" >/dev/null 2>&1; then
    pass "Found command: $name"
  else
    fail "Missing required command: $name"
  fi
}

check_path() {
  path="$1"

  if [ -e "$path" ]; then
    pass "Found path: $path"
  else
    fail "Missing path: $path"
  fi
}

run_read_only_check() {
  if [ "$failures" -ne 0 ]; then
    info "Skipping openspec status because prerequisite checks failed"
    return
  fi

  printf '\nRunning read-only OpenSpec validation...\n'
  if openspec status --change "$change_name"; then
    pass "openspec status succeeded for change: $change_name"
  else
    fail "openspec status failed for change: $change_name"
  fi
}

info "Verifying quickTeams repository"
printf '\nChecking required commands...\n'
for tool in $required_tools; do
  check_command "$tool"
done

printf '\nChecking required paths...\n'
for path in $required_paths; do
  check_path "$path"
done
for path in $required_change_files; do
  check_path "$path"
done

run_read_only_check
printf '\n'
if [ "$failures" -eq 0 ]; then
  printf '[SUCCESS] Verification passed. Repository looks ready to use.\n'
  printf 'Next step: start working with the change or rerun this script after updates.\n'
  exit 0
fi

printf '[ERROR] Verification failed with %s issue(s).\n' "$failures"
printf 'Fix the missing prerequisites above, then rerun ./scripts/verify.sh.\n'
exit 1
