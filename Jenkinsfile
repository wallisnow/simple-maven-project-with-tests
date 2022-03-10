import hudson.model.*

//use GIT to mock gerrit
def FAILED_STAGE
def rootDir
def ENV
def log
def BUILD_ENV


Map<String, Map> images = [
        'capo_ephemeral': [:],
        'capo_node'     : [:]
]

Map<String, Map> disks = [
        'ephemeral': null,
        'node'     : null
]

pipeline {
    agent { label "master" }
    //checkout scm
    environment {
        MY_ENV = "TEST ENV"
    }

    stages {
        stage('init') {
            steps {
                script {
                    rootDir = pwd()
                    ENV = "${rootDir}/env.groovy"
                    // ${rootDir} is same as ${WORKSPACE}
                    log = load "${WORKSPACE}/logs.groovy"
                }
                sh 'pwd'
                sh 'ls'
                load "${ENV}"
                load "${K8S_BUILDER_ENV}"
                sh 'echo ${K8S_COMMON_METHODS}'
            }
        }
        stage('Test run script') {
            steps {
                sh('./helloworld.sh')
            }
        }
        stage('Build') {
            steps {
                //sh "mvn -Dmaven.test.failure.ignore=true clean package"
                withMaven(maven: 'M3') {
                    sh "mvn -Dmaven.test.failure.ignore=true clean package"
                }
            }
        }
        stage('Test env') {
            steps {
                script {
                    FAILED_STAGE = env.STAGE_NAME
                    env.MY_NEW_ENV = "foo" // creates env.SOMETHING variable
                    env.MY_ENV = "bar"
                    sh "echo MY_NEW_ENV: ${MY_NEW_ENV}, MY_ENV: ${MY_ENV}"
                    env.MY_NEW_ENV = "foofoofoo"
                    sh "echo MY_NEW_ENV: ${MY_NEW_ENV}, MY_ENV: ${MY_ENV}"
                }

                withEnv(["MY_ENV=barrr"]) { // it can override any env variable
                    echo "MY_ENV = ${env.MY_ENV}"
                }

                sh 'echo ${MY_ENV}'
                sh "printenv"
                sh 'echo "Hello World 1"'
                sh '''
                    echo "Multiline shell steps works too "
                    ls -lah
                '''
            }
        }
        stage("run robot ") {
            steps {
                script {
                    env.TEST_FILE = "file.txt"
//                    sh '''
//                        #!/bin/bash -xe
//                        robot --outputdir robot/reports robot/mytest.robot
//                    '''.stripIndent()
                    sh '''
                      rm -rf ${TEST_FILE}
                      echo "MY_TEST_BADGE" >> ${TEST_FILE}
                      cat ${TEST_FILE}
                      '''.stripIndent()

                }
                script {
                    duration = sh(script: "cat ${WORKSPACE}/${TEST_FILE}", returnStdout: true).trim()
                    echo "return duration :${duration}"
                    manager.addShortText(duration, "black", "lightgreen", "0px", "white")

                    try {
                        exitValue = sh(script: "cat ${WORKSPACE}/not_exists.txt", returnStdout: true)
                        echo "return exitValue :${exitValue}"
                    } catch (err) {
                        echo "not_exists.txt file does not exists! "
                        //throw err
                    }

                    //test if file exists
                    String unexist_file_path = "${WORKSPACE}/${TEST_FILE}"
                    if (fileExists(unexist_file_path)) {
                        echo "${unexist_file_path} file -> Yes"
                    } else {
                        echo "${unexist_file_path} file -> No"
                    }
                }
            }
        }
        stage('test mock build image') {
            steps {
                script {
                    commonK8sMethod = load "${K8S_COMMON_METHODS}"
                    commonK8sMethod.test()
                    commonK8sMethod.generateImageNames(1, 'MINUTES', images, log)
                    commonK8sMethod.buildSourceCode(3, 'HOURS')
                    commonK8sMethod.fetchContainerList(10, 'MINUTES')
                    commonK8sMethod.buildBaseImageIfNeeded(40, 'MINUTES')

                    capo = load "${CAPO_COMMON_METHODS}"
                    capo.buildValuePackage(30, 'MINUTES')

                    parallel(
                            'node': {
                                script {
                                    env.ENV_IN_PARALLEL = "parallel_env"
                                    capo.buildCapoNodeImage(35, 'MINUTES', images, "${K8S_COMMON_METHODS}")
                                    // If we are this far, try to remove potential volumes:
                                    env.CAPO_VOLUME_IN_OS = "true"
                                    disks.node = capo.attachImage(30, 'MINUTES', env.BM_NODE_IMAGE)
                                    disks.node.each { key, val ->
                                        echo "Map of disks, disks Key : $key = $val"
                                    }
                                    capo.convertImage(30, 'MINUTES', "${ROOT_ISO9660_DIR}/node-images/", disks.node.disk_path, "node.img")
                                }
                            }
                    )

                    env.TEST_ENV_IN_PARALLEL = ${ENV_IN_PARALLEL}
                    echo "test set value after parallel: ${TEST_ENV_IN_PARALLEL}"
                }
            }
        }
        stage('Result') {
            steps {
                script {
                    FAILED_STAGE = env.STAGE_NAME
                }
                junit '**/target/surefire-reports/TEST-*.xml'
                archiveArtifacts 'target/*.jar'
            }
        }
//        stage('Robot Result') {
//            steps {
//                script {
//                    step(
//                            [$class           : 'RobotPublisher',
//                             outputPath       : 'robot/reports',
//                             outputFileName   : 'robot/reports/output.xml',
//                             reportFileName   : 'robot/reports/report.html',
//                             logFileName      : 'robot/reports/log.html',
//                             passThreshold    : 100,
//                             unstableThreshold: 0,
//                             onlyCritical     : true,
//                             otherFiles       : "*.log"]
//                    )
//                }
//            }
//        }
    }
    post {
        always {
            script {
                echo "Failed stage name: ${FAILED_STAGE}"
            }
        }
    }
}