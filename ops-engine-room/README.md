# Ops Engine Room

Operations workspace for developer workflow automation and infrastructure code.

## Structure

- `git-hooks/` - local Git hook sources and installer
- `infrastructure/` - Terraform environments and modules
  - `production-environment/`
  - `monitoring-environment/`
  - `diagram-engine-room/`

## Git Hooks

Hook sources are versioned in `ops-engine-room/git-hooks/` and installed into `.git/hooks/`.

### Install locally

Run from repository root:

```bash
bash ops-engine-room/git-hooks/setup.sh
```

### Installed hooks

- `pre-commit`
  - If `backend/` changed: runs `mvn clean compile checkstyle:check` in `backend/`
  - If `qa/api-tests/` changed: runs `mvn clean compile` in `qa/api-tests/`
  - Infrastructure changes do not trigger Terraform checks in this hook
- `commit-msg`
  - Enforces Conventional Commits
  - Requires issue reference in commit message (`(#123)`, `Closes #123`, `Fixes #123`)
  - If branch contains a ticket number, commit message must reference the same ticket number

### Backend Maven auto-install

Running Maven in `backend/` from phase `initialize` onward installs/refreshes hooks:

```bash
cd backend
mvn initialize
```

## Commit Message Standard

Required header format:

```text
<type>(optional-scope): short description
```

Allowed types:

- `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`, `build`, `ci`, `perf`

Description rules:

- starts with lowercase
- maximum 72 characters
- does not end with a period

Valid example:

```text
feat(auth): add login rate limiting (#123)
```

## Secret Scanning

Local hooks do not run secret scanning.

Secret detection is enforced in CI with Gitleaks.

## Infrastructure Notes

Terraform code is organized by environment under `ops-engine-room/infrastructure/`.

Typical commands (run inside a specific environment folder):

```bash
terraform init
terraform validate
terraform plan
```
