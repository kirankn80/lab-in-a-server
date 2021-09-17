#!/bin/bash

LAB_IN_SERVER_PATH="LAB_IN_SERVER_PATH_INFO"

# git remote update
export LC_ALL=C

cd $LAB_IN_SERVER_PATH && git remote update
LOCAL_MASTER="`git rev-parse master`"
ORIGIN_MASTER="`git rev-parse origin/master`"

if [ $LOCAL_MASTER != $ORIGIN_MASTER ]; then
    
    TIME_STR=$(date +"%y%m%d%H%M%S")
    echo "Updating lab-in-a-server .... "
    echo "Copying the diff to ../lab_in_server_diff_$TIME_STR.diff"
    cd $LAB_IN_SERVER_PATH && git diff > ../lab_in_server_diff_$TIME_STR.diff
    cd $LAB_IN_SERVER_PATH && git checkout .
    if cd $LAB_IN_SERVER_PATH && git pull origin master; then
    
        sudo cp $LAB_IN_SERVER_PATH/scripts/vm_builder.py /usr/bin/vm_builder
        sudo cp $LAB_IN_SERVER_PATH/scripts/vm_models.py /usr/bin/vm_models.py

        MACHINE_DIR="`(cd ~ && pwd)`"

        sudo sed -i 's@VAGRANT_MACHINES_FOLDER_PATH@'$MACHINE_DIR'/.machines@' /usr/bin/vm_builder
        sudo sed -i 's@VAGRANT_MACHINES_FOLDER_PATH@'$MACHINE_DIR'/.machines@' /usr/bin/vm_models.py
        sudo sed -i 's@LAB_IN_A_SERVER_ANSIBLE_SCRIPTS_PATH@'$LAB_IN_SERVER_PATH'/ansible@' /usr/bin/vm_builder
        sudo sed -i 's@LAB_IN_A_SERVER_ANSIBLE_SCRIPTS_PATH@'$LAB_IN_SERVER_PATH'/ansible@' /usr/bin/vm_models.py
        sudo sed -i 's@LAB_IN_A_SERVER_INFO_FILE@'$MACHINE_DIR'/.machines/vminfo.json@' /usr/bin/vm_builder
        sudo sed -i 's@LAB_IN_A_SERVER_INFO_FILE@'$LAB_IN_SERVER_PATH'@' /usr/bin/create_lab

        sudo chmod 777 /usr/bin/vm_builder
        sudo chmod 777 /usr/bin/create_lab
        /usr/bin/create_lab $@
        exit 0
    else
        echo "Git pull was not successful. Please pull the latest code manually. Using old codebase.."
    fi
fi

echo $@
/usr/bin/vm_builder $@

exit 0