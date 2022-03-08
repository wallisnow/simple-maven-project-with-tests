void test(){
    echo("--> test load script")
}

def runStage(
        String stageName, int stageTimeout, String timeoutUnits, Closure stageAction,
        Closure catchAction={}, String buildResult='FAILURE', Closure finalAction={})
{
    def log = load "${WORKSPACE}/logs.groovy"
    wrap([$class: 'AnsiColorBuildWrapper', 'colorMapName': 'xterm']) {
        log.echoWithColor("blue", "${stageName}")
        timeout(time: stageTimeout, unit: timeoutUnits) {
            try {
                stageAction()
            } catch(Exception e) {
                //log.addError("${stageName} failed with ${e}")
                manager.addShortText("${stageName}", "white", "red", "2px", "black")
                log.echoWithColor("red", "catch: ${e}")
                catchAction()
                log.echoWithColor("red", "Set currentBuild.result to " + buildResult)
                currentBuild.result = buildResult
                if (buildResult == 'FAILURE') {
                    log.echoWithColor("red", "throw exception")
                    throw e
                }
            } finally {
                finalAction()
            }
        }
    }
}

void buildSourceCode(int stageTimeout, String timeoutUnits='MINUTES') {
    String stageName = "Build source code"
    def stageAction = {
        String buildDecisionCmd = '''\
        #!/bin/bash -xe
        source common/utils/kube-tag.sh
        #creds="--netrc-file /home/jenkins/sdnrad.creds"
        # Artifactory rest api:
         url="https://arm.rnd.ki.sw.ericsson.se/artifactory/api/storage"
         url="${url}/proj-erikube-generic-local/erikube/build/gic-build-v4/"
         url="${url}/${ERIKUBE_VERSION}/${ERIKUBE_TAG}/eccd-${ERIKUBE_TAG}-x86_64.tgz"

        eccd_release_tarball_uri=$(curl -s ${creds} ${url} | jq .uri)
        rm -rf tmp_build_decision
        if [ -z ${eccd_release_tarball_uri} ] || \
           [ ${eccd_release_tarball_uri} == "null" ]; then
            echo "ECCD release tarball does not exist in artifactory. Need to build source code"
            echo "trigger"
        else
            echo "ECCD release tarball already exist in artifactory. No need to build again"
            echo "skip"
        fi
       '''.stripIndent()

        String buildDecision = sh(returnStdout: true, script: buildDecisionCmd).trim()

        if (buildDecision =~ '.*trigger.*') {
//            if (env.GERRIT_EVENT_TYPE && env.GERRIT_EVENT_TYPE.contains('change-merged') ||
//                    env.GERRIT_REFSPEC.contains("refs/heads")) {
//                build job: 'mock-eccd-build-scheduler-v4',
//                        parameters: [string(name: 'GERRIT_REFSPEC',value: "${GERRIT_REFSPEC}"),
//                                     string(name: 'RELEASE_LATEST', value: "true")]
//            }
//            else {
//                build job: 'mock-eccd-build-scheduler-v4',
//                        parameters: [string(name: 'GERRIT_REFSPEC',value: "${GERRIT_REFSPEC}"),
//                                     string(name: 'DONOT_BUILD_TAR_BALL', value: 'true')]
//            }
            build job: 'mock-eccd-build-scheduler-v4',
                    parameters: [string(name: 'GERRIT_REFSPEC', value: "${env.GIT_COMMIT}"),
                                 string(name: 'DONOT_BUILD_TAR_BALL', value: 'true')]
        }
    }
    runStage(stageName, stageTimeout, timeoutUnits, stageAction)
}

