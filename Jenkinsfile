pipeline {
    agent { label "master" }
    //checkout scm
    stages {
        stage('Build') {
            steps {
                sh 'echo "Hello World"'
                sh '''
                    echo "Multiline shell steps works too"
                    ls -lah
                '''
                //sh "mvn -Dmaven.test.failure.ignore=true clean package"
                withMaven(maven: 'M3'){
                    sh "mvn -Dmaven.test.failure.ignore=true clean package"
                }
            }
        }
        stage('Result') {
            steps {
                junit '**/target/surefire-reports/TEST-*.xml'
                archiveArtifacts 'target/*.jar'
            }
        }
    }
}