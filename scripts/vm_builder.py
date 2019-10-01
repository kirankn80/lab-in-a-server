#!/usr/bin/env python3

import argparse
import os
import re
import yaml
import json
import random
import datetime
import pprint
import sys
import shutil
import requests
from colorama import Fore, init
import subprocess
from schema import *
from prettytable import PrettyTable
import vm_models as vm

############# global vars


par_dir = "VAGRANT_MACHINES_FOLDER_PATH"
#par_dir = os.path.join(lab_path, ".machines")

host_vboxnet_ip = ""

ansible_scripts_path = "LAB_IN_A_SERVER_ANSIBLE_SCRIPTS_PATH"

info_file = "LAB_IN_A_SERVER_INFO_FILE"
#info_file = os.path.join(lab_path, "all_in_one/vagrant_vm/vminfo.json")
# append timestamp as suffix so that internal_network interface names are unique across
unique_suffix = str(datetime.datetime.now().strftime("_%Y%m%d%m%s"))

############# decorator

def static_var(varname, value):
  def decorate(func):
    setattr(func, varname, value)
    return func
  return decorate

############# dummy functions

def get_keys(prefix, num):
  list = []
  for i in range(1, num+1):
    list.append(prefix+str(i))
  return list

def get_host_names(name, dict, list):
  for element in list:
    dict[element] = str(name+'-'+element)
  return dict

############# validation functions

def validate_name(name):
  return Regex('^[a-zA-Z][a-zA-Z0-9-]*[a-zA-Z0-9]$').validate(name)

