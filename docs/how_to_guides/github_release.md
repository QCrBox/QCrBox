# How to create a release for QCrBox

## Step 1: Prepare the branch

Ensure your working tree is clean and all changes are committed and merged to the target branch.

```bash
git checkout dev && git pull
```

## Step 2: Push all QCrBox images to GHCR

Log in to GHCR and run the release script. It creates the git tag, builds every image in dependency order, and pushes to `ghcr.io/qcrbox`:

```bash
docker login ghcr.io -u <github-username> -p <PAT with write:packages>
bash scripts/update_container_repository.sh 0.2.0
# Add --tag-latest if this is the new default release
bash scripts/update_container_repository.sh 0.2.0 --tag-latest
```

Private app images (MoPro, CrysAlis Pro, Eval15) are skipped with a warning if the installer files are not present — see [Getting Licensed Components](obtain_licenced_components.md).

## Step 3: Push the frontend image

From the QCrBoxFrontend repository:

```bash
bash scripts/push-frontend.sh 0.2.0
# Add --tag-latest to also update the :latest tag
bash scripts/push-frontend.sh 0.2.0 --tag-latest
```

## Step 4: Push the git tag

```bash
git push origin v0.2.0
```

## Step 5: Create a GitHub release

Navigate to the QCrBox repository on GitHub. Use **Draft a new release**, select the tag `v0.2.0`, and add a short description and release notes.

## Step 6: Upload wheel files

Attach the `pyqcrbox` and `qcrboxtools` wheel files to the release. They are built as part of `update_container_repository.sh` and can be found at:

- `services/base_images/base_ancestor/pyqcrbox_dist/*.whl`
- `services/base_images/base_ancestor/qcrboxtools_dist/*.whl`
