#!/usr/bin/env bash
set -u

required_tools="git openspec"
optional_tools="gh"
required_paths=".claude/commands/opsx .claude/skills openspec/config.yaml openspec/changes/reliable-agent-team-workflow"
required_change_files="openspec/changes/reliable-agent-team-workflow/proposal.md openspec/changes/reliable-agent-team-workflow/design.md openspec/changes/reliable-agent-team-workflow/tasks.md"

failures=0
warnings=0

info() {
  printf '[INFO] %s\n' "$1"
}

pass() {
  printf '[PASS] %s\n' "$1"
}

warn() {
  printf '[WARN] %s\n' "$1"
  warnings=$((warnings + 1))
}

fail() {
  printf '[FAIL] %s\n' "$1"
  failures=$((failures + 1))
}

check_command() {
  name="$1"
  requirement="$2"

  if command -v "$name" >/dev/null 2>&1; then
    pass "Found command: $name"
  else
    if [ "$requirement" = "required" ]; then
      fail "Missing required command: $name"
    else
      warn "Missing optional command: $name"
    fi
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

print_next_steps() {
  printf '\nNext steps:\n'
  printf '  1. Install any missing required tools.\n'
  printf '  2. Run ./scripts/verify.sh for read-only validation.\n'
  printf '  3. If gh is installed, you can also use GitHub-related helpers.\n'
}

info "Bootstrapping quickTeams repository checks"
printf '\nChecking commands...\n'
for tool in $required_tools; do
  check_command "$tool" "required"
done
for tool in $optional_tools; do
  check_command "$tool" "optional"
done

printf '\nChecking repository paths...\n'
for path in $required_paths; do
  check_path "$path"
done
for path in $required_change_files; do
  check_path "$path"
done

printf '\n'
if [ "$failures" -eq 0 ]; then
  printf '[SUCCESS] Repository bootstrap checks passed'
  if [ "$warnings" -gt 0 ]; then
    printf ' with %s warning(s)' "$warnings"
  fi
  printf '.\n'
  print_next_steps
  exit 0
fi

printf '[ERROR] Bootstrap checks failed with %s issue(s)' "$failures"
if [ "$warnings" -gt 0 ]; then
  printf ' and %s warning(s)' "$warnings"
fi
printf '.\n'
print_next_steps
exit 1
