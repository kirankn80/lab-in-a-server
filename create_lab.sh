#!/bin/bash

LAB_IN_SERVER_PATH="LAB_IN_SERVER_PATH_INFO"

# git remote update
export LC_ALL=C

pushd $LAB_IN_SERVER_PATH > /dev/null && git remote update > /dev/null
GIT_BRANCH="`git rev-parse --abbrev-ref HEAD`"
LOCAL_MASTER="`git rev-parse $GIT_BRANCH`"
ORIGIN_MASTER="`git rev-parse origin/$GIT_BRANCH`"

if [ $(git status --porcelain | wc -l) -ne "0" ]; then

    TIME_STR=$(date +"%y%m%d%H%M%S")
    echo "Updating lab-in-a-server .... "
    echo "Copying the diff to ../lab_in_server_diff_$TIME_STR.diff"
    git diff > ../lab_in_server_diff_$TIME_STR.diff
    git checkout .
fi

if [ $LOCAL_MASTER != $ORIGIN_MASTER ]; then
    
    if git pull origin $GIT_BRANCH; then

        sudo cp $LAB_IN_SERVER_PATH/scripts/vm_builder.py /usr/bin/vm_builder
        sudo cp $LAB_IN_SERVER_PATH/scripts/all_in_one.py $SITE_PACKAGES_PATH/lab/all_in_one.py
        sudo cp $LAB_IN_SERVER_PATH/scripts/base_template.py $SITE_PACKAGES_PATH/lab/base_template.py
        sudo cp $LAB_IN_SERVER_PATH/scripts/contents.py $SITE_PACKAGES_PATH/lab/contents.py
        sudo cp $LAB_IN_SERVER_PATH/scripts/dev_env.py $SITE_PACKAGES_PATH/lab/dev_env.py
        sudo cp $LAB_IN_SERVER_PATH/scripts/interface_handler.py $SITE_PACKAGES_PATH/lab/interface_handler.py
        sudo cp $LAB_IN_SERVER_PATH/scripts/parser_commands_impl.py $SITE_PACKAGES_PATH/lab/parser_commands_impl.py
        sudo cp $LAB_IN_SERVER_PATH/scripts/provisioners.py $SITE_PACKAGES_PATH/lab/provisioners.py
        sudo cp $LAB_IN_SERVER_PATH/scripts/three_node_vqfx.py $SITE_PACKAGES_PATH/lab/three_node_vqfx.py
        sudo cp $LAB_IN_SERVER_PATH/scripts/three_node.py $SITE_PACKAGES_PATH/lab/three_node.py
        sudo cp $LAB_IN_SERVER_PATH/scripts/vagrant_wrappers.py $SITE_PACKAGES_PATH/lab/vagrant_wrappers.py
        sudo cp $LAB_IN_SERVER_PATH/scripts/vm_models.py $SITE_PACKAGES_PATH/lab/vm_models.py
        sudo cp $LAB_IN_SERVER_PATH/create_lab.sh /usr/bin/create_lab

        MACHINE_DIR="$HOME"

        sudo sed -i 's@VAGRANT_MACHINES_FOLDER_PATH@'$MACHINE_DIR'/.machines@' /usr/bin/vm_builder
        sudo sed -i 's@VAGRANT_MACHINES_FOLDER_PATH@'$MACHINE_DIR'/.machines@' $SITE_PACKAGES_PATH/lab/vm_models.py
        sudo sed -i 's@LAB_IN_A_SERVER_ANSIBLE_SCRIPTS_PATH@'/etc/lab'/ansible@' /usr/bin/vm_builder
        sudo sed -i 's@LAB_IN_A_SERVER_ANSIBLE_SCRIPTS_PATH@'/etc/lab'/ansible@' $SITE_PACKAGES_PATH/lab/vm_models.py
        sudo sed -i 's@LAB_IN_A_SERVER_INFO_FILE@'$MACHINE_DIR'/.machines/vminfo.json@' /usr/bin/vm_builder
        sudo sed -i '3 s@LAB_IN_SERVER_PATH_INFO@'$VAGRANT_VM'@' /usr/bin/create_lab

        sudo chmod 777 /usr/bin/vm_builder
        sudo chmod 777 /usr/bin/create_lab
        /usr/bin/create_lab $@
        exit 0
    else
        echo "Git pull was not successful. Please pull the latest code manually. Using old codebase..."
    fi       
fi

popd > /dev/null
/usr/bin/vm_builder $@

exit 0