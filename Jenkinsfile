def FAILED_STAGE

pipeline {
    agent { label "master" }
    //checkout scm
    environment{
        MY_ENV="TEST"
    }

    stages {
        stage('Build') {
            steps {
                script {
                    FAILED_STAGE = env.STAGE_NAME
                }
                sh 'echo ${MY_ENV}'
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
        stage('Result') {
            steps {
                script {
                    FAILED_STAGE = env.STAGE_NAME
                }
                junit '**/target/surefire-reports/TEST-*.xml'
                archiveArtifacts 'target/*.jar'
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