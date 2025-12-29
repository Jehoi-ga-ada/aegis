pipeline {
    agent any

    environment {
        DOCKER_HOST = 'tcp://docker:2376'
        DOCKER_TLS_VERIFY = '1'
        DOCKER_CERT_PATH = '/certs/client'
    }

    stages {
        stage('Cleanup Environment') {
            steps {
                sh 'docker compose -f docker-compose.app.yaml down --remove-orphans'
            }
        }

        stage('Build Aegis') {
            steps {
                echo 'Building images inside the DinD Sandbox...'
                sh 'docker compose -f docker-compose.app.yaml build'
            }
        }

        stage('Logic Tests') {
            steps {
                echo 'Running Pytest for Trading Logic...'
                sh 'docker compose -f docker-compose.app.yaml run -T --rm worker uv run pytest tests/test_logic.py'
            }
        }

        stage('Integration Up') {
            steps {
                echo 'Spinning up full Aegis stack...'
                sh 'docker compose -f docker-compose.app.yaml up -d'
                
                sh 'sleep 5' 
            }
        }

        stage('Stress Test') {
            steps {
                echo 'Starting Locust Load Test (1 Minute)...'
                sh 'docker compose -f docker-compose.app.yaml run --rm locust'
            }
        }

        stage('Production Handover') {
            when { 
                anyOf {
                    branch 'main'
                    expression { env.BRANCH_NAME == 'origin/main' }
                }
            }
            steps {
                echo 'Handoff: Starting long-running service on Host...'
                sh 'docker compose -f docker-compose.app.yaml up -d --no-recreate'
            }
        }
    }

    post {
        always {
            sh 'docker compose -f docker-compose.app.yaml rm -f locust'
        }
        failure {
            echo 'Build failed. Tearing down broken environment...'
            sh 'docker compose -f docker-compose.app.yaml down'
        }
        success {
            script {
                if (env.BRANCH_NAME != 'main') {
                    echo 'Feature test successful. Cleaning up...'
                    sh 'docker compose -f docker-compose.app.yaml down'
                } else {
                    echo 'Production deployment successful. Services is live.'
                }
            }
        }
    }
}