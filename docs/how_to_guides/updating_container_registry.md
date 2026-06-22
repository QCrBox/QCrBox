# Updating the QCrBox Container Registry

This guide explains how to tag and push Docker images to QCrBox's [Azure Container Registry
(ACR)](https://learn.microsoft.com/en-us/azure/container-registry/), using the Azure CLI.

## Prerequisites

To push images to QCrBox's Azure Container Registry (ACR), you need to have the Azure CLI installed and configured and
to have access to QCrBox's Azure subscription/portal. If you do not have the Azure CLI installed, follow the [official
installation guide](https://learn.microsoft.com/en-us/cli/azure/install-azure-cli) for your operating system.

Once it is installed, you need to log into Azure and pick the subscription you want to link. Open your terminal and run:

```sh
az login
```

This will open a browser window for authentication. After logging in, you can verify your account with:

```sh
az account show
```

Once you are logged in, you need to also log into the ACR using:

```sh
az acr login --name qcrbox
```

## Uploading/updating an image

Assuming your image is built locally (e.g., `qcrbox/registry:latest`), you need to tag the local image with the address
of the Azure Container Registry (ACR) before pushing it:

```sh
docker tag qcrbox/registry:latest qcrbox.azurecr.io/qcrbox-registry:latest
```

The `qcrbox.azurecr.io` part is the hostname of the QCrBox ACR. Docker uses this address to know where to push (or
pull) the image. If you do not tag your image with the full registry address, Docker will not know to associate it with
the ACR, and the push will fail or go to the wrong place. Always use the full registry address when preparing images for
upload to Azure.

Once tagged, we can push the image to the ACR:

```sh
docker push qcrbox.azurecr.io/qcrbox-olex2-linux:latest
```

You should see the upload progress and a confirmation when the push is complete.

### List images in the QCrBox ACR

To see images in the ACR:

```sh
az acr repository list --name qcrbox --output table
```

To list tags for a specific image:

```sh
az acr repository show-tags --name qcrbox --repository qcrbox-registry --output table
```

## Using pre-built images

You can use the `qcb` tool to start services with pre-built images. For example, to start the `olex2` service with the
production image:

```sh
qcb up --prebuilt-images olex2
```

This command will use the production Docker Compose file for `olex2` and pull the image from the ACR if it is not
already present locally. To enable an application to pull form the ACR, you must include a `docker-compose.*.prebuilt.yml`
file in its directory in `QCrBox/services/applications/`. Instead of using the Dockerfile to build the image, you
instead use the image from the ACR. Below is an example of what the relevant section of this file might look like:

```yaml
services:
  olex2:
    image: ${QCRBOX_DOCKER_REPO:?Must set env var QCRBOX_DOCKER_REPO}/olex2-linux:${QCRBOX_DOCKER_TAG:?Must set env var QCRBOX_DOCKER_TAG}  # Pulls from the QCrBox ACR
    volumes:
      - ${QCRBOX_SHARED_FILES_DIR_HOST_PATH:?Must set env var QCRBOX_SHARED_FILES_DIR_HOST_PATH}:${QCRBOX_SHARED_FILES_DIR_CONTAINER_PATH:?Must set env var QCRBOX_SHARED_FILES_DIR_CONTAINER_PATH}
    networks:
      - qcrbox-net
    labels:
      traefik.enable: true
      traefik.http.routers.to-olex2-path-prefix.rule: Path(`/gui/olex2`)
      traefik.http.routers.to-olex2-path-prefix.middlewares: redirect-gui-olex2-path
      traefik.http.routers.to-olex2-path-prefix.service: olex2-service
      traefik.http.middlewares.redirect-gui-olex2-path.redirectregex.regex: ^http://(.+)/gui/olex2(/?)$$
      traefik.http.middlewares.redirect-gui-olex2-path.redirectregex.replacement: http://olex2.gui.$$1/vnc.html?path=vnc&autoconnect=true&resize=remote&reconnect=true&show_dot=true

      traefik.http.routers.to-olex2-subdomain.rule: HostRegexp(`^olex2\.gui\..+$$`)
      traefik.http.routers.to-olex2-subdomain.middlewares: redirect-gui-olex2-subdomain
      traefik.http.routers.to-olex2-subdomain.service: olex2-service
      traefik.http.middlewares.redirect-gui-olex2-subdomain.redirectregex.regex: ^http://olex2\.gui\.([^/]+)(/?)$$
      traefik.http.middlewares.redirect-gui-olex2-subdomain.redirectregex.replacement: http://olex2.gui.$$1/vnc.html?path=vnc&autoconnect=true&resize=remote&reconnect=true&show_dot=true

      traefik.http.services.olex2-service.loadbalancer.server.scheme: http
      traefik.http.services.olex2-service.loadbalancer.server.port: 8080
    depends_on:
      qcrbox-registry:
        condition: service_healthy
    # then you can configure environment variables and whatever else is required
```

This requires the following environment variables:

```sh
QCRBOX_DOCKER_REPO=qcrbox.azurecr.io
QCRBOX_DOCKER_TAG=latest
```
