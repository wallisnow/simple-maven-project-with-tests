//env.CICD_DIR = "cicd"
//env.ANSIBLE_DIR = "erikube-deployment/ansible/erikube"
//env.ARMDOCKER_CREDENTIAL_ID = "00da472d-25c8-4a5e-92ac-9e560dd60498"
//
//env.OS_AUTH_VERSION = "3"
//env.OS_DOMAIN_NAME = (env.OS_DOMAIN_NAME) ? env.OS_DOMAIN_NAME : "LAB"
//env.OS_USER_DOMAIN_NAME = (env.OS_USER_DOMAIN_NAME) ?
//                           env.OS_USER_DOMAIN_NAME :
//                           env.OS_DOMAIN_NAME
//env.OS_PROJECT_DOMAIN_NAME = (env.OS_PROJECT_DOMAIN_NAME) ?
//                              env.OS_PROJECT_DOMAIN_NAME :
//                              env.OS_DOMAIN_NAME
//env.OS_TENANT_ID = "$OS_PROJECT_ID"
//env.OS_TENANT_NAME = "$OS_PROJECT_NAME"
//env.OS_IDENTITY_API_VERSION = "3"
//env.OS_REGION_NAME = (env.OS_REGION_NAME) ? env.OS_REGION_NAME : "regionOne"
//
//env.OS_SSH_USERNAME = "sles"
//env.IMAGE_VISIBILITY = "public"
//env.ANSIBLE_EMPTY_GROUPS = ""
//env.IMAGE_OUTPUT_DIR = "/home/jenkins"
//env.PACKER_LOG = "LOGLEVEL2"
//env.PACKER_BIN_PATH = "/usr/local/bin/packer"
//env.PACKER_VERSION = "1.3.5"
env.HOST_IMAGE_TYPE = "SLES"
//env.VARIABLE_FILE = "${WORKSPACE}/variables.txt"
//env.SHELL_CMD="/bin/sh -c 'packer build image_build.json'"
//env.TERM_FLAGS="-t --privileged"
//
//env.BASE_K8S_BUILD_ARTIFACTS_LOCATION="https://arm.rnd.ki.sw.ericsson.se/artifactory/"+
//    "proj-erikube-generic-local/erikube/build/eccd-ibd-k8s-image-builder"
//env.K8S_BUILD_ARTIFACTS_LOCATION_SUFFIX=
//    (env.OS_AUTH_URL && env.OS_AUTH_URL.contains("serodc92ceenbi")) ? "-n92" : ""
//env.K8S_BUILD_ARTIFACTS_LOCATION=BASE_K8S_BUILD_ARTIFACTS_LOCATION +
//     K8S_BUILD_ARTIFACTS_LOCATION_SUFFIX