void generateImageNames(int stageTimeout, String timeoutUnits = 'MINUTES', Map image_types, log) {
    String stageName = "Generate image names"
    def stageAction = {
        //def log = load "cicd/jenkins/job-dsl/groovy/logs.groovy"
        def summary = createSummary(icon: 'package.png', text: "Image names:<br>")
        // Get the list of OpenStack images, and use it as a List
        List os_images = []
//        withCredentials([
//                usernamePassword(credentialsId: "$JENKINS_OS_CREDENTIAL_ID",
//                        passwordVariable: "OS_PASSWORD",
//                        usernameVariable: "OS_USERNAME")]) {
//            String os_cmdline = "openstack image list --public --column Name -f value"
//            String os_output = sh(returnStdout: true, script: os_cmdline)
//            os_images = os_output.readLines()
//        }
        String erikube_tag = "${env.ERIKUBE_TAG}"
        // Write the current erikube tag to the variable files
        sh(script: 'echo "eccd_release_number=${ERIKUBE_TAG}" > "${VARIABLE_FILE}"')
//        summary.appendText("eccd_release_number=${ERIKUBE_TAG}<br>")
//        log.echoWithColor("blue", "eccd_release_number=${ERIKUBE_TAG}")
        // for each image type, create a regex and return the latest matching element
        // in the list of OpenStack images
        image_types.each { String type, Map data ->
            echo("Generating image name for image type ${type}")
//            def image_regex = /.*-${type}-image-${erikube_tag}.*${env.HOST_IMAGE_TYPE}/
//
//            List images_available = os_images.findAll {
//                it =~ image_regex
//            }

//            String safe_refspec = "${env.GERRIT_REFSPEC}".replace("/", "_")
            // Take the last of the images found, if any
//            if (images_available) {
//                data.image_name = images_available.last()
//                echo("Already have an image built for this ${type} image")
//                echo("--> ${data.image_name}")
//                data.available = true
//            } else {
                // If none were found, generate the name
//                if ("${env.GERRIT_REFSPEC}" =~ /.*master.*/) {
//                    // master job image name
//                    data.image_name =
//                            "${type}-image-${erikube_tag}-${env.BUILD_NUMBER}-${env.HOST_IMAGE_TYPE}"
//                } else {
                    // patchset job image name
                    String safe_refspec = "1234567"
                    data.image_name =
                            "${safe_refspec}-${type}-image-${erikube_tag}-${env.BUILD_NUMBER}-${env.HOST_IMAGE_TYPE}"
//                }
                echo("${type} image name: ${data.image_name}")
                data.available = false
//            }

            // Register the name in the environment for later steps
            env["${type.toUpperCase()}_IMAGE_NAME"] = data.image_name
            // Write to file that will be uploaded to artifactory
            sh("echo ${type}_image_name=${data.image_name} >> ${VARIABLE_FILE}")
            log.echoWithColor("blue", "${type}_image_name=${data.image_name}")
            sh("echo log type is : ${log.getClass()}")
            summary.appendText("${type}_image_name=${data.image_name}<br>")
        }
    }
    runStage(stageName, stageTimeout, timeoutUnits, stageAction)
}

void fetchContainerList(int stageTimeout, String timeoutUnits='MINUTES') {

    String stageName = "Fetch container list"
    def stageAction = {
        dir("kube-deployment/ansible/kube") {
            echo 'Fetch container-list.json file'
            sh '''\
                  #!/bin/bash -xe
                  ansible-playbook playbooks/get-container-list.yml
               '''.stripIndent()
        }
    }
    runStage(stageName, stageTimeout, timeoutUnits, stageAction)
}

void buildBaseImageIfNeeded(int stageTimeout, String timeoutUnits='MINUTES') {

    String stageName = "Build base image if needed"
    def stageAction = {
        sh '''
            #!/bin/bash -xe
            echo "packer build image_build.json"
           '''.stripIndent()
    }
    def catchAction = {}
    runStage(stageName, stageTimeout, timeoutUnits, stageAction, catchAction)
}

