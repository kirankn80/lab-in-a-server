# Lab-in-a-server

This tool can be used to create pre-defined virtual topologies (dev env, all-in-one, three-node, three node vqfx) on a single server very easily. And with the restructured code, one can bring up their own custom topologies by implementing the python script and integrating it with the code. The idea is to leverage high end servers and spin up Virtual machines and use them as Bare-metal servers. We can eliminate the need of physical servers, physical switches, physical routers and their painful connections and mis-configurations. The high end servers can be used effectively. As a thumb rule, we can spin about 15 to 20 virtual machines as bare metals in each of the high-end physical servers. VMs can be as fast as bare metals, so the difference between physical and virtual systems are blurred. The tool combines the power of vagrant, virtualbox and python to create virtual topologies, install contrail and provision the cluster. This tool makes the life of developers and testers very easy by doing all these using a simple yaml file. It can also assign Floating IPs to the bare metal instances so that they are accessible through the LAN.

## Installation

### 0. Pre-requisites
1) A high-end Xeon server with about 40 cores, atleast 256GB RAM
2) Ubuntu 18.04 OS

### 1. Clone the repository

```
  git clone https://github.com/kirankn80/lab-in-a-server.git

``` 
### 2. Run installer.sh 


```
  cd lab-in-a-server
  sudo ./installer.sh 

``` 

## Upgrading the tool

From version2 , The Autoupgrade feature has been implemented which will update and pull if there are any changes from the git repository the user have cloned.
For the below versions 
### 1. Pull the changes
Pull the latest code in the directory

```
cd <lab-in-a-server directory>
git pull
```
### 2. Run installer.sh

```
sudo ./installer.sh
```

## Tool Usage

### 1. Creating Topologies
Configuration file should be given as the input, hence the user needs to create a yml file for creating vms. The configuration file will have attributes specific to topologies.
After creating a yml file say topo_name.yml

The command to bring up topology is

#### command

```
create_lab create lab.yml
```

### 2. View Topology Details

#### command

```
create_lab list
```
Lists all the topologies hosted on the machine, the templates and the working directory associated with them.

