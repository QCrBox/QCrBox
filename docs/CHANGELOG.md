---
hide:
  - navigation
---

# Changelog

All notable changes to this project will be documented in this file.

This project aims to follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
However, there will be an initial period of stabilisation where this is not adhered to
(releases with version numbers `0.0.x`).


## [Unreleased]

### New Features

### Enhancements

### Issues Fixed

### Development

### Documentation


## [0.0.1]

### New Features

- Docker base images:
   - `base-application`
   - `base-novnc` [#39](https://github.com/QCrBox/QCrBox/issues/39)
- Core components:
   - `qcrbox-message-bus` [#9](https://github.com/QCrBox/QCrBox/issues/9)
   - `qcrbox-registry` [#13](https://github.com/QCrBox/QCrBox/issues/13)
- Crystallographic applications:
   - CrystalExplorer [#44](https://github.com/QCrBox/QCrBox/issues/44)
   - Olex2 [#46](https://github.com/QCrBox/QCrBox/issues/46)
- CLI tool (`qcb`) for common development and deployment tasks. ([#10](https://github.com/QCrBox/QCrBox/issues/10))
- Python package (`qcrbox`) to interact with QCrBox from Python code. ([#14](https://github.com/QCrBox/QCrBox/issues/14))
- The base image now includes [cctbx](https://cci.lbl.gov/docs/cctbx/) and [QCrBoxTools](https://github.com/Niolon/QCrBoxTools.git). ([#53](https://github.com/QCrBox/QCrBox/issues/53))

### Documentation

- Created documentation skeleton. ([#2](https://github.com/QCrBox/QCrBox/issues/2))
- Set up GitHub Actions for continuous deployment of the [docs](https://qcrbox.github.io/QCrBox/) to GitHub pages. ([#11](https://github.com/QCrBox/QCrBox/issues/11))
- Added how-to guide on how to set up a development environment. ([#24](https://github.com/QCrBox/QCrBox/issues/24))

### Internal improvements

- The base images now use the [mamba](https://mamba.readthedocs.io/) package manager, resulting in much faster build times than using `conda`.
- All QCrBox-specific Python packages are now installed in the base mamba environment. The separate Python virtual environment has been removed. ([#54](https://github.com/QCrBox/QCrBox/issues/54))



[unreleased]: https://github.com/QCrBox/QCrBox/compare/0.0.1...master
[0.0.1]: https://github.com/QCrBox/QCrBox/compare/initial_commit...0.0.1
