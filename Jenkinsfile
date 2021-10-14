def FAILED_STAGE

pipeline {
    agent {label "master"}
    stages {
        checkout scm
        stage('Build maven') {
            FAILED_STAGE = env.STAGE_NAME
            steps(
                    withMaven(maven: 'M3') {
                        sh "mvn -Dmaven.test.failure.ignore=true clean package"
                    }
            )

        }
        stage('Collect test info') {
            steps{
                echo currentBuild.result
                //FAILED_STAGE = env.STAGE_NAME
            }
        }
        stage('Result') {
            steps{
                junit '**/target/surefire-reports/TEST-*.xml'
                archiveArtifacts 'target/*.jar'
            }
        }
    }


    post {
        always {
            steps{
                echo "Failed stage name: ${FAILED_STAGE}"
            }
        }
    }
}


