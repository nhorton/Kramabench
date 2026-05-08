"""Shared base for SUTs that drive a Claude Code-style CLI.

Intentionally has no public re-exports: `ClaudeBasedSystem` is abstract-ish
(requires class-attr overrides + a CLI binary that doesn't ship by default)
and must not be reachable via `--sut`.
"""
