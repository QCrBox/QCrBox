az login
az acr login --name qcrbox

docker tag qcrbox/base-ancestor:latest qcrbox.azurecr.io/base-ancestor:latest
docker tag qcrbox/base-application:latest qcrbox.azurecr.io/base-application:latest
docker tag qcrbox/base-novnc:latest qcrbox.azurecr.io/base-novnc:latest
docker tag qcrbox/base-wine:latest qcrbox.azurecr.io/base-wine:latest
docker tag qcrbox/registry:latest qcrbox.azurecr.io/registry:latest
docker tag qcrbox/olex2-linux:latest qcrbox.azurecr.io/olex2-linux:latest
docker tag qcrbox/qcrboxtools:latest qcrbox.azurecr.io/qcrboxtools:latest
docker tag qcrbox/crystal-explorer:latest qcrbox.azurecr.io/crystal-explorer:latest
docker tag qcrbox/qcrbox_quality:latest qcrbox.azurecr.io/qcrbox_quality:latest
docker tag qcrbox/cod_check:latest qcrbox.azurecr.io/cod_check:latest
docker tag qcrbox/xharpy-gpaw:latest qcrbox.azurecr.io/xharpy-gpaw:latest
docker tag qcrbox/mopro:latest qcrbox.azurecr.io/mopro:latest

docker push qcrbox.azurecr.io/base-ancestor:latest
docker push qcrbox.azurecr.io/base-application:latest
docker push qcrbox.azurecr.io/base-novnc:latest
docker push qcrbox.azurecr.io/base-wine:latest
docker push qcrbox.azurecr.io/registry:latest
docker push qcrbox.azurecr.io/olex2-linux:latest
docker push qcrbox.azurecr.io/crystal-explorer:latest
docker push qcrbox.azurecr.io/qcrboxtools:latest
docker push qcrbox.azurecr.io/qcrbox_quality:latest
docker push qcrbox.azurecr.io/cod_check:latest
docker push qcrbox.azurecr.io/xharpy-gpaw:latest
docker push qcrbox.azurecr.io/mopro:latest

VERSION=0.1.1
docker tag qcrbox/base-ancestor:latest qcrbox.azurecr.io/base-ancestor:$VERSION
docker tag qcrbox/base-application:latest qcrbox.azurecr.io/base-application:$VERSION
docker tag qcrbox/base-novnc:latest qcrbox.azurecr.io/base-novnc:$VERSION
docker tag qcrbox/base-wine:latest qcrbox.azurecr.io/base-wine:$VERSION
docker tag qcrbox/registry:latest qcrbox.azurecr.io/registry:$VERSION
docker tag qcrbox/olex2-linux:latest qcrbox.azurecr.io/olex2-linux:$VERSION
docker tag qcrbox/qcrboxtools:latest qcrbox.azurecr.io/qcrboxtools:$VERSION
docker tag qcrbox/crystal-explorer:latest qcrbox.azurecr.io/crystal-explorer:$VERSION
docker tag qcrbox/qcrbox_quality:latest qcrbox.azurecr.io/qcrbox_quality:$VERSION
docker tag qcrbox/cod_check:latest qcrbox.azurecr.io/cod_check:$VERSION
docker tag qcrbox/xharpy-gpaw:latest qcrbox.azurecr.io/xharpy-gpaw:$VERSION
docker tag qcrbox/mopro:latest qcrbox.azurecr.io/mopro:$VERSION

docker push qcrbox.azurecr.io/base-ancestor:$VERSION
docker push qcrbox.azurecr.io/base-application:$VERSION
docker push qcrbox.azurecr.io/base-novnc:$VERSION
docker push qcrbox.azurecr.io/base-wine:$VERSION
docker push qcrbox.azurecr.io/registry:$VERSION
docker push qcrbox.azurecr.io/olex2-linux:$VERSION
docker push qcrbox.azurecr.io/crystal-explorer:$VERSION
docker push qcrbox.azurecr.io/qcrboxtools:$VERSION
docker push qcrbox.azurecr.io/qcrbox_quality:$VERSION
docker push qcrbox.azurecr.io/cod_check:$VERSION
docker push qcrbox.azurecr.io/xharpy-gpaw:$VERSION
docker push qcrbox.azurecr.io/mopro:$VERSION
