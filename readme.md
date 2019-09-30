# Lab-in-a-server

Lab-in-a-server is a tool to spin up virtual machines. The tool is a wrapper for Vagrant.

## Installation

### 1. Clone the repository

```
  git clone https://github.com/kirankn80/lab-in-a-server.git
  git checkout version1

``` 
### 2. Run installer.sh 
For setting up execution environment and first time installation

```
  cd lab-in-a-server
  sudo ./installer.sh 

``` 

## Tool Usage

### 1. Creating Virtual Machines
Configuration file should be given as the input for creating vms. The configuration file will have attributes specific to topologies.

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

```
create_lab show <topology_name> 
```
<topology_name> is the unique name given at the time of creation.
Displays all the resources assigned to the virtual machines in the topology.

### 3. Destroying Virtual Machines
Deallocate the resources assigned to the virtual machines

#### command
```
create_lab destroy <topology_name>
```

## Topologies Supported

1. Dev-env
2. All-in-one
3. Three node setup 
4. Three node setup with VQFX

## Input Format
Every configuration file given at the time of topology creation can have these fields specified

#### 1. template : <template_name> (mandatory)
Template name specifies the topology and it should be one among [ devenv, all_in_one, three_node_vqfx, three_node ] 

#### 2. name : <name> (mandatory)
Unique name given for a deployment

#### 3. management_ip : <management_ip> (optional)
List of public ip address to be assigned to the virtual machines.
```
{'ip' : '10.204.220.30', 'netmask':'255.255.255.192','gateway': '10.204.220.62'}
```
#### 4. internal_network: <True/False> (optional)
When True, assigns private ip address accessible from host machine, as management ip. It is "FALSE" by default.

### 1. Dev-env

input file - dev_env.yml
```
template : 'devenv'
name : dev
internal_network: False
branch: R1910
management_ip: { 'ip' : '10.204.220.30', 'netmask':'255.255.255.192','gateway': '10.204.220.62'}
```
#### 1. branch: <branch> (mandatory)
The branch which is checked out for creating dev-env from [contrail-dev-env](https://github.com/Juniper/contrail-dev-env.git) repository.

### 2. All-in-one

input file - aio.yml
```
template : all_in_one
name : aio1
internal_network: True
contrail_version: 1910-3
#management_ip:
openstack_version: queens
registry: nodei40
contrail_command_ip: { 'ip' : '10.204.220.30', 'netmask':'255.255.255.192','gateway': '10.204.220.62'}
```
#### 1. contrail_version: <contrail_version> (optional)
The virtual machines are provisioned with given contrail version. 

#### 2. registry: <registry> (optional)
The value for this field should be one among [cirepo, nodei40, hub]. The images are pulled from the registry specified. cirepo is the default registry.

#### 3. openstack_version: <openstack_version> (optional)
Openstack version is "queens" by default.

#### 4. contrail_command_ip: <contrail_command_ip> (optional)
If this field is specified, then contrail-command is installed.

### 3. Three node with VQFX
The template spins up 1 controller node and 2 compute nodes connected to VQFX box.

input file - three_node_vqfx.yml
```
template : 'three_node_vqfx'
name : tnv-f
additional_control: 1
additional_compute: 1
dpdk_computes: 1
contrail_version: 1910-3
registry: nodei40
internal_network: True
openstack_version: queens
contrail_command_ip: { 'ip' : '10.204.220.30', 'netmask':'255.255.255.192','gateway': '10.204.220.62'}
```
#### 1. additional_control: <additional_control> (optional)
The number of additional control nodes to be provisioned. Zero by default.

#### 2. additional_compute: <additional_compute> (optional)
The number of additional compute nodes to be provisioned. Zero by default.

#### 3. dpdk_computes: <dpdk_computes> (optional)
The number of dpdk computes to be provisioned. The default number is zero. The value for this field should always be <= additional_computes + 2.

### Note: The total number of nodes that can be connected to VQFX box is limited to 5. Including node for contrail-command.
### 4. Three node setup
The template spins up 1 controller node and 2 compute nodes.

input file - three_node.yml
```
template : three_node
name : tn-f
internal_network: False
contrail_version: 1910-3
openstack_version: queens
dpdk_computes: 1
registry: nodei40
management_ip: [{'ip' : '10.204.220.31', 'netmask':'255.255.255.192','gateway': '10.204.220.62'},
{'ip' : '10.204.220.32', 'netmask':'255.255.255.192','gateway': '10.204.220.62'},
{'ip' : '10.204.220.33', 'netmask':'255.255.255.192','gateway': '10.204.220.62'}]
```
## Note:
If the contrail_version is not specified during topology creation, the virtual machines are still up without contrail.