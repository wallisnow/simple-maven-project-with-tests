#!/bin/bash
container_name="jenkins_dev"
container_version="v1.0"
img_name="${container_name}:${container_version}"
docker_gid="994"
USER="vagrant"
docker_file="jenkins_image.Dockerfile"

docker build \
       -t "${img_name}" \
       --build-arg USER="${USER}" \
       --build-arg DOCKER_GID="${docker_gid}" \
       --build-arg USER_UID="$(id -u "${USER}")" \
       --build-arg CONTAINER_NAME="${container_name}" \
       -f "${BUILD_DIR}"/"${docker_file}" \
       "${BUILD_DIR}"