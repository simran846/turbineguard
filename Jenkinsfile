pipeline {
    agent any

    environment {
        PYTHONUNBUFFERED = '1'
        REPORTS_DIR = 'reports'
    }

    stages {
        stage('Checkout') {
            steps {
                echo 'Checking out source repository...'
                checkout scm
            }
        }

        stage('Install Dependencies') {
            steps {
                echo 'Installing Python virtualenv and dependencies...'
                sh '''
                    python3 -m venv venv
                    . venv/bin/activate
                    pip install --upgrade pip
                    pip install -r requirements.txt
                    pip install -e .
                '''
            }
        }

        stage('Lint & Static Analysis') {
            steps {
                echo 'Running Ruff static code analysis...'
                sh '''
                    . venv/bin/activate
                    ruff check src tests
                '''
            }
        }

        stage('Unit Testing') {
            steps {
                echo 'Executing Unit Test Suite...'
                sh '''
                    . venv/bin/activate
                    pytest -m unit --junitxml=reports/unit_tests.xml
                '''
            }
        }

        stage('Integration Testing') {
            steps {
                echo 'Executing Integration Test Suite...'
                sh '''
                    . venv/bin/activate
                    pytest -m integration --junitxml=reports/integration_tests.xml
                '''
            }
        }

        stage('Safety & Validation Suite') {
            steps {
                echo 'Executing Safety Limits & Formal Validation Suite...'
                sh '''
                    . venv/bin/activate
                    pytest -m "validation or safety" --junitxml=reports/validation_tests.xml
                '''
            }
        }

        stage('Generate Engineering Reports') {
            steps {
                echo 'Generating HTML, PDF, CSV, and JSON validation reports...'
                sh '''
                    . venv/bin/activate
                    python scripts/run_validation_suite.py
                '''
            }
        }

        stage('Build Docker Image') {
            steps {
                echo 'Building production Docker container...'
                sh 'docker build -t turbineguard:latest .'
            }
        }
    }

    post {
        always {
            echo 'Archiving test reports and telemetry plots...'
            junit 'reports/*.xml'
            archiveArtifacts artifacts: 'reports/**', allowEmptyArchive: true
        }
        success {
            echo 'TurbineGuard validation pipeline completed with 100% success!'
        }
        failure {
            echo 'Pipeline failed! Check test logs and requirement diagnostics.'
        }
    }
}
