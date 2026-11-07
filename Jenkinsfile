pipeline {
  agent { label 'releaseops-linux' }
  environment {
    UV_PROJECT_ENVIRONMENT = '/home/jenkins/venvs/releaseops'
  }
  options {
    timestamps()
    timeout(time: 25, unit: 'MINUTES')
    disableConcurrentBuilds()
  }
  parameters {
    booleanParam(name: 'DEPLOY_PREVIEW', defaultValue: false, description: 'Deploy this revision to the persistent local preview at 127.0.0.1:8083 after all checks pass.')
  }
  stages {
    stage('Checks') {
      steps {
        dir('/workspace') {
          sh 'bash scripts/check.sh'
        }
      }
    }
    stage('Build images') {
      steps {
        dir('/workspace') {
          sh 'bash scripts/build.sh'
        }
      }
    }
    stage('Scan runtime images') {
      steps {
        dir('/workspace') {
          sh 'bash scripts/scan-images.sh'
        }
      }
    }
    stage('Disposable Compose integration') {
      steps {
        dir('/workspace') {
          sh 'CI_RUN_ID="jenkins-${BUILD_NUMBER}" bash scripts/compose-smoke.sh'
        }
      }
    }
    stage('Deploy local preview') {
      when { expression { params.DEPLOY_PREVIEW } }
      steps {
        dir('/workspace') {
          sh 'bash scripts/release-preview.sh'
        }
      }
    }
    stage('Post-deploy smoke') {
      when { expression { params.DEPLOY_PREVIEW } }
      steps {
        dir('/workspace') {
          sh 'bash scripts/postdeploy-smoke.sh'
        }
      }
    }
  }
  post {
    always {
      echo 'Review stage logs above. Disposable Compose resources are removed by the integration script.'
    }
  }
}