String buildImage(String image_type, Map image_data, String flavor = "") {
    // If the image already exists, just activate it and return
    if (image_data.available) {
        echo("Image kind: ${image_type} already available.")
        echo("${image_data.image_name}, set to activate state.")
//        withCredentials([
//                usernamePassword(
//                        credentialsId: "$JENKINS_OS_CREDENTIAL_ID",
//                        passwordVariable: "OS_PASSWORD",
//                        usernameVariable: "OS_USERNAME"),
//        ]){
        echo("login with $JENKINS_OS_CREDENTIAL_ID, and proceed active the image:")
        echo("execut cmd: \$ openstack image set ${image_data.image_name} --activate")
//            if (env.OS_AUTH_URL.contains("serodc92ceenbi")) {
                //public_images_project
//                sh("OS_PROJECT_ID=6b5ad64040f9445db677e9f09d480952 openstack image set ${image_data.image_name} --activate")
//            }
//            else {
//                sh("openstack image set ${image_data.image_name} --activate")
//            }
//        }
//        sh("touch ${CICD_DIR}/image_build/vm-image-builder/${image_type}_packer.log}")
        echo("touch ${WORKSPACE}/image_build/vm-image-builder/${image_type}_packer.log}")
        echo("will reaturn: $image_data.image_name")
        return image_data.image_name
    }

    // for some images, an specific flavor might be specified
    // to be set, in case different needs are reequired
    if (flavor.length() > 0){
        env["OS_FLAVOR"] = flavor
    }

    dir("${WORKSPACE}/image_build/vm-image-builder") {
//        withCredentials([
//                usernamePassword(credentialsId: "$JENKINS_OS_CREDENTIAL_ID",
//                        passwordVariable: "OS_PASSWORD",
//                        usernameVariable: "OS_USERNAME"),
//                usernamePassword(credentialsId: "$ARMDOCKER_CREDENTIAL_ID",
//                        passwordVariable: "ARMDOCKER_PASSWORD",
//                        usernameVariable: "ARMDOCKER_USERNAME"),
//                string(credentialsId: '76d8b7a5-3cb6-498b-9369-c78b3bc353f3',
//                        variable: 'SLES_REG_CODE')
//        ]) {

            String container_name = generateContainerName(image_type)

            sh('''
            #!/bin/bash -xe
            #set -euo pipefail
            #IFS=$'nt'

            . ${WORKSPACE}/common/utils/kube-tag.sh

            export IMAGE_TYPE="${image_type}"
            echo "export IMAGE_TYPE="${image_type}""
            export ANSIBLE_GROUPS="${image_type}"
            echo ANSIBLE_GROUPS="${image_type}"
            export PLAYBOOK_FILE="ansible_provisioner/${image_type}-image.yml"
            echo PLAYBOOK_FILE="ansible_provisioner/${image_type}-image.yml"
            export PACKER_LOG_PATH="${image_type}_packer.log"
            echo PACKER_LOG_PATH="${image_type}_packer.log"
            #export GERRIT_TRIGGERS_LIST=\$(cat ${WORKSPACE}/cicd/run-proposal/output.txt | tr "\\n" " ")
            echo "No existing image, need to build new image"
            if [[ "${image_type}" == "director" ]]; then
                echo "Build helm charts first which is needed by ${image_type} image"
                pushd "\${WORKSPACE}/helm-charts"
                make
                popd
            fi
            echo "Build ${image_type} image via packer"
            #if  [[ \${GERRIT_EVENT_TYPE:-} != "change-merged" ]] &&
            #    [[ \${GERRIT_EVENT_COMMENT_TEXT:-} == *"-all-image"* ||
            #       \${GERRIT_TRIGGERS_LIST} == *"check-ibd-all-image"* ]]; then
            #    # Gerrit comment text indicate to use custom base image.
            #    # So use ECCD tag version base image
            #    export OS_SOURCE_IMAGE_NAME="base-image-\${ERIKUBE_TAG}-\${HOST_IMAGE_TYPE}"
            #else
            #    # Use relative base image depends on patchset branch
            #    export GERRIT_BRANCH="\${GERRIT_BRANCH//./_}"
            #    export OS_SOURCE_IMAGE_NAME="SLES_15_SP2_IBD_BASE_IMAGE_\${GERRIT_BRANCH##*/}"
            #fi
            echo "set OS_SOURCE_IMAGE_NAME"
            export OS_SOURCE_IMAGE_NAME="base-image-\\$(ERIKUBE_TAG)-\\$(HOST_IMAGE_TYPE)"
            export OS_TARGET_IMAGE_NAME="$(image_data.image_name)"
            echo "OS_TARGET_IMAGE_NAME=\${OS_TARGET_IMAGE_NAME}" |tee target_image.txt
            export ECCD_RELEASE_NUMBER="\${ERIKUBE_TAG}"
            export CONTAINER_NAME="${container_name}"
            echo "CONTAINER_NAME="${container_name}""
            #echo if [[ "OS_AUTH_URL" = *"serodc92ceenbi"* ]]; then
            #    export SHELL_CMD='/bin/sh -c "packer build image_build.json"'
            #    export IMAGE_VISIBILITY="private"
            #    export USE_BLOCKSTORAGE_VOLUME=true
            #    export BLOCKSTORAGE_VOLUME_SIZE=16
            #    export OS_VOLUME_API_VERSION=3
            #fi
            echo run make print-variables
            echo run make run

            '''.stripIndent())
//        }
//        withCredentials([
//                usernamePassword(credentialsId: "$JENKINS_OS_UPGRADE_CREDENTIAL_ID",
//                        passwordVariable: "OS_PASSWORD",
//                        usernameVariable: "OS_USERNAME"),
//                usernamePassword(credentialsId: "$ARMDOCKER_CREDENTIAL_ID",
//                        passwordVariable: "ARMDOCKER_PASSWORD",
//                        usernameVariable: "ARMDOCKER_USERNAME"),
//                string(credentialsId: '76d8b7a5-3cb6-498b-9369-c78b3bc353f3',
//                        variable: 'SLES_REG_CODE')
//        ]) {
            sh('''
            #!/bin/bash

            echo if "OS_AUTH_URL" = *"serodc92ceenbi"*
                #Image is moved from builder project to public-images-project
                #UUID is needed because there mght be more images with same name in public
                #images project
             echo "Image is moved from builder project to public-images-project"
            '''.stripIndent())
       // }
    }
    return image_data.image_name
}

String generateContainerName(String image_type) {
    return "${image_type}-image-builder-${env.BUILD_NUMBER}-${env.GIT_COMMIT}".toString()
}

return this
