# How to create a release for QCrBox

## Step 1: Create a git tag

- Ensure your working tree is clean and all changes intended for the release are committed and merged to the main
  branch.
- Checkout the main branch and create an annotated tag for the release.

```bash
git checkout main && git pull
git tag -a v0.1.1 -m "Release v0.1.1"
```

## Step 2: Check out the tag

- Switch to the newly release tag to guarantee that the release is built from the exact tagged commit.

```bash
git checkout v0.1.1
```

## Step 3: Rebuild QCrBox

- Regenerate all QCrBox components to ensure the container images and `pyqcrbox` package contain the right version
  number.

```bash
qcb up --all
```

## Step 4: Push container images to Azure Container Registry

- Use the provided script to update and push the rebuilt images. You **must** update the version number variable (`VERSION`)
  with the version number of the release.

```bash
bash scripts/update_container_repository.sh
```

- Ensure you are authenticated to Azure and have the necessary permissions.

## Step 5: Create a GitHub release

- Navigate to the QCrBox repository on GitHub.
- Use **Draft a new release**, select the tag created earlier, and provide a short description of the update and include
  the release notes.

## Step 6: Upload wheel files

- Upload the wheels built from `qcb up -all` for `pyqcrbox` and `qcrboxtools`. They can be found in
  `QCrBox/services/base_images/base_ancestor/pyqcrbox_dist/` and
  `QCrBox/services/base_images/base_ancestor/qcrboxtools_dist/` respectively.
- Upload both wheels to the GitHub release page and tttach the generated `.whl` files to the release before publishing.
