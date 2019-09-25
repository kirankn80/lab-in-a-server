#!/bin/bash -ex
echo "Configure contrail deployment"
cd /root/contrail-ansible-deployer
echo $PWD
ansible --version
env
ansible-playbook -i inventory/ -e orchestrator=openstack playbooks/configure_instances.yml

echo "Install Openstack"
cd /root/contrail-ansible-deployer
echo $PWD
ansible --version
env
ansible-playbook -i inventory/ playbooks/install_openstack.yml

echo "Install contrail"
cd /root/contrail-ansible-deployer
echo $PWD
ansible --version
env
ansible-playbook -i inventory/ -e orchestrator=openstack playbooks/install_contrail.yml

