node('master') {
    checkout scm
    stage('Build') {
        withMaven(maven: 'M3') {
            sh "mvn -Dmaven.test.failure.ignore=true clean package"
        }
    }
    stage('Result') {

        junit '**/target/surefire-reports/TEST-*.xml'
        archiveArtifacts 'target/*.jar'
    }
}
