def FAILED_STAGE

pipeline {
    agent { label "master" }
    options {
        timestamps()
        buildDiscarder(logRotator(numToKeepStr: '100'))
        timeout(time: 25, unit: 'HOURS')
    }
    stages {
        checkout scm
        stage('Build maven') {
            steps(
                    //FAILED_STAGE = env.STAGE_NAME
                    withMaven(maven: 'M3') {
                        sh "mvn -Dmaven.test.failure.ignore=true clean package"
                    }
            )

        }
        stage('Collect test info') {
            steps {
                script {
                    echo currentBuild.result
                }
                //FAILED_STAGE = env.STAGE_NAME
            }
        }
        stage('Result') {
            steps {
                junit '**/target/surefire-reports/TEST-*.xml'
                archiveArtifacts 'target/*.jar'
            }
        }
    }


    post {
        always {
            steps {
                script { echo "Failed stage name: ${FAILED_STAGE}" }
            }
        }
    }
}


