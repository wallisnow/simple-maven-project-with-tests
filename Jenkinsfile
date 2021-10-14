def FAILED_STAGE

node('master') {
    stages {
        checkout scm
        stage('Build maven') {
            //FAILED_STAGE = env.STAGE_NAME
            withMaven(maven: 'M3') {
                sh "mvn -Dmaven.test.failure.ignore=true clean package"
            }
        }
        stage('Collect test info') {
            echo currentBuild.result
            //FAILED_STAGE = env.STAGE_NAME
        }
        stage('Result') {
            junit '**/target/surefire-reports/TEST-*.xml'
            archiveArtifacts 'target/*.jar'
        }
    }


    post {
        always {
            echo "Failed stage name: "
        }
    }
}


