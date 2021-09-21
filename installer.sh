#!/bin/bash -v

export LC_ALL=C

VAGRANT_VM="`dirname \"$0\"`"              
VAGRANT_VM="`( cd \"$VAGRANT_VM\" && pwd )`"  
if [ -z "$VAGRANT_VM" ] ; then
  exit 1  
fi
echo "$VAGRANT_VM"

apt-get install -y gnupg2
apt-get update
apt-get install -y wget git bridge-utils python3 python3-pip tmux apt-transport-https software-properties-common

# VirtualBox Installation
# Add following line in "/etc/apt/sources.list"
dpkg -s virtualbox-6.1 &> /dev/null
if [ `which virtualbox | wc -l` -eq  "0" ] || ([ $? -ne 0 ] && [ `vboxmanage list runningvms | wc -l` -eq "0" ]); then
wget -q https://www.virtualbox.org/download/oracle_vbox_2016.asc -O- | sudo apt-key add -
wget -q https://www.virtualbox.org/download/oracle_vbox.asc -O- | sudo apt-key add -
sudo add-apt-repository "deb http://download.virtualbox.org/virtualbox/debian `lsb_release -cs` contrib"
sudo apt-get update
sudo apt-get -y install virtualbox-6.1
fi

### Vagrant install
Version="`vagrant --version`"
if [ `which vagrant | wc -l` -eq  "0" ] || ([ "$Version" != *"2.2.7"* ] && [ `vboxmanage list runningvms | wc -l` -eq "0" ]); then
wget https://releases.hashicorp.com/vagrant/2.2.7/vagrant_2.2.7_x86_64.deb
dpkg -i vagrant_2.2.7_x86_64.deb
fi

## Ansible Install
sudo apt-get update
sudo apt-add-repository -y ppa:ansible/ansible
sudo apt-get update
pip install --upgrade pip
pip install ansible==2.8.6
ansible-galaxy install Juniper.junos

## Install JunOS Ansible Module and Python Modules
sudo ansible-galaxy install Juniper.junos

pip install --upgrade pip
sudo apt-get update
pip install jxmlease future==0.18.2
pip install --ignore-installed junos-eznc


## vQFX Box Addition

cd /var/tmp
if [ `vagrant box list | grep juniper/vqfx10k-pfe | wc -l` -eq "0" ]; then
wget http://10.204.217.158/images/kirankn/vqfx10k-pfe-virtualbox.box
vagrant box add --name juniper/vqfx10k-pfe /var/tmp/vqfx10k-pfe-virtualbox.box
fi

if [ `vagrant box list | grep juniper/vqfx10k-re | wc -l` -eq "0" ]; then
wget http://10.204.217.158/images/kirankn/vqfx-re-virtualbox.box
vagrant box add --name juniper/vqfx10k-re /var/tmp/vqfx-re-virtualbox.box
fi

# Download and Addd CentOS-7.5 Box
if [ `vagrant box list | grep kirankn/centOS-7.5 | wc -l` -eq "0" ]; then
wget http://10.204.217.158/images/kirankn/centos-7.5-virtualbox.box
vagrant box add --name kirankn/centOS-7.5 /var/tmp/centos-7.5-virtualbox.box
fi

if [ `vagrant box list | grep kirankn/centOS-7.7 | wc -l` -eq "0" ]; then
wget http://10.204.217.158/images/kirankn/centos-7.7-virtualbox.box
vagrant box add --name kirankn/centOS-7.7 /var/tmp/centos-7.7-virtualbox.box
fi

echo "List Box"
vagrant box list

sudo apt-get install -y python3-pip
pip3 install -U requests colorama schema pyyaml argparse prettytable pTable
pip install jxmlease
pip install --ignore-installed junos-eznc
pip install requests==2.18.4

MACHINE_DIR="`(cd ~ && pwd)`"
if [ -z "$MACHINE_DIR" ] ; then
  exit 1  
fi
echo "$MACHINE_DIR"

if [ ! -d "$MACHINE_DIR/.machines" ]; then
  mkdir "$MACHINE_DIR/.machines"
  echo "directory .machines created in home directory"
fi

if [ ! -f "$MACHINE_DIR/.machines/vminfo.json" ]; then
  cp "$VAGRANT_VM/scripts/vminfo.json" "$MACHINE_DIR/.machines/vminfo.json"
fi

sudo cp $VAGRANT_VM/scripts/vm_builder.py /usr/bin/vm_builder
sudo cp $VAGRANT_VM/scripts/vm_models.py /usr/bin/vm_models.py
sudo cp $VAGRANT_VM/create_lab.sh /usr/bin/create_lab

sudo sed -i 's@VAGRANT_MACHINES_FOLDER_PATH@'$MACHINE_DIR'/.machines@' /usr/bin/vm_builder
sudo sed -i 's@VAGRANT_MACHINES_FOLDER_PATH@'$MACHINE_DIR'/.machines@' /usr/bin/vm_models.py
sudo sed -i 's@LAB_IN_A_SERVER_ANSIBLE_SCRIPTS_PATH@'$VAGRANT_VM'/ansible@' /usr/bin/vm_builder
sudo sed -i 's@LAB_IN_A_SERVER_ANSIBLE_SCRIPTS_PATH@'$VAGRANT_VM'/ansible@' /usr/bin/vm_models.py
sudo sed -i 's@LAB_IN_A_SERVER_INFO_FILE@'$MACHINE_DIR'/.machines/vminfo.json@' /usr/bin/vm_builder
sudo sed -i '3 s@LAB_IN_SERVER_PATH_INFO@'$VAGRANT_VM'@' /usr/bin/create_lab

sudo chmod 777 /usr/bin/vm_builder
sudo chmod 777 /usr/bin/create_lab



