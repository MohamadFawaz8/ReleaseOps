import jenkins.model.Jenkins
import java.nio.file.Files
import java.nio.file.StandardCopyOption

def j = Jenkins.get()
j.setNumExecutors(0)
j.setQuietPeriod(1)
def job = j.getItem('releaseops-ci')
if (job == null) {
  job = j.createProject(org.jenkinsci.plugins.workflow.job.WorkflowJob, 'releaseops-ci')
}
job.setDefinition(new org.jenkinsci.plugins.workflow.cps.CpsFlowDefinition(new File('/workspace/Jenkinsfile').text, true))
job.addProperty(new hudson.model.ParametersDefinitionProperty(
  new hudson.model.BooleanParameterDefinition('DEPLOY_PREVIEW', false, 'Deploy a checked revision to the local preview')
))
job.setDescription('Local ReleaseOps CI pipeline. Trigger manually from Jenkins after updating the mounted source workspace.')
job.save()
j.save()
Thread.start {
  while (true) {
    try {
      def secret = j.getComputer('releaseops-agent')?.getJnlpMac()
      if (secret) {
        def destination = new File('/run/jenkins-agent/secret')
        def temporary = new File('/run/jenkins-agent/secret.new')
        temporary.text = secret
        temporary.setReadable(false, false)
        temporary.setWritable(false, false)
        temporary.setReadable(true, true)
        temporary.setWritable(true, true)
        Files.move(temporary.toPath(), destination.toPath(), StandardCopyOption.REPLACE_EXISTING, StandardCopyOption.ATOMIC_MOVE)
        break
      }
    } catch (Throwable ignored) {}
    sleep(1000)
  }
}
