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
    }

    post {
        always {
            echo 'Final Cleanup: Tearing down the workshop...'
            sh 'docker compose -f docker-compose.app.yaml down'
        }
        success {
            echo 'Aegis is stable. Logic and integration checks passed!'
        }
        failure {
            echo 'Build failed. Check the logs for logic errors.'
        }
    }
}