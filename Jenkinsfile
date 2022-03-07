import hudson.model.*

def FAILED_STAGE
def ENV = "env.groovy"

pipeline {
    agent { label "master" }
    //checkout scm
    environment {
        MY_ENV = "TEST ENV"
    }

    stages {
        stage('init'){
            steps{
                sh 'load env'
                load "${ENV}"
                sh 'echo ${COMMON_METHODS}'
            }
        }
        stage('Build') {
            steps {

                script {
                    FAILED_STAGE = env.STAGE_NAME
                }
                sh 'echo ${MY_ENV}'
                sh "printenv"
                sh 'echo "Hello World 1"'
                sh '''
                    echo "Multiline shell steps works too "
                    ls -lah
                '''
                //sh "mvn -Dmaven.test.failure.ignore=true clean package"
                withMaven(maven: 'M3') {
                    sh "mvn -Dmaven.test.failure.ignore=true clean package"
                }
            }
        }
        stage('set new env') {
            steps {
                script {
                    env.MY_NEW_ENV = "foo" // creates env.SOMETHING variable
                    env.MY_ENV = "bar"
                    sh "echo MY_NEW_ENV: ${MY_NEW_ENV}, MY_ENV: ${MY_ENV}"
                    env.MY_NEW_ENV = "foofoofoo"
                    sh "echo MY_NEW_ENV: ${MY_NEW_ENV}, MY_ENV: ${MY_ENV}"
                }

                withEnv(["MY_ENV=bar"]) { // it can override any env variable
                    echo "MY_ENV = ${env.MY_ENV}"
                }

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
                      echo "AAAAAAA" >> ${TEST_FILE}
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
        stage('load script'){
            commonMethod = load "${COMMON_METHODS}"
            commonMethod.test()
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