node('master') {
    checkout scm
    stage('Build maven') {
        withMaven(maven: 'M3') {
            sh "mvn -Dmaven.test.failure.ignore=true clean package"
        }
    }
    stage('Collect test info'){
        echo currentBuild.result
    }
    stage('Result') {
        junit '**/target/surefire-reports/TEST-*.xml'
        archiveArtifacts 'target/*.jar'
    }
}
