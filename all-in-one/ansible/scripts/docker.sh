#!/bin/bash -ex
yum install -y yum-utils device-mapper-persistent-data lvm2
yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
yum install -y docker-ce
systemctl enable docker
systemctl start docker
echo '{"insecure-registries": ["nodei40.englab.juniper.net:5000", "nodei40.englab.juniper.net:5010"]}' >> /etc/docker/daemon.json
systemctl restart docker
