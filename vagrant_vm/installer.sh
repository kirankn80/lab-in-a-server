#!/bin/bash
pip3 install requests colorama schema pyyaml json argparse re abc enum 

VAGRANT_VM="`dirname \"$0\"`"              
VAGRANT_VM="`( cd \"$VAGRANT_VM\" && pwd )`"  
if [ -z "$VAGRANT_VM" ] ; then
  exit 1  
fi
echo "$VAGRANT_VM"

MACHINE_DIR="`(cd ~ && pwd)`"
if [ -z "$MACHINE_DIR" ] ; then
  exit 1  
fi
echo "$MACHINE_DIR"
mkdir $MACHINE_DIR/.machines

sed -i'.bak' 's@VAGRANT_MACHINES_FOLDER_PATH@'$MACHINE_DIR'/.machines@' ./scripts/vm_builder.py
sed -i'.bak' 's@VAGRANT_MACHINES_FOLDER_PATH@'$MACHINE_DIR'/.machines@' ./scripts/vm_models.py
sed -i'.bak' 's@LAB_IN_A_SERVER_ANSIBLE_SCRIPTS_PATH@'$VAGRANT_VM'/ansible@' ./scripts/vm_builder.py
sed -i'.bak' 's@LAB_IN_A_SERVER_ANSIBLE_SCRIPTS_PATH@'$VAGRANT_VM'/ansible@' ./scripts/vm_models.py
sed -i'.bak' 's@LAB_IN_A_SERVER_INFO_FILE@'$VAGRANT_VM'/vminfo.json@' ./scripts/vm_builder.py


sudo cp ./scripts/vm_builder.py /usr/bin/vm_builder
sudo cp ./scripts/vm_models.py /usr/bin/vm_models.py

sudo chmod 777 /usr/bin/vm_builder
