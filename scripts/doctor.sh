#!/usr/bin/env bash
set -u

required_tools="git openspec"
optional_tools="gh"
required_paths=".claude/commands/opsx .claude/skills openspec/config.yaml openspec/changes/reliable-agent-team-workflow"
required_change_files="openspec/changes/reliable-agent-team-workflow/proposal.md openspec/changes/reliable-agent-team-workflow/design.md openspec/changes/reliable-agent-team-workflow/tasks.md"
change_name="reliable-agent-team-workflow"

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

check_git_root() {
  if git rev-parse --show-toplevel >/dev/null 2>&1; then
    pass 'Current directory is inside a git repository'
  else
    fail 'Current directory is not inside a git repository'
  fi
}

check_claude_assets() {
  if [ -d ".claude/commands/opsx" ] && [ -d ".claude/skills" ]; then
    pass 'Claude command and skill directories are present'
  else
    fail 'Claude command or skill directory is missing'
  fi
}

check_local_state_boundary() {
  if git check-ignore -q .omc 2>/dev/null; then
    pass '.omc is ignored as local runtime state'
  else
    warn '.omc is not ignored; local runtime state may leak into version control'
  fi

  if git check-ignore -q .claude/settings.local.json 2>/dev/null; then
    pass '.claude/settings.local.json is ignored'
  else
    warn '.claude/settings.local.json is not ignored'
  fi
}

check_openspec_change() {
  if ! command -v openspec >/dev/null 2>&1; then
    info 'Skipping openspec status because openspec is missing'
    return
  fi

  printf '\nRunning OpenSpec health check...\n'
  if openspec status --change "$change_name" >/dev/null; then
    pass "OpenSpec change is readable: $change_name"
  else
    fail "OpenSpec change check failed: $change_name"
  fi
}

print_guidance() {
  printf '\nGuidance:\n'
  printf '  - Run ./scripts/bootstrap.sh for a quick prerequisite check.\n'
  printf '  - Run ./scripts/verify.sh for a read-only validation pass.\n'
  printf '  - Read docs/troubleshooting.md if a required tool or path is missing.\n'
}

info 'Diagnosing quickTeams environment'
printf '\nChecking commands...\n'
for tool in $required_tools; do
  check_command "$tool" "required"
done
for tool in $optional_tools; do
  check_command "$tool" "optional"
done

printf '\nChecking repository context...\n'
check_git_root
check_claude_assets
check_local_state_boundary

printf '\nChecking required repository paths...\n'
for path in $required_paths; do
  check_path "$path"
done
for path in $required_change_files; do
  check_path "$path"
done

check_openspec_change
print_guidance
printf '\n'
if [ "$failures" -eq 0 ]; then
  printf '[SUCCESS] Doctor finished with no blocking issues'
  if [ "$warnings" -gt 0 ]; then
    printf ' and %s warning(s)' "$warnings"
  fi
  printf '.\n'
  exit 0
fi

printf '[ERROR] Doctor found %s blocking issue(s)' "$failures"
if [ "$warnings" -gt 0 ]; then
  printf ' and %s warning(s)' "$warnings"
fi
printf '.\n'
exit 1
