#!/bin/bash -ex
set -x

EOF=EOF
DIR="$( cd -P "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
source $DIR/user-list.cfg

print_usage() {
    echo ""
    echo "Usage: create_vm.sh <user-id> [VM OPTIONS]"
    echo ""
    echo "    VM OPTIONS:"
    echo "       --dev           : Create the Dev VM"
    echo "       --dev-lite      : Create the Headless Dev VM"
    echo "       --all <version> : Create the Contrail all-in-one and UI VM"
    echo "       --destroy       : Destroy the VM"
    echo ""
    echo "Note: Each developer is assigned with an ip range. The dev VM is created with the"
    echo "first ip in that range. For example, if your assgined range is 10.155.75.100-109, then"
    echo "dev VM is assigned 10.155.75.100."
    echo "The target VM is created with the second ip in that range."
    echo ""
    echo "Here are assigned ip ranges:"
    echo ""

    if [ $# -eq 1 ]; then
        exit $1
    fi
    exit 1
}

generate_vagrantfile() {
    local user=$1
    local name=$2
    local memory=$3
    local cpus=$4
    local vagrantdir="$user"_"$name"

    mkdir -p $DIR/vagrant_vm/$vagrantdir/config
    cat << EOF > $DIR/vagrant_vm/$vagrantdir/Vagrantfile
vagrant_root = File.dirname(__FILE__)

Vagrant.configure("2") do |config|
  config.vm.box = "qarham/CentOS7.5-350GB"
  config.vbguest.auto_update = false

  config.vm.define "$user_id-$name" do |m|
    m.vm.hostname = "$user_id-$name"
    m.vm.provider "virtualbox" do |v|
      v.memory = $memory
      v.cpus = $cpus
    end

    m.vm.network "public_network", auto_config: false, bridge: '$host_interface'

    m.vm.provision :ansible do |ansible|
      ansible.playbook = "$DIR/vagrant_vm/ansible/$name.yml"
      ansible.extra_vars = {
          vm_interface: "$interface",
          vm_gateway_ip: "$gateway_ip",
          vm_ip: "$vm_ip",
          vm_netmask: "255.255.224.0",
          vm_dns1: "172.21.200.60",
          vm_dns2: "8.8.8.8",
          vm_domain: "englab.juniper.net jnpr.net juniper.net",
          ntp_server: "$ntp_server",
          contrail_version: "$tag",
          vagrant_root: vagrant_root
      }
    end
EOF
    if [ "$name" == "all" ]; then
        cat << EOF >> $DIR/vagrant_vm/$vagrantdir/Vagrantfile

    m.vm.provision "shell", path: "$DIR/vagrant_vm/ansible/scripts/$name.sh"
EOF
    fi
    cat << EOF >> $DIR/vagrant_vm/$vagrantdir/Vagrantfile
  end
EOF
    if [ "$name" == "all" ]; then
        cat << EOF >> $DIR/vagrant_vm/$vagrantdir/Vagrantfile

  config.vm.define "$user_id-ui" do |cc|
    cc.vm.hostname = "$user_id-ui"
    cc.vm.provider "virtualbox" do |v|
      v.memory = 4000
      v.cpus = 2
    end

    cc.vm.network "public_network", auto_config: false, bridge: '$host_interface'

    cc.vm.network "forwarded_port", guest: 9091, host: 9091
    cc.vm.provision :ansible do |ansible|
      ansible.playbook = "$DIR/vagrant_vm/ansible/ui.yml"
      ansible.extra_vars = {
          vm_interface: "$interface",
          vm_gateway_ip: "$gateway_ip",
          vm_ip: "$ui_ip",
          vm_netmask: "255.255.224.0",
          vm_dns1: "172.21.200.60",
          vm_dns2: "8.8.8.8",
          vm_domain: "englab.juniper.net jnpr.net juniper.net",
          ntp_server: "$ntp_server",
          contrail_version: "$ui_tag",
          vagrant_root: vagrant_root
      }
    end
    cc.vm.provision "shell", inline: "> /etc/profile.d/myvars.sh"
    cc.vm.provision "shell", inline: "echo 'export CCD_IMAGE=ci-repo.englab.juniper.net:5010/contrail-command-deployer:$ui_tag' >> /etc/profile.d/myvars.sh"
    cc.vm.provision "shell", inline: "echo 'export COMMAND_SERVERS_FILE=/tmp/command_servers.yml' >> /etc/profile.d/myvars.sh"
    cc.vm.provision "shell", inline: "echo 'export INSTANCES_FILE=/tmp/instances.yml' >> /etc/profile.d/myvars.sh"

    cc.vm.provision "file", source: "config/command_servers.yml", destination: "/tmp/command_servers.yml"
    cc.vm.provision "file", source: "config/instances.yml", destination: "/tmp/instances.yml"

    cc.vm.provision "shell", path: "$DIR/vagrant_vm/ansible/scripts/docker.sh"
    cc.vm.provision "file", source: "$DIR/vagrant_vm/ansible/scripts/cc.sh", destination: "/tmp/cc.sh"
    cc.vm.provision "shell", inline: "chmod +x /tmp/cc.sh"
    cc.vm.provision "shell", inline: "/tmp/cc.sh"
  end
EOF
    fi
    cat << EOF >> $DIR/vagrant_vm/$vagrantdir/Vagrantfile
end
EOF

    if [ "$name" == "all" ]; then
        ansible-playbook ansible/command.yml --extra-vars "vm_ip=$ui_ip ntp_server=$ntp_server contrail_version=$ui_tag vagrant_root=$DIR/vagrant_vm/$vagrantdir"
    fi
}

create_vm() {
    local user=$1
    local name=$2
    local vagrantdir="$user"_"$name"

    cd $DIR/vagrant_vm/$vagrantdir
    if [ $destroy -eq 1 ]; then
        vagrant destroy -f
    else
        echo "Creating ${user}_${name} vm with IP $vm_ip..."
        if [ "$name" == "all" ]; then
            echo "Creating ${user}_ui vm with IP $ui_ip..."
        fi
        vagrant up
    fi
    cd $DIR
}

dev_vm=0
dev_lite_vm=0
all_vm=0
destroy=0

while [ $# -gt 0 ]
do
    case "$1" in
        --dev)      dev_vm=1                           ;;
        --dev-lite) dev_lite_vm=1                      ;;
        --all)      all_vm=1; tag=$2; ui_tag=$2; shift ;;
        --destroy)  destroy=1                          ;;
        --help)     print_usage 0                      ;;
        -*)         echo "Error! Unknown option $1";
                    print_usage                        ;;
        *)          if [ -z "$user_id" ]; then
                        user_id="$1"
                    else
                        print_usage
                    fi                                 ;;
    esac
    shift
