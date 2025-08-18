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
