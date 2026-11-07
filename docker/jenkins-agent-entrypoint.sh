#!/bin/sh
set -eu
while [ ! -s /run/jenkins-agent/secret ]; do sleep 1; done
export JENKINS_SECRET="$(cat /run/jenkins-agent/secret)"
exec /usr/local/bin/jenkins-agent "$@"