def validate_managementip(ip_address):
  ping_test = ["ping", "-q", "-c", "1"]
  ping_test.append(ip_address)
  op = subprocess.run(ping_test, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
  if op.stderr:
    print("Unknown host")
    return False
  packet_loss = re.findall("(\d{1,3}.\d)% packet loss", op.stdout.decode("UTF-8"))
  if float(packet_loss[0]) == 100.0:
    return True
  print("Ip address is reachable")
  return False

# function validating the existance of file
def validate_file(file_name):
  if not os.path.exists(file_name):
    parser.error("File %s not found in the path"%(file_name))
  else:
    return file_name

def validate_topology_name_creation(name):
  if not os.path.exists(info_file):
    print(Fore.RED + "Note: " + Fore.WHITE + "info file not found in path")
    return False
  with open(info_file, "r") as info_file_handler:
    info = json.load(info_file_handler)
  if name in info.keys():
    print(Fore.RED + "Note: " + Fore.WHITE + "Topology exists with name %s"%(name))
    return False 
  return True

def validate_topology_name_deletion(name):
  if not os.path.exists(info_file):
    print(Fore.RED + "Note: " + Fore.WHITE + "info file not found in path")
    parser.error("File %s not found in the path"%(info_file))
  with open(info_file, "r") as info_file_handler:
    info = json.load(info_file_handler)
  if name not in info.keys():
    parser.error("topology with name %s does not exist\n Check topology name"%(name)) 
  return name

def validate_topology_name_view(name):
  if not os.path.exists(info_file):
    print(Fore.RED + "Note: " + Fore.WHITE + "info file not found in path")
    parser.error("File %s not found in the path"%(info_file))
  with open(info_file, "r") as info_file_handler:
    info = json.load(info_file_handler)
  print(name)
  if name not in info.keys():
    parser.error("topology with name %s does not exist\n Check topology name"%(name)) 
  return name

def parse_input_file(file_name):
  valid_templates = ['devenv', 'all_in_one', 'three_node_vqfx', 'three_node']
  inputs = Schema({'template' : And(str, lambda name: name in valid_templates), Optional(str) : object }).validate(yaml.load(open(file_name, "r"), Loader = yaml.FullLoader))
  return inputs

def validate_flavour(flavour):
  if flavour in vm.flavour.keys():
    return True
  print(Fore.RED + "Note:" + Fore.WHITE + "Flavour %s does not exist"%(flavour))
  return False

def validate_tnv_additional_nodes(inputs,n):
  if 'contrail_command_ip' in inputs.keys() and 'contrail_version' in inputs.keys():
    if n < 2:
      return True
  else:
    if n < 3:
      return True
  print(Fore.RED + "Note: " + Fore.WHITE + "Total number of nodes connected to switch cannot exceed 5")
  return False
    

def validate_tnv_dpdk_computes(inputs,n):
  an = inputs['additional_nodes']
  if n <= (2 + inputs['additional_compute']):
    return True
  print(Fore.RED + "Note: " + Fore.WHITE + "Total number of dpdk computes cannot be greater than {}".format(an+2))
  return False

def validate_contrail_command(inputs,command_ip):
  if 'contrail_version' not in inputs.keys():
    print(Fore.RED + "Note: " + Fore.WHITE + "contrail version is to be specified for having contrail command")
    return False
  return True

def validate_tn_dpdk_computes(inputs,n):
  if n <= inputs['additional_compute']+2:
    return True
  print(Fore.RED + "Note: " + Fore.WHITE + "The number of dpdk computes cannot be greater than total number of computes")
  return False

def validate_registry(repo):
  if repo in ['cirepo', 'nodei40', 'hub']:
    return True
  print(Fore.RED + "Note: " + Fore.WHITE + "The value for registry should be one among -")
  print(['cirepo', 'nodei40', 'hub'])
  return False

def validate_devenv_branch(input_branch):
  git_list_branch_api = "https://api.github.com/repos/Juniper/contrail-dev-env/branches"
  branches_info = requests.get(git_list_branch_api).json()
  all_branches = []
  for branch in branches_info:
    all_branches.append(branch['name'])
  if input_branch in all_branches:
    return True
  else:
    print(Fore.RED + "Note: " + Fore.WHITE + "The branch name can be one among - ")
    print(all_branches)
    return False

def validate_deployer_branch(input_branch):
  git_list_branch_api = "https://api.github.com/repos/Juniper/contrail-ansible-deployer/branches"
  branches_info = requests.get(git_list_branch_api).json()
  all_branches = []
  for branch in branches_info:
    all_branches.append(branch['name'])
  if input_branch in all_branches:
    return True
  else:
    print(Fore.RED + "Note: " + Fore.WHITE + "The branch name can be one among - ")
    print(all_branches)
    return False

#########################set defaults

def set_defaults(inputs):
  if 'internal_network' not in inputs.keys():
    inputs['internal_network'] = False

  if 'management_ip' not in inputs.keys():
    inputs['management_ip'] = []

  if 'management_ip' in inputs.keys() and type(inputs['management_ip']) is dict:
    inputs['management_ip'] = [inputs['management_ip']]

  if 'flavour' not in inputs.keys():
    inputs['flavour'] = "large"

  if 'openstack_version' not in inputs.keys():
    inputs['openstack_version'] = "queens"

  if 'registry' not in inputs.keys():
    inputs['registry'] = "cirepo"

def set_defaults_three_node(inputs):

  if 'additional_compute' not in inputs.keys():
    inputs['additional_compute'] = 0

  if 'additional_control' not in inputs.keys():
    inputs['additional_control'] = 0 

  inputs['additional_nodes'] = inputs['additional_compute'] + inputs['additional_control']

  if 'dpdk_computes' not in inputs.keys():
    inputs['dpdk_computes'] = 0

def update_kernel(release,host_instance):
  try:
    if release == "master" or float(release) > 1909:
      for node in host_instance:
        node.provision = [{'method': 'ansible', 'path': "\"%s\""%(os.path.join(ansible_scripts_path, "kernel_upgrade.yml")), 'variables': {}}] + node.provision
  except ValueError:
    pass

################## api functions

def get_contrail_deployer_branch(contrail_version):
  git_list_branch_api = "https://api.github.com/repos/Juniper/contrail-ansible-deployer/branches"
  branches_info = requests.get(git_list_branch_api).json()
  all_branches = {}
  for branch in branches_info:
    branch_name = branch['name']
    if branch_name[0] == "R":
      branch_name = branch_name[1:]
    all_branches[str(branch_name)] = branch['name']
  for branch in all_branches.keys():
    if branch in contrail_version:
      print("checking out {} branch in contrail ansible deployer".format(all_branches[branch]))
      return branch, all_branches[branch]
  print("No matching version found \n checking out {} branch in contrail ansible deployer".format("master"))
  return("master", "master")

def check_for_devenv_vm_init_script(devbranch):
	git_vm_script_path = "https://raw.githubusercontent.com/Juniper/contrail-dev-env/BRANCH/vm-dev-env/init.sh"
	git_vm_script_path = git_vm_script_path.replace("BRANCH", devbranch)
	response = requests.get(git_vm_script_path)
	if response.status_code == 404:
		return "dev-lite-container.yml"
	else:
		return "dev-lite.yml"

################## network address allocation functions

# returns list of ip address belonging to same /24 subnet 
@static_var("octet3",251)
def get_ctrl_data_ip(hosts):
  ctrl_data_subnet = { 'octet1': '192', 'octet2': '168'}
  ctrl_data_ip = {}
  #ctrl_data_subnet['octet3'] = str(random.randrange(0,255))
  for i in range(0, len(hosts)):
    ctrl_data_ip[hosts[i]]= str(ctrl_data_subnet['octet1']+'.'+ctrl_data_subnet['octet2']+'.'+str(get_ctrl_data_ip.octet3)+'.'+str(i+2))
  gateway = str(ctrl_data_subnet['octet1']+'.'+ctrl_data_subnet['octet2']+'.'+str(get_ctrl_data_ip.octet3)+'.'+str(1))
  get_ctrl_data_ip.octet3 += 1
  return ctrl_data_ip, gateway

@static_var("count",2)
def get_vboxnet_ip():
  #print("\n\nhello\n\n")
  global host_vboxnet_ip
  vbox_command = ["vboxmanage", "list", "hostonlyifs"]
  if get_vboxnet_ip.count == 2:
    try:
      op = subprocess.run(vbox_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
      print(op.stdout.decode("UTF-8"))
      print(op.stderr.decode("UTF-8"))
      print("try block")
    except subprocess.CalledProcessError as e:
      raise e
      print("except block")
      sys.exit()
    else:
      print("else block")
      print(op.stdout.decode("UTF-8"),"\n\n\n")
      print(op.stderr.decode("UTF-8"),"\n\n\n")
      existing_vboxnet_tuples = re.findall('Name:\s+(vboxnet\d)[\s\S]{1,100}IPAddress:\s+([\d{1,3}\.]+)', op.stdout.decode("UTF-8"))
      vboxnet_ips = []
      for vbnet in existing_vboxnet_tuples:
        vboxnet_ips.append(vbnet[1])
      valid_vboxnet_tuples = []
      for i in range(1,250):
        valid_vboxnet_tuples.append('192.168.{}.1'.format(i))
      host_vboxnet_ip = list(set(valid_vboxnet_tuples).difference(set(vboxnet_ips)))[0]
  vbip = str(host_vboxnet_ip[:-1]+str(get_vboxnet_ip.count))
  get_vboxnet_ip.count += 1
  return vbip

# assign one management ip to each host and {} when given number of management ip is less
def set_management_ips(hosts, management_ip_input, interfaces = {}, vboxnet_ips = {}, internalnet = 0):
  management_ip = {}
  for node in range(0,min(len(management_ip_input),len(hosts))):
    management_ip[hosts[node]] = management_ip_input[node]
  if len(management_ip_input) < len(hosts):
    for node in range(len(management_ip_input), len(hosts)):
      if internalnet:
        vboxnet_ips, interfaces = set_vboxnet_ips([hosts[node]], interfaces, vboxnet_ips)
      management_ip[hosts[node]] = {}
  return management_ip, vboxnet_ips, interfaces

def set_vboxnet_ips(hosts, interfaces, vboxnet_ips):
  for node in hosts:
    if node not in interfaces.keys():
      interfaces[node] = []
    vboxip = get_vboxnet_ip()
    vboxnet_ips[node] = vboxip
    interfaces[node].append({'name': 'h_only','ip': '%s'%(vboxip),'netmask':'%s'%('255.255.255.0'),'host_only': True})
  return vboxnet_ips, interfaces

# setting up internal_networks
@static_var("icounter",1)
def set_up_switch_host_interfaces(interfaces, hosts, switch):
  global ctrl_data
  ctrl_data, gateway = get_ctrl_data_ip(hosts)
  if switch not in interfaces.keys():
    interfaces[switch] = []
  for host in hosts:
    if host not in interfaces.keys():
      interfaces[host] = []
    interfaces[host].append({'name': str('i'+str(set_up_switch_host_interfaces.icounter)+unique_suffix), 'ip': ctrl_data[host], 'netmask':'255.255.255.0', 'host_only': False})
    interfaces[switch].append(str('i'+str(set_up_switch_host_interfaces.icounter)+unique_suffix))
    set_up_switch_host_interfaces.icounter += 1
  return ctrl_data, gateway, interfaces 

@static_var("scounter",1)
def set_up_switch_switch_interfaces(interfaces, switch1, switch2):
  if switch1 not in interfaces.keys():
    interfaces[switch1] = []
  if switch2 not in interfaces.keys():
    interfaces[switch2] = []
  interface = str('s'+str(set_up_switch_switch_interfaces.scounter)+unique_suffix)
  interfaces[switch1].append(interface)
  interfaces[switch2].append(interface)
  set_up_switch_switch_interfaces.scounter += 1
  return interfaces

############### update info file 
def insert_topo_info(template, name, hosts, host_names, management_ips = {}, vboxnet_ips = {}, ctrl_data_ips = {}, contrail_version = None):
  topo_info = {}
  print(os.path.join(par_dir, name))
  topo_info['contrail_version'] = contrail_version
  topo_info['hosts'] = hosts
  topo_info['template'] = template
  topo_info['dirname'] = os.path.join(par_dir, name)
  topo_info['host_vboxnet_ip'] = host_vboxnet_ip
  topo_info['management_data'] = management_ips
  topo_info['vboxnet_interfaces'] = vboxnet_ips
  topo_info['ctrl_data_ip'] = ctrl_data_ips
  topo_info['hostnames'] = host_names

  if not os.path.exists(info_file):
    print("info file not found in path")
    sys.exit()
  with open(info_file, "r") as info_file_handler:
    info = json.load(info_file_handler)
    if name in info.keys():
      print("topology already exists")
      sys.exit()
  info[name] = topo_info
  json.dump(info, open(info_file, "w"))

def create_workspace(name):
  dirname = os.path.join(par_dir, name)
  if os.path.exists(dirname):
    print("directory %s exists already. Delete the directory and try again"%dirname)
    sys.exit()
  try: 
    os.mkdir(dirname) 
  except OSError as e: 
    print(e)
    raise(e)
    print("failed to create workspace")
    sys.exit()
  return dirname

def destroy_workspace(dirname):
  try:
    os.chdir("/root")
    shutil.rmtree(dirname)
  except Exception as e:
    print(e)
    raise(e)
    print("failed to delete workspace %s"%(dirname))
    sys.exit()


############### topology creation and provisioning

def get_contrail_command(inputs,name,flavour,management_ip,interfaces,vm_ip):
  x = vm.CENTOS(name, flavour,management_ip, interfaces, [\
      {'method': 'ansible', 'path': "\"%s\""%(os.path.join(ansible_scripts_path, 'ui.yml')), 'variables': {'vm_ip': vm_ip, 'contrail_version': inputs['contrail_version'], 'ntp_server': 'ntp.juniper.net', 'registry': inputs['registry'], 'vagrant_root': "%s"%os.path.join(par_dir,inputs['name'])}}, \
      {'method': 'shell', 'path': "\"%s\""%(os.path.join(ansible_scripts_path, 'scripts/docker.sh'))},
      {'method': 'file', 'source': "\"%s\""%(os.path.join(ansible_scripts_path, 'scripts/cc.sh')), 'destination': "\"/tmp/cc.sh\""},
      {'method': 'shell', 'inline': "\"chmod +x /tmp/cc.sh && /tmp/cc.sh\""}])
  return x

def three_node(inputs):
  # validate input fields
  set_defaults_three_node(inputs)

  Schema({'name' : And(lambda value: validate_name(value), lambda value: validate_topology_name_creation(value)),
    'additional_nodes': And(int, int),
    Optional('management_ip') : 
    [{'ip' : And(str, lambda ip: Regex('^[\d]{1,3}\.[\d]{1,3}\.[\d]{1,3}\.[\d]{1,3}$').validate(ip)), 
    'netmask' : And(str, lambda netmask: Regex('^[\d]{1,3}\.[\d]{1,3}\.[\d]{1,3}\.[\d]{1,3}$').validate(netmask)), 
    'gateway' : And(str, lambda gateway: Regex('^[\d]{1,3}\.[\d]{1,3}\.[\d]{1,3}\.[\d]{1,3}$').validate(gateway))}], 
    Optional('contrail_version'): str, 
    Optional('flavour') : And(str, lambda flavour: validate_flavour(flavour)), 
    Optional('contrail_command_ip'): 
    {'ip' : And(str, lambda ip: Regex('^[\d]{1,3}\.[\d]{1,3}\.[\d]{1,3}\.[\d]{1,3}$').validate(ip)), 
    'netmask' : And(str, lambda netmask: Regex('^[\d]{1,3}\.[\d]{1,3}\.[\d]{1,3}\.[\d]{1,3}$').validate(netmask)), 
    'gateway' : And(str, lambda gateway: Regex('^[\d]{1,3}\.[\d]{1,3}\.[\d]{1,3}\.[\d]{1,3}$').validate(gateway))},
    Optional('kolla_external_vip_address'): 
    {'ip' : And(str, lambda ip: Regex('^[\d]{1,3}\.[\d]{1,3}\.[\d]{1,3}\.[\d]{1,3}$').validate(ip)), 
    'netmask' : And(str, lambda netmask: Regex('^[\d]{1,3}\.[\d]{1,3}\.[\d]{1,3}\.[\d]{1,3}$').validate(netmask)), 
    'gateway' : And(str, lambda gateway: Regex('^[\d]{1,3}\.[\d]{1,3}\.[\d]{1,3}\.[\d]{1,3}$').validate(gateway))},
    Optional('additional_compute') : int,
    Optional('additional_control'): int,
    Optional('dpdk_computes'): And(int, lambda n: validate_tn_dpdk_computes(inputs,n)),
    Optional('registry'): And(str, lambda repo: validate_registry(repo)),
    Optional('openstack_version'): str,
    Optional('contrail_deployer_branch'): And(str, lambda value: validate_deployer_branch(value)),
    Optional('internal_network'): bool,
    Optional('template'): str}).validate(inputs)
  
  set_defaults(inputs)
  nodes_count = 3
  nodes_count = nodes_count + inputs['additional_nodes']
  hosts = get_keys('node',nodes_count)
  interfaces = {}
  management_data, vboxnet_ip, interfaces = set_management_ips(hosts[::-1], inputs['management_ip'], interfaces, {}, inputs['internal_network'])
  # add contrail_command_to_hosts
  if 'kolla_external_vip_address' in inputs.keys():
    kolla_evip = inputs['kolla_external_vip_address']['ip']
  else:
    kolla_evip_dict, interface_dummy  = set_vboxnet_ips(['kolla-evip'], {}, {})
    kolla_evip = kolla_evip_dict['kolla-evip']

  if 'contrail_command_ip' in inputs.keys():
    hosts.append('command')
    management_data['command'] = inputs['contrail_command_ip']

  # control_data_ip is hostonly ip
  ctrl_data_ip, interfaces = set_vboxnet_ips(hosts, interfaces, {})

  kolla_ivip_dict, interface_dummy  = set_vboxnet_ips(['kolla-ivip'], {}, {})
  kolla_ivip = kolla_ivip_dict['kolla-ivip']

  host_names = get_host_names(inputs['name'], {}, hosts)
  if 'command' in hosts:
    host_names['command'] = str(inputs['name']+"-node"+ str(len(host_names)-1))
  host_instance = []
  computes_controllers = []
  for node in hosts:
    if node is not 'command':
      host_instance.append(vm.CENTOS(host_names[node], "medium", management_data[node], interfaces[node], [{'method': 'ansible', 'path': "\"%s\""%(os.path.join(ansible_scripts_path, 'base_pkgs.yml')), 'variables':{}}]))
      computes_controllers.append({'host':"{}".format(host_names[node]), 'ip': ctrl_data_ip[node]})

  if 'contrail_version' in inputs.keys():
    contrail_version = inputs['contrail_version']
    if 'contrail_deployer_branch' not in inputs.keys():
      release, inputs['contrail_deployer_branch'] = get_contrail_deployer_branch(inputs['contrail_version'])
    else:
      release = "undefined"
    update_kernel(release,host_instance)
    primary = computes_controllers.pop()
    contrail_host = host_instance.pop()
    computes = host_instance[:inputs['additional_compute']]
    computes_ip = computes_controllers[:inputs['additional_compute']]
    controls = host_instance[inputs['additional_compute']:]
    controls_ip = computes_controllers[inputs['additional_compute']:]
  # increase computes size
    for compute_node in computes:
      print(compute_node)
      compute_node.flavour = "large"
    contrail_host.provision.append({'method': 'ansible', 'path': "\"%s\""%(os.path.join(ansible_scripts_path, 'multinode.yml')), 'variables':{'primary':primary, 'controls': controls_ip, 'openstack_version': inputs['openstack_version'], 'computes': computes_ip, 'registry': inputs['registry'], 'ntp_server': 'ntp.juniper.net', 'kolla_evip': kolla_evip, 'kolla_ivip': kolla_ivip, 'kvrouter_id': "101", 'contrail_version': inputs['contrail_version'], 'vagrant_root': "%s"%(os.path.join(par_dir,inputs['name'])), 'dpdk_computes':inputs['dpdk_computes'], 'contrail_deployer_branch':inputs['contrail_deployer_branch']}})
    contrail_host.provision.extend([{'method':'file', 'source':"\"%s\""%(os.path.join(ansible_scripts_path,"scripts/all.sh")), 'destination': "\"/tmp/all.sh\""},{'method': 'shell', 'inline': "\"/bin/sh /tmp/all.sh\"" }])
    host_instance.append(contrail_host)

    if 'contrail_command_ip' in inputs.keys():
      host_instance.append(get_contrail_command(inputs,name = host_names['command'], flavour="medium", management_ip=inputs['contrail_command_ip'], interfaces=interfaces['command'], vm_ip=ctrl_data_ip['command']))
  
  else:
    contrail_version = inputs['contrail_version']
    if 'command' in hosts:
      del host_names['command']

  dirname = create_workspace(inputs['name'])
  vm.generate_vagrant_file(host_instance, [], file_name=os.path.join(dirname,"Vagrantfile"))
  insert_topo_info(inputs['template'], inputs['name'], hosts, host_names, management_ips = management_data, vboxnet_ips = vboxnet_ip, ctrl_data_ips = ctrl_data_ip, contrail_version=contrail_version)
  return dirname

# depends on input parameters
# 1 switch , 3 nodes topology
def three_node_vqfx(inputs):
  # validate input fields
  set_defaults_three_node(inputs)
  
  Schema({'name' : And(lambda value: validate_name(value), lambda value: validate_topology_name_creation(value)),
    'additional_nodes': And(int,lambda n: validate_tnv_additional_nodes(inputs,n)),
    Optional('dpdk_computes'): And(int, lambda n: validate_tnv_dpdk_computes(inputs,n)),
    Optional('management_ip'): 
    [{'ip' : And(str, lambda ip: Regex('^[\d]{1,3}\.[\d]{1,3}\.[\d]{1,3}\.[\d]{1,3}$').validate(ip)), 
    'netmask' : And(str, lambda netmask: Regex('^[\d]{1,3}\.[\d]{1,3}\.[\d]{1,3}\.[\d]{1,3}$').validate(netmask)), 
    'gateway' : And(str, lambda gateway: Regex('^[\d]{1,3}\.[\d]{1,3}\.[\d]{1,3}\.[\d]{1,3}$').validate(gateway))}], 
    Optional('contrail_version'): str, 
    Optional('internal_network'): bool,
    Optional('flavour') : And(str, lambda flavour: validate_flavour(flavour)), 
    Optional('contrail_command_ip'): 
    {'ip' : And(str, lambda ip: Regex('^[\d]{1,3}\.[\d]{1,3}\.[\d]{1,3}\.[\d]{1,3}$').validate(ip)), 
    'netmask' : And(str, lambda netmask: Regex('^[\d]{1,3}\.[\d]{1,3}\.[\d]{1,3}\.[\d]{1,3}$').validate(netmask)), 
    'gateway' : And(str, lambda gateway: Regex('^[\d]{1,3}\.[\d]{1,3}\.[\d]{1,3}\.[\d]{1,3}$').validate(gateway))},
    Optional('template') : str,
    Optional('registry') : And(str, lambda repo: validate_registry(repo)),
    Optional('additional_compute') : int,
    Optional('additional_control'): int,
    Optional('openstack_version'): str,
    Optional('contrail_deployer_branch'): And(str, lambda value: validate_deployer_branch(value))}).validate(inputs)

  set_defaults(inputs)

  ctrl_data_ip = {}
  management_data = {}
  vboxnet_ips = {}
  # number of nodes 
  nodes_count = 3
  # adding additional nodes as per input file
  nodes_count = nodes_count + inputs['additional_nodes']
  # setting up keys for all the nodes
  hosts = get_keys('node',nodes_count)
  # setting up keys for all the switches
  switches = get_keys('switch', 1)
  # setting management ips if given for nodes and setting up vboxnet interface if there is less management ips
  interfaces = {}
  # setting up interfaces
  management_data, vboxnet_ip, interfaces = set_management_ips(hosts[::-1], inputs['management_ip'], interfaces, {}, inputs['internal_network'])
  
  if 'kolla_external_vip_address' in inputs.keys():
    kolla_evip = inputs['kolla_external_vip_address']['ip']
  else:
    kolla_evip_dict, interface_dummy  = set_vboxnet_ips(['kolla-evip'], {}, {})
    kolla_evip = kolla_evip_dict['kolla-evip']

  # add contrail_command_to_hosts  
  if 'contrail_command_ip' in inputs.keys():
    hosts.append('command')
    management_data['command'] = inputs['contrail_command_ip']

  ctrl_data_ip, gateway, interfaces = set_up_switch_host_interfaces(interfaces, hosts, switches[0])
  kolla_ivip = str(gateway.rsplit(".",1)[0] + "." + str(len(ctrl_data_ip)+2))
  # setting up dummy hostname //?? required??
  host_names = {}
  host_names = get_host_names(inputs['name'], host_names, hosts)
  host_names = get_host_names(inputs['name'], host_names, switches)
  if 'command' in hosts:
    host_names['command'] = str(inputs['name']+"-node"+ str(len(host_names)-1))

  switch_instance = []
  computes_controllers = []
  host_instance = []
  for node in hosts:
    if node is not 'command':
      host_instance.append(vm.CENTOS(name=host_names[node], flavour="medium", management_ip=management_data[node], interfaces=interfaces[node], provision=[{'method': 'ansible', 'path': "\"%s\""%(os.path.join(ansible_scripts_path, 'base_pkgs.yml')), 'variables':{}}]))
      computes_controllers.append({'host':"{}".format(host_names[node]), 'ip': ctrl_data_ip[node]})
  # take out the last node instance make it controller and install contrail with this as host
  if 'contrail_version' in inputs.keys():
    contrail_version = inputs['contrail_version']
    if 'contrail_deployer_branch' not in inputs.keys():
      release, inputs['contrail_deployer_branch'] = get_contrail_deployer_branch(inputs['contrail_version'])
    else:
      release = "undefined"
    update_kernel(release,host_instance)
    primary = computes_controllers.pop()
    contrail_host = host_instance.pop()
    computes = host_instance[:inputs['additional_compute']]
    computes_ip = computes_controllers[:inputs['additional_compute']]
    controls = host_instance[inputs['additional_compute']:]
    controls_ip = computes_controllers[inputs['additional_compute']:]
    # allocate more memory for computes
    for compute_node in computes:
      print(compute_node)
      compute_node.flavour = "large"
    contrail_host.provision.append({'method': 'ansible', 'path': "\"%s\""%(os.path.join(ansible_scripts_path, 'multinode.yml')), 'variables':{'primary':primary, 'controls': controls_ip, 'openstack_version': inputs['openstack_version'], 'computes': computes_ip, 'kolla_ivip': kolla_ivip, 'kolla_evip': kolla_evip, 'registry': inputs['registry'], 'ntp_server': 'ntp.juniper.net', 'contrail_version': inputs['contrail_version'], 'vagrant_root': "%s"%(os.path.join(par_dir,inputs['name'])), 'dpdk_computes':inputs['dpdk_computes'], 'contrail_deployer_branch':inputs['contrail_deployer_branch']}})
    contrail_host.provision.extend([{'method':'file', 'source':"\"%s\""%(os.path.join(ansible_scripts_path, "scripts/all.sh")), 'destination': "\"/tmp/all.sh\""},{'method': 'shell', 'inline': "\"/bin/sh /tmp/all.sh\"" }])
    host_instance.append(contrail_host)
    
    if 'contrail_command_ip' in inputs.keys():
      host_instance.append(get_contrail_command(inputs,name = host_names['command'], flavour="medium", management_ip=inputs['contrail_command_ip'], interfaces=interfaces['command'], vm_ip=ctrl_data_ip['command']))
  
  else:
    contrail_version = None

  for switch in switches:
    switch_instance.append(vm.VQFX(host_names[switch], gateway, interfaces[switch]))

  dirname = create_workspace(inputs['name'])
  vm.generate_vagrant_file(host_instance, switch_instance, file_name=os.path.join(dirname,"Vagrantfile"))
  insert_topo_info(inputs['template'], inputs['name'], hosts, host_names, management_ips = management_data, vboxnet_ips = vboxnet_ip, ctrl_data_ips = ctrl_data_ip, contrail_version=contrail_version)
  return dirname



def devenv(inputs):
  # validate schema 
  Schema({'name' : And(lambda value: validate_name(value), lambda value: validate_topology_name_creation(value)),
    'branch' : And(str, lambda value: validate_devenv_branch(value)),
    Optional('management_ip') : 
    {'ip' : And(str, lambda ip: Regex('^[\d]{1,3}\.[\d]{1,3}\.[\d]{1,3}\.[\d]{1,3}$').validate(ip)), 
    'netmask' : And(str, lambda netmask: Regex('^[\d]{1,3}\.[\d]{1,3}\.[\d]{1,3}\.[\d]{1,3}$').validate(netmask)), 
    'gateway' : And(str, lambda gateway: Regex('^[\d]{1,3}\.[\d]{1,3}\.[\d]{1,3}\.[\d]{1,3}$').validate(gateway))}, 
    Optional('internal_network') : bool, 
    Optional('template') : str }).validate(inputs)
  
  set_defaults(inputs)
  #single device
  # CENTOS(name, {management_ip}, [interfaces], [provision])
  interfaces = {}
  interfaces['node1'] = []
  management_ip, vboxnet_ip, interfaces = set_management_ips(['node1'], inputs['management_ip'], interfaces, {}, inputs['internal_network'])
  print(management_ip, interfaces)
  s1 = vm.CENTOS(str(inputs['name']+"-node1"), "large", management_ip['node1'], interfaces['node1'], [{'method': 'ansible', 'path': "\"%s\""%(os.path.join(ansible_scripts_path, check_for_devenv_vm_init_script(inputs['branch']))), 'variables': {'branch': inputs['branch']}}])
  # no switches one server

  dirname = create_workspace(inputs['name'])
  vm.generate_vagrant_file([s1], [], file_name=os.path.join(dirname,"Vagrantfile"))
  insert_topo_info(inputs['template'], inputs['name'], ['node1'], {'node1': str(inputs['name']+"-node1")}, management_ips = management_ip, vboxnet_ips = vboxnet_ip, ctrl_data_ips = {}, contrail_version=None)
  return dirname

def all_in_one(inputs):
  # validate schema
  if 'dpdk_compute' not in inputs.keys():
    inputs['dpdk_compute'] = False

  Schema({'name' : And(lambda value: validate_name(value), lambda value: validate_topology_name_creation(value)),
    Optional('management_ip') : 
    {'ip' : And(str, lambda ip: Regex('^[\d]{1,3}\.[\d]{1,3}\.[\d]{1,3}\.[\d]{1,3}$').validate(ip)), 
    'netmask' : And(str, lambda netmask: Regex('^[\d]{1,3}\.[\d]{1,3}\.[\d]{1,3}\.[\d]{1,3}$').validate(netmask)), 
    'gateway' : And(str, lambda gateway: Regex('^[\d]{1,3}\.[\d]{1,3}\.[\d]{1,3}\.[\d]{1,3}$').validate(gateway))}, 
    Optional('contrail_version'): str, 
    Optional('internal_network') : bool, 
    Optional('flavour') : And(str, lambda flavour: validate_flavour(flavour)), 
    Optional('contrail_command_ip'): 
    {'ip' : And(str, lambda ip: Regex('^[\d]{1,3}\.[\d]{1,3}\.[\d]{1,3}\.[\d]{1,3}$').validate(ip)), 
    'netmask' : And(str, lambda netmask: Regex('^[\d]{1,3}\.[\d]{1,3}\.[\d]{1,3}\.[\d]{1,3}$').validate(netmask)), 
    'gateway' : And(str, lambda gateway: Regex('^[\d]{1,3}\.[\d]{1,3}\.[\d]{1,3}\.[\d]{1,3}$').validate(gateway))}, 
    Optional('template') : str,
    Optional('dpdk_compute') : bool,
    Optional('registry') : And(str, lambda repo: validate_registry(repo)),
    Optional('openstack_version'): str,
    Optional('contrail_deployer_branch'): And(str, lambda value: validate_deployer_branch(value))}).validate(inputs)

  set_defaults(inputs)

  host_instance = []
  # provisioning for contrail role 
  #vm_ip : inputs['management_ip']['ip']
  #ntp_server : 
  #contrail_version :
  #vagrant_root :
  interfaces = {}
  interfaces['node1'] = []
  management_ip, vboxnet_ip, interfaces = set_management_ips(['node1'], inputs['management_ip'], interfaces, {}, inputs['internal_network'])
  host_instance.append(vm.CENTOS(str(inputs['name']+"-node1"), inputs['flavour'], management_ip['node1'], interfaces['node1'], [{'method': 'ansible', 'path': "\"%s\""%(os.path.join(ansible_scripts_path, 'base_pkgs.yml')), 'variables': {}}]))
  if 'contrail_version' in inputs.keys():
    contrail_version = inputs['contrail_version']
    if inputs['management_ip'] != []:
      vm_ip = management_ip['node1']['ip']
      if 'contrail_command_ip' in inputs.keys():
        command_vm_ip = inputs['contrail_command_ip']['ip']
        management_ip['command'] = inputs['contrail_command_ip']
    elif vboxnet_ip != {}:
      vm_ip = vboxnet_ip['node1']
      if 'contrail_command_ip' in inputs.keys():
        vboxnet_ip, interfaces = set_vboxnet_ips(['command'], interfaces, vboxnet_ip)
        command_vm_ip = vboxnet_ip['command']
        management_ip['command'] = inputs['contrail_command_ip']
    else:
      print("cannot install contrail without ip\n")
      sys.exit()      
    if 'contrail_deployer_branch' not in inputs.keys():
      release, inputs['contrail_deployer_branch'] = get_contrail_deployer_branch(inputs['contrail_version'])
    else:
      release = "undefined"
    update_kernel(release,host_instance)
    host_instance[0].provision.extend([{'method': 'ansible', 'path': "\"%s\""%(os.path.join(ansible_scripts_path, 'all.yml')), 'variables': {'vm_ip': vm_ip, 'vm_name': str(inputs['name']+"-node1"), 'contrail_version': inputs['contrail_version'], 'openstack_version': inputs['openstack_version'], 'registry': inputs['registry'], 'dpdk_compute': int(inputs['dpdk_compute']), 'contrail_deployer_branch': inputs['contrail_deployer_branch'],'ntp_server': 'ntp.juniper.net', 'vagrant_root': "%s"%os.path.join(par_dir,inputs['name'])}},{'method':'file', 'source':"\"%s\""%(os.path.join(ansible_scripts_path, "scripts/all.sh")), 'destination': "\"/tmp/all.sh\""}, {'method': 'shell', 'inline': "\"/bin/sh /tmp/all.sh\""}])
  # install contrail_command when contrail command ip_address is given
    if 'contrail_command_ip' in inputs.keys():
      host_instance.append(get_contrail_command(inputs,name=str(inputs['name']+"-node2"),flavour="medium", management_ip=inputs['contrail_command_ip'], interfaces=interfaces['command'], vm_ip=command_vm_ip))
  else:
    contrail_version = None
  dirname = create_workspace(inputs['name'])
  vm.generate_vagrant_file(host_instance, [], file_name=os.path.join(dirname,"Vagrantfile"))
  insert_topo_info(inputs['template'], inputs['name'], ['node1', 'command'], {'node1': str(inputs['name']+"-node1"), 'command': str(inputs['name']+"-node2")}, management_ips = management_ip, vboxnet_ips = {}, ctrl_data_ips = vboxnet_ips, contrail_version=contrail_version)
  return dirname

##################### subparser functions

def create(args):
  input_vars = parse_input_file(args.file_name)
  dir_name = globals()[input_vars['template']](input_vars)
  vagrant_up(dir_name)

def show(args):
  if not os.path.exists(info_file):
    print("info file not found in path")
    sys.exit()
  with open(info_file, "r") as info_file_handler:
    info = json.load(info_file_handler)
  topology_name = args.topology_name
  topo_info = info[topology_name]
  dirname = topo_info['dirname']
  instances_file_path = os.path.join(dirname, "config/instances.yaml")
  if not os.path.exists(instances_file_path):
    print(Fore.RED + "Note:" + Fore.WHITE + "instances file does not exist")
    instances_file_path = "DOES NOT EXIST"
  for host in topo_info['hosts']:
    table = PrettyTable(['Fields', 'Values'])
    table.add_row(["hostname", topo_info['hostnames'][host]])
    if host not in topo_info['management_data'].keys() or topo_info['management_data'][host] == {}:
      table.add_row(["public ip", None])
    else:
      table.add_row(["public ip", topo_info['management_data'][host]['ip']])
      table.add_row(["netmask", topo_info['management_data'][host]['netmask']])
      table.add_row(["default gateway", topo_info['management_data'][host]['ip']])
    if host not in topo_info['vboxnet_interfaces'].keys():
      table.add_row(["private ip", None])
    else:
      table.add_row(["private ip", topo_info['vboxnet_interfaces'][host]])
    if host not in topo_info['ctrl_data_ip'].keys():
      table.add_row(["control/data ip", None])
    else:
      table.add_row(["control/data ip", topo_info['ctrl_data_ip'][host]])
    if instances_file_path != "DOES NOT EXIST":
      contrail_info = yaml.load(open(instances_file_path, "r"), Loader = yaml.FullLoader)
      if topo_info['hostnames'][host] in contrail_info['instances'].keys():
        table.add_row(["roles", ""])
        ins = contrail_info['instances'][topo_info['hostnames'][host]]
        for role in ins['roles'].keys():
          table.add_row(["", role])
      if host == 'command':
        table.add_row(["roles", "command"])
    else:
      table.add_row(["roles", None])
    table.align["Fields"] = "l"
    table.align["Values"] = "l"
    print(table)
    print("\n")

def list_vm(args):
  if not os.path.exists(info_file):
    print("info file not found in path")
    sys.exit()
  with open(info_file, "r") as info_file_handler:
    info = json.load(info_file_handler)
  table = PrettyTable(['Topology Name', 'Template', 'Contrail Version', 'Working Directory'])
  for name, item in info.items():
    row = []
    row.append(name)
    row.append(item['template'])
    row.append(item['contrail_version'])
    row.append(item['dirname'])
    table.add_row(row)
  print(table)

def destroy(args):
  destory_command = ["vagrant", "destroy", "-f"]
  vbox_remove_command = ["vboxmanage", "hostonlyif", "remove"]
  vbox_list_command = ["vboxmanage", "list", "hostonlyifs"]
  if not os.path.exists(info_file):
    print("info file not found in path")
    sys.exit()
  with open(info_file, "r") as info_file_handler:
    info = json.load(info_file_handler)
  topo_info = info[args.topology_name]
  dirname = topo_info['dirname']
  try:
    os.chdir(dirname)
    op = subprocess.run(destory_command, stdout=sys.stdout, stderr=subprocess.STDOUT)
  except subprocess.CalledProcessError as e:
    print(e)
    print("vagrant destroy failed")
    sys.exit()
  if topo_info['host_vboxnet_ip'] is not "":
    try:
      op = subprocess.run(vbox_list_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except subprocess.CalledProcessError as e:
      raise e
      sys.exit()
      print("vboxmanage list hostonlyifs failed")
    else:
      print("vboxnet ip associated with the topology is %s"%topo_info['host_vboxnet_ip'])
      vboxnet_ip = re.findall('Name:\s+(vboxnet\d)[\s\S]{{1,100}}IPAddress:\s+{}'.format(topo_info['host_vboxnet_ip']), op.stdout.decode("UTF-8"))
      if vboxnet_ip == []:
        print("vboxnet interface name not found for ip address {} on host".format(topo_info['host_vboxnet_ip']))
      else:
        vbox_remove_command.append(vboxnet_ip[0])
        try:
          op1 = subprocess.run(vbox_remove_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except subprocess.CalledProcessError as e:
          raise e
          print("Could not delete hostonly interface on the host machine")
          sys.exit()
  info = json.load(open(info_file, "r"))
  del info[args.topology_name]
  json.dump(info, open(info_file, "w"))
  print("destroy workspace")
  destroy_workspace(dirname)
  return

def vagrant_up(dirname = "", topology_name = ""):
  vagrant_up_command = ["vagrant", "up"]
  if not dirname and not topology_name:
    print("either path to vagrantfile or the topology name is to be given a input to vagrant up")
    sys.exit()
  if topology_name:
    with open(info_file, "r") as info_file_handler:
      info = json.load(info_file_handler)
    topo_info = info[topology_name]
    dirname = topo_info['dirname']
  try:
    os.chdir(dirname)
  except Exception as e:
    print(e)
    print("cannot change directory to %s"%dirname)
    raise(e)
    sys.exit()
  else:
    print(os.getcwd())
    if not os.path.exists(os.path.join(os.getcwd(), "Vagrantfile")):
      print("Vagrantfile does not exist in directory %s"%os.getcwd()) 
      sys.exit()
    try:
      op = subprocess.run(vagrant_up_command, stdout=sys.stdout, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as e:
      raise e
      print("Could not run vagrant up command")
      sys.exit()
  print("Virtual machines are up")

################ main function

if __name__ == '__main__':
  init(autoreset=True)
  global parser
  parser = argparse.ArgumentParser()
  subparser = parser.add_subparsers(dest = 'command')
  create_topology = subparser.add_parser("create", help = "create vagrant file")
  list_topology = subparser.add_parser("list", help = "list topology details")
  show_topology = subparser.add_parser("show", help = "show individual topology details")
  delete_topology = subparser.add_parser("destroy", help = "delete topology")
  # create topology has mandatory file name as argument
  create_topology.add_argument("file_name", help = "path to the config file", type = lambda x: validate_file(x))
  # list global i.e., for all keys
  show_topology.add_argument("topology_name", help = "name of the topology", type = lambda x: validate_topology_name_view(x))
  # destroy vm 
  delete_topology.add_argument("topology_name", help = "name of the topology to be destroyed",  type = lambda x: validate_topology_name_deletion(x))
  
  args = parser.parse_args()
  #print(args)
  if args.command == "list":
    list_vm(args)
  else:
    globals()[args.command](args)
  
