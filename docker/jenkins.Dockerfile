FROM jenkins/jenkins:2.580.2-jdk21
USER root
RUN jenkins-plugin-cli --plugins workflow-aggregator configuration-as-code timestamper
COPY docker/jenkins-init.groovy /usr/share/jenkins/ref/init.groovy.d/10-releaseops.groovy
COPY docker/casc.yaml /usr/local/share/jenkins/casc.yaml
USER jenkins
