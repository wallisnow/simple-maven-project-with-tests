import java.util.regex.*
import groovy.json.JsonOutput

def runStage(
    String stageName, int stageTimeout, String timeoutUnits, Closure stageAction,
    Closure catchAction={}, String buildResult='FAILURE', Closure finalAction={})
{
    def log = load "${WORKSPACE}/logs.groovy"
    wrap([$class: 'AnsiColorBuildWrapper', 'colorMapName': 'xterm']) {
        removeBadges()
        addInfoBadge("INFO")
        addShortText(text: stageName, color: "black", background: "white", border: 0)
        log.echoWithColor("blue", "${stageName}")
        timeout(time: stageTimeout, unit: timeoutUnits) {
            try {
                stageAction()
            } catch(Exception e) {
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

void buildValuePackage(int stageTimeout, String timeoutUnits='MINUTES')
{
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

return this
