#!/bin/bash -ex
systemctl disable firewalld
systemctl stop firewalld
HUB="hub.juniper.net/contrail-nightly"
if [[ "$CCD_IMAGE" = *"$HUB"* ]]; then
  docker login hub.juniper.net --username "JNPR-CSRXFieldUser12" --password "d2VbRJ8xPhSUAwzo7Lym"
fi
docker run -t --net host -e orchestrator=openstack -e action=import_cluster -v $COMMAND_SERVERS_FILE:/command_servers.yml -v $INSTANCES_FILE:/instances.yml -d --privileged --name contrail_command_deployer $CCD_IMAGE
docker logs -f contrail_command_deployer
