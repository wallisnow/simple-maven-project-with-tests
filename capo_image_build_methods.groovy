import java.util.regex.*

def runStage(
        String stageName, int stageTimeout, String timeoutUnits, Closure stageAction,
        Closure catchAction = {}, String buildResult = 'FAILURE', Closure finalAction = {}) {
    def log = load "${WORKSPACE}/logs.groovy"
    wrap([$class: 'AnsiColorBuildWrapper', 'colorMapName': 'xterm']) {
        removeBadges()
        addInfoBadge("INFO")
        addShortText(text: stageName, color: "black", background: "white", border: 0)
        log.echoWithColor("blue", "${stageName}")
        timeout(time: stageTimeout, unit: timeoutUnits) {
            try {
                stageAction()
            } catch (Exception e) {
                removeBadges()
                log.addError("${stageName}")
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

void buildValuePackage(int stageTimeout, String timeoutUnits = 'MINUTES') {
    String stageName = "Build Value Package"
    def stageAction = {
        dir(env.CAPO_CONTAINER_LIST_WORKDIR) {
            // Build them with python script
            // The script saves a JSON list to BM_VALUEPACK_JSON
            sh '''#!/bin/bash -xe
                echo "${WORKSPACE}/builder/value_packs.py  build  --container-list container-list.json  >> ${CAPO_VALUEPACK_JSON}"
                echo ["CXP9039695-2.22.0-945602b19d3967ad2ce3c8f78b87ccbe.tar.gz", "CXP9039691-2.22.0-f925aff19cbeeecc00926535e1ec3ad8.tar.gz", "CXP9042262-2.22.0-c3f5ac47956afba884095fea78b743d3.tar.gz", "CXP9042308-2.22.0-f3937ab21b3b6d0763bb8ba5fa261234.tar.gz"] >> ${CAPO_VALUEPACK_JSON}
                echo "create draino_v1.0.tar.gz"
                touch draino_v1.0.tar.gz
                for i in *.gz; do
                    [ -f "$i" ] || break
                    echo "upload /capo/valuepacks/${ERIKUBE_TAG%%-*} $i"
                done
                '''.stripIndent()
            ccd_rel_version = env.ERIKUBE_TAG.split("-")[0]
            env.VALUEPACKS_URL = "${env.ARTIFACTORY_BASE_PATH}/capo/valuepacks/${ccd_rel_version}"
            def valuePacksJson = readFile("${env.CAPO_VALUEPACK_JSON}")
            def summary = createSummary(icon: 'package.png', text: "Value packs:<br>")
            summary.appendText(valuePacksJson)
        }
    }
    runStage(stageName, stageTimeout, timeoutUnits, stageAction)
}

void buildCapoNodeImage(
        int stageTimeout, String timeoutUnits = 'MINUTES', Map image_types, String buildMethods
) {
    run = load buildMethods
    String stageName = "Build capo node image"
    def stageAction = {
        image_types.each { key, val ->
            echo "Map of image, Image Key : $key = Image Value: $val"
        }
        env.BM_NODE_IMAGE = run.buildImage("capo_node", image_types.capo_node)
    }
    runStage(stageName, stageTimeout, timeoutUnits, stageAction)
}

Map attachImage(int stageTimeout, String timeoutUnits = 'MINUTES', String image) {
    String stageName = "Attach image: ${image}"
    Map device_paths
    def stageAction = {
        //String executor_id = sh(script: "cat /var/lib/cloud/data/instance-id", returnStdout: true).trim()
        String executor_id = "9527"
        String volume_name = "${image}_${BUILD_TAG}"
        echo "Attaching ${image} to VM ${executor_id}"
//        withCredentials([
//                usernamePassword(credentialsId: "$JENKINS_OS_CREDENTIAL_ID",
//                        passwordVariable: "OS_PASSWORD",
//                        usernameVariable: "OS_USERNAME")]
//        ){
        String os_cmdline = "echo openstack volume create --size 15 --image ${image} ${volume_name} -f json"
        def ret_createVol = sh(script: os_cmdline, returnStdout: true)
        //Map volume_info = readJSON(text: ret_createVol)
        Map volume_info = readJSON(text: '{ "id": "vol_id_99999999999999999999999999999999" }')
        //Volume creation takes some time, retry until it works
        retry(10) {
            //sh("openstack server add volume ${executor_id} ${volume_info.id}")
            sh("echo do openstack server add volume ${executor_id} ${volume_info.id}")
        }
        device_paths = calculateDeviceID(volume_info.id, 3)
//        }
    }
    runStage(stageName, stageTimeout, timeoutUnits, stageAction)
    return device_paths
}

/*
 To have several jobs running on the same executor, predictable disk names are used.
 OpenStack sets the SCSI ID of LUNs in a predictable way.
 Example:
 Volume id: 94685948-7e66-4558-92ac-21b804a3a330
 Device file: /dev/disk/by-id/scsi-0QEMU_QEMU_HARDDISK_94685948-7e66-4558-9
 */
Map calculateDeviceID(String volume_id, int partition){
    String short_id = volume_id.substring(0,20)
    String part_path = "/dev/disk/by-id/scsi-0QEMU_QEMU_HARDDISK_${short_id}-part${partition}"
    String disk_path = "/dev/disk/by-id/scsi-0QEMU_QEMU_HARDDISK_${short_id}"
    return [disk_path: disk_path, part_path: part_path, volume_id: volume_id]
}

return this
