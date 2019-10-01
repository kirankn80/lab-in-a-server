#!/bin/bash
export LC_ALL=C

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

if [ ! -d "$MACHINE_DIR" ]; then
  mkdir "$MACHINE_DIR/.machines"
  echo "directory .machines created in home directory"
fi

if [ ! -f "$MACHINE_DIR/vminfo.json" ]; then
  cp "$VAGRANT_VM/scripts/vminfo.json" "$MACHINE_DIR/.machines/vminfo.json"
fi

sudo cp $VAGRANT_VM/scripts/vm_builder.py /usr/bin/create_lab
sudo cp $VAGRANT_VM/scripts/vm_models.py /usr/bin/vm_models.py

sudo sed -i 's@VAGRANT_MACHINES_FOLDER_PATH@'$MACHINE_DIR'/.machines@' /usr/bin/create_lab
sudo sed -i 's@VAGRANT_MACHINES_FOLDER_PATH@'$MACHINE_DIR'/.machines@' /usr/bin/vm_models.py
sudo sed -i 's@LAB_IN_A_SERVER_ANSIBLE_SCRIPTS_PATH@'$VAGRANT_VM'/ansible@' /usr/bin/create_lab
sudo sed -i 's@LAB_IN_A_SERVER_ANSIBLE_SCRIPTS_PATH@'$VAGRANT_VM'/ansible@' /usr/bin/vm_models.py
sudo sed -i 's@LAB_IN_A_SERVER_INFO_FILE@'$MACHINE_DIR'/vminfo.json@' /usr/bin/create_lab

sudo chmod 777 /usr/bin/create_lab
