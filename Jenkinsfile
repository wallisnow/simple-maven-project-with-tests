node('master') {
    chectout scm
    stages {
        stage('Build') {
            withMaven(maven: 'M3'){
                sh "mvn -Dmaven.test.failure.ignore=true clean package"
            }
        }
        stage('Result'){
            success {
                junit '**/target/surefire-reports/TEST-*.xml'
                archiveArtifacts 'target/*.jar'
            }
        }
    }
}
