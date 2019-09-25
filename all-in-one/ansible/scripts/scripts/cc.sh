#!/bin/bash -ex
systemctl disable firewalld
systemctl stop firewalld
docker run -t --net host -e orchestrator=openstack -e action=import_cluster -v $COMMAND_SERVERS_FILE:/command_servers.yml -v $INSTANCES_FILE:/instances.yml -d --privileged --name contrail_command_deployer $CCD_IMAGE
docker logs -f contrail_command_deployer
