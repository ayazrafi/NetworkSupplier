pipeline {
    agent any

    environment {
        // FIXME: Replace 'your-dockerhub-username' with your actual Docker Hub username
        DOCKER_IMAGE = "ayazlogon/network-supplier-api:latest"
        
        // FIXME: Replace with your actual Ubuntu Production Server IP address
        PROD_SERVER_IP = "13.234.134.227"
        SSH_USER = "root" // Change this to your production server SSH username (e.g., ubuntu, root, admin)
        
        // Jenkins Credentials IDs (Must match the IDs you created in Jenkins Dashboard)
        DOCKER_CREDS_ID = "docker-hub-credentials"
        SSH_CREDS_ID = "ubuntu-server-ssh-key"
    }

    stages {
        stage('Checkout Code') {
            steps {
                // Pulls latest changes from your Git repository (GitHub/GitLab)
                checkout scm
            }
        }

        stage('Build Docker Image') {
            steps {
                echo "Building Docker image: ${DOCKER_IMAGE}..."
                sh "docker build -t ${DOCKER_IMAGE} ."
            }
        }

        stage('Push to Docker Hub') {
            steps {
                echo 'Pushing built image to Docker Hub...'
                withCredentials([usernamePassword(credentialsId: "${DOCKER_CREDS_ID}", usernameVariable: 'USER', passwordVariable: 'PASS')]) {
                    sh "echo ${PASS} | docker login -u ${USER} --password-stdin"
                    sh "docker push ${DOCKER_IMAGE}"
                }
            }
        }

        stage('Deploy to Production Server') {
            steps {
                echo "Deploying to remote Ubuntu Server (${PROD_SERVER_IP})..."
                sshagent(["${SSH_CREDS_ID}"]) {
                    // Connects to your production server via SSH, pulls the new image, and restarts the container
                    sh """
                        ssh -o StrictHostKeyChecking=no ${SSH_USER}@${PROD_SERVER_IP} '
                            cd ~/network-supplier-api &&
                            docker-compose pull &&
                            docker-compose up -d --force-recreate
                        '
                    """
                }
            }
        }

        stage('Post-Build Cleanup') {
            steps {
                echo 'Cleaning up unused Docker images on the Jenkins build server...'
                sh 'docker image prune -f'
            }
        }
    }

    post {
        success {
            echo 'Pipeline completed and deployment was successful!'
        }
        failure {
            echo 'Pipeline failed. Check build logs for details.'
        }
    }
}
