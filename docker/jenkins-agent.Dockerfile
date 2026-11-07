FROM jenkins/inbound-agent:alpine-jdk21
COPY --from=ghcr.io/astral-sh/uv:0.13.5 /uv /usr/local/bin/uv
USER root
COPY docker/jenkins-agent-entrypoint.sh /opt/jenkins-agent-entrypoint
RUN chmod 0755 /opt/jenkins-agent-entrypoint && apk add --no-cache bash python3 curl docker-cli docker-cli-compose && \
    mkdir -p /workspace /workspace@tmp && chown jenkins:jenkins /workspace /workspace@tmp
USER jenkins
