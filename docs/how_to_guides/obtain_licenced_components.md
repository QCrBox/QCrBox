Getting licensed components needed to build some containers
===========================================================

Some container dependencies are not freely available. Follow the per-app instructions below to obtain the required file, place it in the application directory, then build and push the image:

```bash
export QCRBOX_DOCKER_REPO=ghcr.io/qcrbox
export QCRBOX_DOCKER_TAG=latest
docker login ghcr.io -u <github-username> -p <PAT with write:packages>
bash scripts/build/push-apps.sh <app-name>   # e.g. mopro
```

The script reads `private_build.yml` in the application directory and reports exactly which file is missing if the installer has not been placed yet.

## MoPro
Obtain the Windows executable zip file named `MoProSuite_win_2024_10.zip` by registering [here](https://crm2.univ-lorraine.fr/de/die-software/mopro/download-mopro/). Then copy it into the QCrBox/services/applications/mopro directory as is.

## CrysAlisPro (support in development)
Register in the CrysAlisPro forum [here](https://www.rigakuxrayforum.com/). Then get the executable here: TBD.

## Eval14/15 (support in development)
Get a license as described [here](http://www.crystal.chem.uu.nl/distr/eval/). Then download the file using the obtained details from [here](http://www.crystal.chem.uu.nl/distr/eval/download/EVPY-Linux-x86_64-20231113-bullseye.tar.gz)

