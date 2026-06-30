pipeline {
    agent any

    environment {
        DOCKER_IMAGE = "ayazlogon/network-supplier-api:latest"
        DOCKER_CREDS_ID = "docker-hub-credentials-02"
    }

    stages {

        stage('Checkout Code') {
            steps {
                checkout scm
            }
        }

        stage('Build Docker Image') {
            steps {
                echo "Building Docker Image..."
                sh """
                    docker build -t ${DOCKER_IMAGE} .
                """
            }
        }

        stage('Push Docker Image') {
            steps {
                withCredentials([usernamePassword(
                    credentialsId: "${DOCKER_CREDS_ID}",
                    usernameVariable: 'DOCKER_USER',
                    passwordVariable: 'DOCKER_PASS'
                )]) {

                    sh """
                        echo \$DOCKER_PASS | docker login -u \$DOCKER_USER --password-stdin
                        docker push ${DOCKER_IMAGE}
                        docker logout
                    """
                }
            }
        }

        stage('Deploy') {
            steps {
                echo "Deploying application..."

                sh """
                    cp docker-compose.yml /home/ayaz/network-supplier-api/docker-compose.yml
                    cp .env /home/ayaz/network-supplier-api/.env

                    cd /home/ayaz/network-supplier-api

                    docker compose pull

                    docker compose up -d --force-recreate

                    docker image prune -f
                """
            }
        }
    }

    post {
        success {
            echo "Deployment Successful"
        }

        failure {
            echo "Deployment Failed"
        }
    }
}