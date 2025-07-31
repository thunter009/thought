# Versioning Guide

This project uses automated semantic versioning based on conventional commits.

## Quick Start

1. **Install dependencies**:
   ```bash
   uv pip install -e ".[dev]"
   pre-commit install
   ```

2. **Write conventional commits**:
   ```bash
   # Features (minor version bump)
   git commit -m "feat: add new export format"

   # Bug fixes (patch version bump)
   git commit -m "fix: resolve CSV export issue"

   # Breaking changes (major version bump)
   git commit -m "feat!: change API interface"
   # or
   git commit -m "feat: new API

   BREAKING CHANGE: removed old endpoints"
   ```

## Commit Types

| Type | Description | Version Bump |
|------|-------------|--------------|
| `feat` | New feature | Minor (0.x.0) |
| `fix` | Bug fix | Patch (0.0.x) |
| `docs` | Documentation only | None |
| `style` | Code style changes | None |
| `refactor` | Code refactoring | None |
| `perf` | Performance improvements | None |
| `test` | Test changes | None |
| `build` | Build system changes | None |
| `ci` | CI configuration | None |
| `chore` | Other changes | None |

**Breaking changes**: Add `!` after type or include `BREAKING CHANGE:` in body → Major (x.0.0)

## How It Works

1. **Pre-commit hooks** validate commit messages using commitizen
2. **On merge to main**, GitHub Actions automatically:
   - Analyzes commits since last tag
   - Bumps version based on commit types
   - Updates `pyproject.toml`
   - Creates git tag
   - Generates changelog
   - Creates GitHub release

## Manual Version Bump

If needed, you can manually bump versions:

```bash
# Bump based on commits
cz bump

# Specific bump type
cz bump --increment PATCH
cz bump --increment MINOR
cz bump --increment MAJOR

# Dry run
cz bump --dry-run
```

## Changelog

View changelog with:
```bash
cz changelog
```

## Configuration

- **Config location**: `pyproject.toml` → `[tool.commitizen]`
- **Pre-commit hook**: `.pre-commit-config.yaml`
- **GitHub Actions**: `.github/workflows/auto-version.yml`

## Troubleshooting

**Invalid commit message?**
- Pre-commit hook will block the commit
- Use `git commit --amend` to fix the message
- Or use `git commit --no-verify` to skip (not recommended)

**Version not bumping?**
- Check if commits follow conventional format
- Ensure workflow has write permissions
- Look for `[skip ci]` in commit messages
