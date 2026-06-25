# Updating the QCrBox Container Registry

This guide explains how to publish Docker images to [GitHub Container Registry (GHCR)](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry) and how to deploy using those published images.

Images are hosted under `ghcr.io/qcrbox`. All images must be published as a **matching set** — base images, registry service, and application images must all come from the same build, because `pyqcrbox` and `qcrboxtools` versions are baked in at build time. Mixing versions causes the registry to silently ignore incompatible containers.

For local development (building from source), see [Using qcb to manage QCrBox](use_qcb_to_interact_with_and_manage_qcrbox.md).

---

## Using prebuilt images

To deploy QCrBox from published GHCR images without building locally, set the desired version in `.env.prod`:

```bash
# .env.prod
QCRBOX_DOCKER_REPO=ghcr.io/qcrbox
QCRBOX_DOCKER_TAG=0.2.0
```

Then start with:

```bash
qcb up --prebuilt-images olex2_linux
```

`qcb up --prebuilt-images` uses `docker-compose.*.prebuilt.yml` for each application, which pulls `${QCRBOX_DOCKER_REPO}/<app>:${QCRBOX_DOCKER_TAG}` from GHCR instead of using locally built images.

### Private container access

GHCR supports private packages. To grant a collaborator pull access:

1. Set package visibility to private in the GHCR web UI (Organisation → Packages → Package Settings → Change visibility)
2. Add them as a package collaborator, or have them create a fine-grained PAT with `read:packages` scope

They then `docker login ghcr.io -u <user> -p <PAT>` and `qcb up --prebuilt-images` works without further changes.

---

## Publishing a release

### Prerequisites

Generate a GitHub Personal Access Token (PAT) with `write:packages` scope at [github.com/settings/tokens](https://github.com/settings/tokens), then log in:

```bash
docker login ghcr.io -u <github-username> -p <PAT>
```

### Full release

```bash
bash scripts/update_container_repository.sh 0.2.0
```

This script:

1. Creates git tag `v0.2.0`
2. Builds and pushes all images in dependency order (`base-ancestor` → `base-application` → `base-novnc` / `base-wine` → `registry` → public apps) with `QCRBOX_DOCKER_TAG=0.2.0`
3. Warns and skips any private app whose installer file is not present — see [Getting Licensed Components](obtain_licenced_components.md) to build those separately
4. Prints `git push origin v0.2.0` for you to run once satisfied

### Single image

For a hotfix to one image after a release:

```bash
export QCRBOX_DOCKER_REPO=ghcr.io/qcrbox
export QCRBOX_DOCKER_TAG=0.2.0
bash scripts/build/push-images.sh olex2_linux
```

Run `bash scripts/build/push-images.sh` (no arguments) for the full list of options and available applications.

---

## Listing published images

Images are visible in the [QCrBox GitHub organisation packages](https://github.com/orgs/QCrBox/packages). To query tags via the GitHub CLI:

```bash
gh api /orgs/QCrBox/packages/container/<image-name>/versions \
    --jq '.[].metadata.container.tags[]'
```