#### output
![create_lab list output](https://github.com/kirankn80/lab-in-a-server/blob/version1/images/list_topology.png)

#### command

```
create_lab list --resources
```
This command lists the available memory and total memory present in the host machine and memory consumed by each topology.

#### command

```
create_lab show <topology_name> 
```
<topology_name> is the unique name given at the time of creation.
Displays all the resources assigned to the virtual machines in the topology.

#### output
![contrail info](https://github.com/kirankn80/lab-in-a-server/blob/version1/images/show_topology_contrail.png)

![sample node info](https://github.com/kirankn80/lab-in-a-server/blob/version1/images/show_topology.png)

### 3. Destroying Topologies
Deallocate the resources assigned to the virtual machines

#### command
```
create_lab destroy <topology_name>
```
### 4. Rebuild Topologies
Retry building entire topology with same resources in case of failure. This command is supposed to be used when topology bring up or contrail installation fails. In case of any changes made to input file used in the creation step, the topology is supposed to be destroyed and recreated.

#### command
```
create_lab rebuild <topology_name>
```

### 5. Poweron Topologies
This command is to be used to turn on the topology when it is powered off.

#### command
```
create_lab poweron <topology_name>
```

### 6. Poweroff Topologies
This command is to be used to shutdown the running topology.

#### command
```
create_lab poweroff <topology_name>
```
### 7. To find the host-machine

To find the host-machine from the vm you can check 

```
vi /etc/host_machine_name
```


## Topologies Supported Currently

1. Dev-env
2. All-in-one
3. Three node setup 
4. Three node setup with VQFX

## Topologies which will be supported in future

1. Fabric (CRB leaf + spine)
2. Edge compute
3. Multi-compute

## Input Format
Every configuration file given at the time of topology creation should have these fields specified

#### 1. template : <template_name> (mandatory)
Template name specifies the topology and it should be one among [ devenv, all_in_one, three_node_vqfx, three_node ] 

#### 2. name : <name> (mandatory)
Unique name given for a deployment. 

#### 3. management_ip : <management_ip> (optional)
List of public ip address to be assigned to the virtual machines.

#### 4. netmask: <netmask> (mandatory when management_ip field is present)

#### 5. gateway: <gateway> (mandatory when management_ip field is present)

```
management_ip: '10.204.220.30'
netmask: '255.255.255.192'
gateway: '10.204.220.62'
```

#### 6. internal_network: <True/False> (optional)
When True, assigns private ip address accessible from host machine, as management ip. It is *FALSE* by default.

#### 7.os_version : <os_version> (optional) 
valid os_versions 

        'centos-7.5'
        'centos-7.7'
        'ubuntu-20.04'  
		
os_version is centos 7.7 by default	

if os_version is given as ubuntu then contrail provision won't work
### 1. Dev-env
![devenv setup](https://github.com/kirankn80/lab-in-a-server/blob/version1/images/devenv.png)

input file - [dev_env.yml](https://github.com/kirankn80/lab-in-a-server/blob/version1/sample-input/dev_env.yml)
```
template : 'devenv'
name : dev
internal_network: False
branch: R1910
management_ip: 10.204.220.30
netmask: 255.255.255.192
gateway: 10.204.220.62

```
#### 1. branch: <branch> (mandatory)
The branch which is checked out for creating dev-env from [contrail-dev-env](https://github.com/Juniper/contrail-dev-env.git) repository.

### 2. All-in-one
![aio setup](https://github.com/kirankn80/lab-in-a-server/blob/version1/images/aio.png)

input file - [aio.yml](https://github.com/kirankn80/lab-in-a-server/blob/version1/sample-input/aio.yml)
```
template: all_in_one
name: aio1
internal_network: True
contrail_version: "2005.61"
#management_ip:
#netmask:
#gateway
openstack_version: queens
registry: bng-artifactory
contrail_command: True
```
#### 1. contrail_version: <contrail_version> (optional)
The virtual machines are provisioned with given contrail version. This value is supposed to be a string and should be within "" when the version tag has only numbers.

```
contrail_version: "1910.30"
```


#### 2. registry: <registry> (optional)
The value for this field should be one among [bng-artifactory, svl-artifactory, cirepo, nodei40, hub]. The images are pulled from the registry specified. bng-artifactory is the default registry.

#### 3. openstack_version: <openstack_version> (optional)
Openstack version is "queens" by default.

#### 4. contrail_command: <True/False> (optional)
If this field is specified, then contrail-command is installed and one of the ip addresses from the management_ip list will be assigned to the node.

### 3. Three node with VQFX
The template spins up 1 controller node and 2 compute nodes connected to VQFX box.

![three node with vqfx setup](https://github.com/kirankn80/lab-in-a-server/blob/version1/images/tnv.png)

input file - [three_node_vqfx.yml](https://github.com/kirankn80/lab-in-a-server/blob/version1/sample-input/three_node_vqfx.yml)
```
template : 'three_node_vqfx'
name : tnv-f
additional_control: 1
additional_compute: 1
dpdk_computes: 1
contrail_version: "2005.61"
registry: bng-artifactory
management_ip: ['10.204.220.31', '10.204.220.32', '10.204.220.33', '10.204.220.30', '10.204.220.34', '10.204.220.35']
netmask: 255.255.255.192
gateway: 10.204.220.62
openstack_version: queens
kolla_external_vip_address: 10.204.220.36

```
#### 1. additional_control: <additional_control> (optional)
The number of additional control nodes to be provisioned. Zero by default.

#### 2. additional_compute: <additional_compute> (optional)
The number of additional compute nodes to be provisioned. Zero by default.

#### 3. dpdk_computes: <dpdk_computes> (optional)
The number of dpdk computes to be provisioned. The default number is zero. The value for this field should always be <= additional_computes + 2.

#### 4. kolla_external_vip_address: <kolla_evip> (optional)
This field is an ip address in the management subnet. This field is to be specified when there are multiple controllers. This field need not be specified when the internal network field is True.
The 8143 port is accessible on this interface.
Horizon will be accessible on the management network by means of the kolla_external_vip_address.

### Note: The total number of nodes that can be connected to VQFX box is limited to 5. 
### 4. Three node setup
The template spins up 1 controller node and 2 compute nodes.

![three node setup](https://github.com/kirankn80/lab-in-a-server/blob/version1/images/three-node.png)

input file - [three_node.yml](https://github.com/kirankn80/lab-in-a-server/blob/version1/sample-input/three_node.yml)
```
template : three_node
name : tn-f
additional_compute: 1
additional_controller: 1
internal_network: True
contrail_version: "2005.61"
openstack_version: queens
dpdk_computes: 1
registry: bng-artifactory
contrail_command: True
```
## Note:
If the contrail_version is not specified during topology creation, the virtual machines are still up without contrail.


## To check the logs

If the user encounters any issue and wants to debug one can find the logs of vagrant up by using the below commands

```
create_lab list 
```
copy the path of the topology

```
cd <path>
```
```
cat vagrantup.log
```
This will open the log file where the user can check for errors

## Steps to raise a ticket for the issues related to lab in a server

1. create a jira ticket with issue type as bug

2. In the epic field link it to lab-in-a-server  bugs epic

3. paste the error message or the issue clearly in the description 

4. Attach the screenshots if any 

5. click on create

6. Any issues which are not related to lab-in-a-server like 
if deployment fails, its not the tool's failure
in that case, reach out to respective teams

7. you can create a jira ticket here
```
https://contrail-jws.atlassian.net/browse/CEM-25946
```
## Steps to perform when provisioning fails
```
https://github.com/kirankn80/lab-in-a-server/wiki/Steps-to-perform-when-provisioning-fails
```
### Accessing Private IP addresses on the host-machine
#### FoxyProxy
Creates a tunnel to host machine using port forwarding.   
[https://github.com/kirankn80/cfm-vagrant/blob/master/docs/FoxyProxy-Chrome-Setup.md](https://github.com/kirankn80/cfm-vagrant/blob/master/docs/FoxyProxy-Chrome-Setup.md)    
[https://github.com/kirankn80/cfm-vagrant/blob/master/docs/FoxyProxy-FireFox-Setup.md](https://github.com/kirankn80/cfm-vagrant/blob/master/docs/FoxyProxy-FireFox-Setup.md)
