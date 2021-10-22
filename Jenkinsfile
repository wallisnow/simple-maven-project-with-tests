def FAILED_STAGE

pipeline {
    agent { label "master" }
    //checkout scm
    environment {
        MY_ENV = "TEST ENV"
    }

    stages {
        stage('Build') {
            steps {
                script {
                    FAILED_STAGE = env.STAGE_NAME
                }
                sh 'echo ${MY_ENV}'
                sh "printenv"
                sh 'echo "Hello World 1"'
                sh '''
                    echo "Multiline shell steps works too"
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
                    sh '''
                        ls
                        /bin/sh robot robot/mytest.robot
                    '''
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
        stage('Robot Result') {
            steps {
                script {
                    step(
                            [$class           : 'RobotPublisher',
                             outputPath       : 'robot',
                             outputFileName   : '**/output.xml',
                             reportFileName   : '**/report.html',
                             logFileName      : '**/log.html',
                             passThreshold    : 100,
                             unstableThreshold: 0,
                             onlyCritical     : true,
                             otherFiles       : "*.log"]
                    )
                }
            }
        }
    }
    post {
        always {
            script {
                echo "Failed stage name: ${FAILED_STAGE}"
            }
        }
    }
}