done

if [ -z "$user_id" ]; then
    user_id=$(whoami)
fi
if [ $dev_vm -eq 0 -a $dev_lite_vm -eq 0 -a $all_vm -eq 0 ]; then
    print_usage
fi
if [ $all_vm -eq 1 -a -z "$tag" ]; then
    print_usage
fi

set -e
interface="eth1"
host_interface="em1"
ntp_server="ntp.juniper.net"
gateway_ip=$(ip route | grep default | grep $host_interface | awk '{print $3}')
all_id=${user_id}_all
all_ip=${!all_id}
ui_id=${user_id}_ui
ui_ip=${!ui_id}
dev_id=${user_id}_dev
dev_ip=${!dev_id}

(vagrant plugin list | grep vbguest >& /dev/null) || vagrant plugin install vagrant-vbguest
vagrant_dir="$user_id"_vm
if [ $dev_vm -eq 1 ]; then
    vm_ip=$dev_ip
    playbook="dev.yml"
    generate_vagrantfile $user_id dev 32000 7
    create_vm $user_id dev
fi
if [ $dev_lite_vm -eq 1 ]; then
    vm_ip=$dev_ip
    playbook="dev-lite.yml"
    generate_vagrantfile $user_id dev-lite 32000 7
    create_vm $user_id dev-lite
fi
if [ $all_vm -eq 1 ]; then
    vm_ip=$all_ip
    count=$(vboxmanage list runningvms | grep all | wc -l)
    if [ $count -gt 5 -a $destroy -ne 1 ]; then
        echo "Cannot create more VMs, 3 or more aio+ui VMs are already running."
        exit 1
    fi
    playbook="all.yml"
    generate_vagrantfile $user_id all 48000 8
    create_vm $user_id all
fi
