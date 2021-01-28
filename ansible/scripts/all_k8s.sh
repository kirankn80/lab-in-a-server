#!/bin/bash -ex

echo "Configure contrail deployment for Kubernetes"
cd /root/contrail-ansible-deployer
echo $PWD
ansible --version
env
yum install -y python-requests
ansible-playbook -i inventory/ -e orchestrator=kubernetes playbooks/configure_instances.yml

echo "Install Kubernetes"
cd /root/contrail-ansible-deployer
echo $PWD
ansible --version
env
yum install -y python-requests
ansible-playbook -i inventory/ -e orchestrator=kubernetes playbooks/install_k8s.yml

echo "Installing Flannel and multus CNI"
kubectl apply -f https://raw.githubusercontent.com/coreos/flannel/master/Documentation/kube-flannel.yml
git clone https://github.com/intel/multus-cni.git && cd multus-cni
cat ./images/multus-daemonset.yml | kubectl apply -f -
cd
