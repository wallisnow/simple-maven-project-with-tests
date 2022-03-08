env.K8S_BUILDER_ENV = "k8s_image_build_env.groovy"

env.K8S_COMMON_METHODS = "k8s_image_build_methods.groovy"
env.CAPO_COMMON_METHODS = "capo_image_build_methods.groovy"
env.ERIKUBE_TAG = "eri_tag"
env.VARIABLE_FILE = "${WORKSPACE}/variables.txt"
env.CAPO_CONTAINER_LIST_WORKDIR = "${WORKSPACE}/kube-deployment/ansible/common"
env.CAPO_VALUEPACK_JSON = "${WORKSPACE}/valuepacks.json"
env.ARTIFACTORY_BASE_PATH = "https://host/artifactory/proj-erikube-generic-local/erikube"

