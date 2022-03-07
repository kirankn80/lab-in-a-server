#!/bin/bash -v

export LC_ALL=C

SITE_PACKAGES_PATH="`python3 -m site --user-site`"


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
wget --no-check-certificate -q https://www.virtualbox.org/download/oracle_vbox_2016.asc -O- | sudo apt-key add -
wget --no-check-certificate -q https://www.virtualbox.org/download/oracle_vbox.asc -O- | sudo apt-key add -
sudo add-apt-repository "deb http://download.virtualbox.org/virtualbox/debian `lsb_release -cs` contrib"
sudo apt-get update
sudo apt-get -y install virtualbox-6.1
fi

### Vagrant install
Version="`vagrant --version`"
if [ `which vagrant | wc -l` -eq  "0" ] || ([ "$Version" != *"2.2.7"* ] && [ `vboxmanage list runningvms | wc -l` -eq "0" ]); then
wget --no-check-certificate https://releases.hashicorp.com/vagrant/2.2.7/vagrant_2.2.7_x86_64.deb
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

##install jq
sudo apt install jq

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

if [ `vagrant box list | grep kirankn/ubuntu-20.04 | wc -l` -eq "0" ]; then
wget http://10.204.217.158/images/kirankn/ubuntu-20.04-virtualbox.box
vagrant box add --name kirankn/ubuntu-20.04 /var/tmp/ubuntu-20.04-virtualbox.box
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

if [ ! -d "$SITE_PACKAGES_PATH/lab" ]; then
  mkdir -p "$SITE_PACKAGES_PATH/lab"
  echo "directory lab created in site-packages directory"
fi

if [ ! -d "/etc/lab" ]; then
  mkdir -p "/etc/lab"
  echo "directory lab created in etc directory"
fi

ANSIBLE_PATH="`/etc/lab`"

if [ ! -d "/etc/vbox/networks.conf" ]; then
  echo "* 0.0.0.0/0 ::/0" >> /etc/vbox/networks.conf
  echo "directory networks.conf created in etc/vbox directory to support higher versions of vbox"
fi

if [ ! -f "$MACHINE_DIR/.machines/vminfo.json" ]; then
  cp "$VAGRANT_VM/scripts/vminfo.json" "$MACHINE_DIR/.machines/vminfo.json"
fi

pushd $VAGRANT_VM
export GIT_BRANCH="`git rev-parse --abbrev-ref HEAD`"
export GIT_COMMIT="`git rev-parse $GIT_BRANCH`"
popd

echo "{ \"branch\": \"$GIT_BRANCH\", \"commit_id\" : \"$GIT_COMMIT\" }"  > $MACHINE_DIR/gitcommit

sudo cp $VAGRANT_VM/scripts/vm_builder.py /usr/bin/vm_builder

sudo cp $VAGRANT_VM/scripts/all_in_one.py $SITE_PACKAGES_PATH/lab/all_in_one.py
sudo cp $VAGRANT_VM/scripts/base_template.py $SITE_PACKAGES_PATH/lab/base_template.py
sudo cp $VAGRANT_VM/scripts/contents.py $SITE_PACKAGES_PATH/lab/contents.py
sudo cp $VAGRANT_VM/scripts/dev_env.py $SITE_PACKAGES_PATH/lab/dev_env.py
sudo cp $VAGRANT_VM/scripts/interface_handler.py $SITE_PACKAGES_PATH/lab/interface_handler.py
sudo cp $VAGRANT_VM/scripts/parser_commands_impl.py $SITE_PACKAGES_PATH/lab/parser_commands_impl.py
sudo cp $VAGRANT_VM/scripts/provisioners.py $SITE_PACKAGES_PATH/lab/provisioners.py
sudo cp $VAGRANT_VM/scripts/three_node_vqfx.py $SITE_PACKAGES_PATH/lab/three_node_vqfx.py
sudo cp $VAGRANT_VM/scripts/three_node.py $SITE_PACKAGES_PATH/lab/three_node.py
sudo cp $VAGRANT_VM/scripts/vagrant_wrappers.py $SITE_PACKAGES_PATH/lab/vagrant_wrappers.py
sudo cp $VAGRANT_VM/scripts/vm_models.py $SITE_PACKAGES_PATH/lab/vm_models.py
sudo cp -r $VAGRANT_VM/ansible /etc/lab

sudo cp $VAGRANT_VM/create_lab.sh /usr/bin/create_lab

sudo sed -i 's@VAGRANT_MACHINES_FOLDER_PATH@'$MACHINE_DIR'/.machines@' /usr/bin/vm_builder
sudo sed -i 's@VAGRANT_MACHINES_FOLDER_PATH@'$MACHINE_DIR'/.machines@' $SITE_PACKAGES_PATH/lab/contents.py
sudo sed -i 's@LAB_IN_A_SERVER_ANSIBLE_SCRIPTS_PATH@'/etc/lab'/ansible@' $SITE_PACKAGES_PATH/lab/contents.py
sudo sed -i 's@LAB_IN_A_SERVER_INFO_FILE@'$MACHINE_DIR'/.machines/vminfo.json@' $SITE_PACKAGES_PATH/lab/contents.py
sudo sed -i 's@LAB_IN_A_SERVER_ANSIBLE_SCRIPTS_PATH@'/etc/lab'/ansible@' $SITE_PACKAGES_PATH/lab/provisioners.py
sudo sed -i 's@VAGRANT_MACHINES_FOLDER_PATH@'$MACHINE_DIR'/.machines@' $SITE_PACKAGES_PATH/lab/vagrant_wrappers.py
sudo sed -i 's@VAGRANT_MACHINES_FOLDER_PATH@'$MACHINE_DIR'/.machines@' $SITE_PACKAGES_PATH/lab/provisioners.py
sudo sed -i 's@VAGRANT_MACHINES_FOLDER_PATH@'$MACHINE_DIR'/.machines@' $SITE_PACKAGES_PATH/lab/vm_models.py
sudo sed -i 's@LAB_IN_A_SERVER_ANSIBLE_SCRIPTS_PATH@'/etc/lab'/ansible@' /usr/bin/vm_builder
sudo sed -i 's@LAB_IN_A_SERVER_ANSIBLE_SCRIPTS_PATH@'/etc/lab'/ansible@' $SITE_PACKAGES_PATH/lab/vm_models.py
sudo sed -i 's@LAB_IN_A_SERVER_INFO_FILE@'$MACHINE_DIR'/.machines/vminfo.json@' /usr/bin/vm_builder
sudo sed -i '3 s@LAB_IN_SERVER_PATH_INFO@'$VAGRANT_VM'@' /usr/bin/create_lab

sudo chmod 777 /usr/bin/vm_builder
sudo chmod 777 /usr/bin/create_lab



