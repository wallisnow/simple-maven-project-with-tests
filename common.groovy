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

void generateImageNames(int stageTimeout, String timeoutUnits = 'MINUTES', Map image_types) {
    String stageName = "Generate image names"
    def stageAction = {
        //def log = load "cicd/jenkins/job-dsl/groovy/logs.groovy"
        //def summary = createSummary(icon: 'package.png', text: "Image names:<br>")
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
            summary.appendText("${type}_image_name=${data.image_name}<br>")
        }
    }
    runStage(stageName, stageTimeout, timeoutUnits, stageAction)
}

return this
