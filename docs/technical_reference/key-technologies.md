# Key Development and Application Environment Technologies

## Shell

- [Devbox](https://www.jetify.com/devbox) - provides lightweight, isolated local shell environments, based on [Nix](https://nixos.org/). Provides the operating environment for QCrBox's command line management and development tools

## Python

QCrBox makes use of a number of drop-in replacement technologies for common Python environment tools that are more performant, mainly to reduce container provisioning time, but also development time:

- [hatch](https://hatch.pypa.io/latest/) - high-level and performant Python project manager
- [mamba](https://mamba.readthedocs.io/en/latest/) - performance-optimised Python package manager, drop-in replacement for Conda
- [uv](https://docs.astral.sh/uv/guides/install-python/) - performance-optimised Python package manager, drop-in replacement for the Pip package manager
- [pytest](https://docs.pytest.org/en/stable/) - automated unit test suite
- [ruff](https://docs.astral.sh/ruff/) - performant Python linter and code formatter

Documentation:

- [mkdocs](https://www.mkdocs.org/) - simple, lightweight markdown-based documentation generation
