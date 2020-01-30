#!/bin/bash -ex
`pip uninstall -y docker` || true 
`pip uninstall -y docker-py` || true
yum install -y yum-utils device-mapper-persistent-data lvm2
yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
yum install -y docker-ce-18.03.1.ce
#yum install -y docker-ce
systemctl enable docker
systemctl start docker
echo '{"insecure-registries": ["nodei40.englab.juniper.net:5000", "nodei40.englab.juniper.net:5010", "ci-repo.englab.juniper.net:5010", "svl-artifactory.juniper.net", "bng-artifactory.juniper.net"]}' >> /etc/docker/daemon.json
systemctl restart docker

