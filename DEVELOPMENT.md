# Development Workflow

This file is for maintainers working from a mounted Home Assistant config volume.

## Source of truth
Edit only in:

`/config/ha_vibecode_git/custom_components/ir_fan_control`

Do not edit directly in:

`/config/custom_components/ir_fan_control`

## Deploy to live Home Assistant
```bash
./deploy.sh
```

If `/Volumes/config` is not mounted, the script exits safely and changes nothing.

## Lint
```bash
./lint.sh
```

What it does:
- syntax-checks Python files in `custom_components/ir_fan_control`
- runs `ruff` checks if `ruff` is installed

Install `ruff` (optional):

```bash
pipx install ruff
```

or

```bash
pip3 install ruff
```
