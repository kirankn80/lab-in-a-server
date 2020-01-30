#!/usr/bin/env python3

import argparse
from colorama import Fore, init
import datetime
import json
import os
import pprint
from prettytable import PrettyTable
import random
import re
import requests
from schema import *
import shutil
import subprocess
import sys
import vm_models as vm
import yaml

############# global vars


par_dir = "VAGRANT_MACHINES_FOLDER_PATH"
#par_dir = os.path.join(lab_path, ".machines")

host_vboxnet_ip = []

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

def get_flavour(inputs, alternate):
  if 'flavour' in inputs.keys():
    return inputs['flavour']
  else:
    return alternate

@static_var("nodecount", 1)
def get_host_names(name, dict, list):
  for element in list:
    if 'switch' not in element:
      dict[element] = str(name+'-node'+str(get_host_names.nodecount))
      get_host_names.nodecount += 1
    else:
      dict[element] = str(name+'-'+element)
  return dict

def management_ip(fip, vboxnet_ip, node):
  if not fip[node]:
    return vboxnet_ip[node]
  else:
    return fip[node]['ip']

def get_flavour_from_host_instance(host_instance_list):
  flavour_dict = {}
  for host_instance in host_instance_list:
    flavour_dict[host_instance[0]] = host_instance[1].flavour
  return flavour_dict

############# validation functions

def validate_name(name):
  if re.match(r'^[a-zA-Z][a-zA-Z0-9-]*[a-zA-Z0-9]$', name):
    return True
  print(Fore.RED + "Note:" + Fore.WHITE + "Name field can have letters, numbers and hyphen")
  return False

def validate_managementip(ip_address):
  ping_test = ["ping", "-q", "-c", "1"]
  ping_test.append(ip_address)
  op = subprocess.run(ping_test, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
  if op.stderr:
    print(Fore.RED + "Note:" + Fore.WHITE + "IP address error")
    return False
  packet_loss = re.findall(r"(\d{1,3}\.*\d*)% packet loss", op.stdout.decode("UTF-8"))
  if float(packet_loss[0]) == 100.0:
    return True
  print(Fore.RED + "Note:" + Fore.WHITE + "%s is reachable"%(ip_address))
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

def parse_input_file(file_name):
  valid_templates = ['devenv', 'all_in_one', 'three_node_vqfx', 'three_node']
  inputs = Schema({'template' : And(str, lambda name: name in valid_templates), Optional(str) : object}).validate(yaml.load(open(file_name, "r"), Loader=yaml.FullLoader))
  return inputs

def validate_flavour(flavour):
  if flavour in vm.flavour.keys():
    return True
  print(Fore.RED + "Note:" + Fore.WHITE + "Flavour %s does not exist"%(flavour))
  return False

def validate_tnv_additional_nodes(inputs, n):
  if 'contrail_command' in inputs.keys() and inputs['contrail_command'] and 'contrail_version' in inputs.keys():
    if n < 2:
      return True
  else:
    if n < 3:
      return True
  print(Fore.RED + "Note: " + Fore.WHITE + "Total number of nodes connected to switch cannot exceed 5")
  return False
    
def validate_tnv_dpdk_computes(inputs, n):
  an = inputs['additional_nodes']
  if n <= (2 + inputs['additional_compute']):
    return True
  print(Fore.RED + "Note: " + Fore.WHITE + "Total number of dpdk computes cannot be greater than {}".format(an+2))
  return False

def validate_contrail_command(inputs, command_ip):
  if 'contrail_version' not in inputs.keys():
    print(Fore.RED + "Note: " + Fore.WHITE + "contrail version is to be specified for having contrail command")
    return False
  return True

def validate_tn_dpdk_computes(inputs, n):
  if n <= inputs['additional_compute']+2:
    return True
  print(Fore.RED + "Note: " + Fore.WHITE + "The number of dpdk computes cannot be greater than total number of computes")
  return False

def validate_registry(repo):
  if repo in ['cirepo', 'nodei40', 'hub', 'bng-artifactory', 'svl-artifactory']:
    return True
  print(Fore.RED + "Note: " + Fore.WHITE + "The value for registry should be one among -")
  print(['cirepo', 'nodei40', 'hub', 'bng-artifactory', 'svl-artifactory'])
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

def validate_fip_count(fip_list, expected_count, command, internal_network):
  if command:
    expected_count += 1
  if len(fip_list) < expected_count and internal_network == False:
    print(Fore.RED + "Note:" + Fore.WHITE + "The number of management ips given is less than expected. Please give %d ips as input or make internal_network field as True to use private ips."%(expected_count))
    return False
  if len(fip_list) < expected_count and internal_network == True:
    use_internal_network = input("The number of management ips given is less than expected. Enter yes to use private ips as management ips. Enter no to abort\n")
    if use_internal_network.lower() != 'yes':
      if use_internal_network.lower() != 'no':
        print("Invalid input")
        return False
      else:
        print("The number of management ips given is less than expected. Please give %d ips as input or make internal_network field as True to use private ips." % (expected_count))
        return False
    return True
  return True


def validate_if_contrail_image_is_present(tag, registry):
  # Check if the given tab is present in vrouter-agent tags list in given repo
  if registry == 'nodei40':
    tag_list_uri = "http://nodei40.englab.juniper.net:5000/v2/contrail-vrouter-agent/tags/list"
  elif registry == 'hub':
    tag_list_uri = "https://hub.juniper.net/v2/contrail-nightly/contrail-vrouter-agent/tags/list"
  elif registry == 'cirepo':
    tag_list_uri = "http://ci-repo.englab.juniper.net:5010/v2/contrail-vrouter-agent/tags/list"
  else:
    return True
  tags_list = requests.get(tag_list_uri).json().get('tags')
  if tag in tags_list:
    return True
  else:
    print(Fore.RED + "Note: " + Fore.WHITE +
          "Tag {} is not present for contrail-vrouter-agent container in {}".format(tag, registry))
    return False

def is_memory_sufficient(falvour_dict):
  clear_cache()
  memory_details = get_memory_details('m')
  required_memory = 0
  for _, flavour in falvour_dict.items():
    required_memory = required_memory + vm.flavour[flavour]['memory']
  if (memory_details['available'] - required_memory) > 10240:
    return True
  else:
    print("Free memory is %d MB\n Memory required is %d MB\n Spinning up the toplogy will cause the host machine to have memory %d MB\n Aborting due to shoratge of memory \n"%(memory_details['available'], required_memory, (memory_details['available']-required_memory)))
    return False

#########################set defaults

def set_defaults(inputs):
  if 'openstack_version' not in inputs.keys():
    inputs['openstack_version'] = "queens"

  if 'registry' not in inputs.keys():
    inputs['registry'] = "bng-artifactory"

  if 'contrail_command' not in inputs.keys():
    inputs['contrail_command'] = False

  if 'internal_network' not in inputs.keys():
    inputs['internal_network'] = False
 
def format_management_ip(inputs):
  if 'management_ip' in inputs.keys() and ('netmask' not in inputs.keys() or 'gateway' not in inputs.keys()):
    print(Fore.RED + "Note:" + Fore.WHITE +
          "Please specify netmask and gateway fields")
    sys.exit()

  if 'management_ip' not in inputs.keys():
    inputs['management_ip'] = []

  if 'management_ip' in inputs.keys() and type(inputs['management_ip']) is str:
    inputs['management_ip'] = [inputs['management_ip']]
  
  management_ips = []
  for ip in inputs['management_ip']:
    management_ip_dict = {}
    management_ip_dict['ip'] = ip
    management_ip_dict['netmask'] = inputs['netmask']
    management_ip_dict['gateway'] = inputs['gateway']
    management_ips.append(management_ip_dict)
  
  inputs['management_ip'] = management_ips

def set_defaults_three_node(inputs):

  if 'additional_compute' not in inputs.keys():
    inputs['additional_compute'] = 0

  if 'additional_control' not in inputs.keys():
    inputs['additional_control'] = 0 

  inputs['additional_nodes'] = inputs['additional_compute'] + inputs['additional_control']

  if 'dpdk_computes' not in inputs.keys():
    inputs['dpdk_computes'] = 0

def get_centos_image(release):
  try:
    if float(release) < 1910:
      image = vm.CENTOS75
    if release == "master" or float(release) > 1909 or release == "undefined":
      image = vm.CENTOS77
  except ValueError:
    image = vm.CENTOS77
  return image

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
@static_var("octet3", 251)
def get_ctrl_data_ip(hosts):
  ctrl_data_subnet = {'octet1': '192', 'octet2': '168'}
  ctrl_data_ip = {}
  #ctrl_data_subnet['octet3'] = str(random.randrange(0,255))
  for i in range(0, len(hosts)):
    ctrl_data_ip[hosts[i]] = str(ctrl_data_subnet['octet1']+'.'+ctrl_data_subnet['octet2']+'.'+str(get_ctrl_data_ip.octet3)+'.'+str(i+2))
  gateway = str(ctrl_data_subnet['octet1']+'.'+ctrl_data_subnet['octet2']+'.'+str(get_ctrl_data_ip.octet3)+'.'+str(1))
  get_ctrl_data_ip.octet3 += 1
  return ctrl_data_ip, gateway

@static_var("count", 2)
@static_var("available_vboxnet_interfaces", [])
def get_vboxnet_ip(change_subnet=False):
  #print("\n\nhello\n\n")
  global host_vboxnet_ip
  if change_subnet:
    get_vboxnet_ip.count = 2
  vbox_command = ["vboxmanage", "list", "hostonlyifs"]
  if get_vboxnet_ip.count == 2:
    try:
      op = subprocess.run(vbox_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
      print(op.stdout.decode("UTF-8"))
      print(op.stderr.decode("UTF-8"))
      #print("try block")
    except subprocess.CalledProcessError as e:
      #print("except block")
      print("Error in listing hostonlyifs")
      print(e)
      sys.exit()
    else:
      existing_vboxnet_tuples = re.findall(r'Name:\s+(vboxnet\d)[\s\S]{1,100}IPAddress:\s+([\d{1,3}\.]+)', op.stdout.decode("UTF-8"))
      vboxnet_ips = []
      for vbnet in existing_vboxnet_tuples:
        vboxnet_ips.append(vbnet[1])
      valid_vboxnet_tuples = []
      for i in range(1, 250):
        valid_vboxnet_tuples.append('192.168.{}.1'.format(i))
      if get_vboxnet_ip.available_vboxnet_interfaces == []:
        get_vboxnet_ip.available_vboxnet_interfaces = list(set(valid_vboxnet_tuples).difference(set(vboxnet_ips)))
      host_vboxnet_ip.append(get_vboxnet_ip.available_vboxnet_interfaces.pop(0))
  vbip = str(host_vboxnet_ip[-1][:-1]+str(get_vboxnet_ip.count))
  get_vboxnet_ip.count += 1
  return vbip

# This is reached when either management_ip_input number matches required ips or when internal_network is True
def set_management_ips(hosts, management_ip_input, interfaces, vboxnet_ips, internal_network):
  for node in hosts:
    if node not in interfaces.keys():
      interfaces[node] = []
  management_ip = {}
  if len(management_ip_input) >= len(hosts):
    for node in range(0, len(hosts)):
      management_ip[hosts[node]] = management_ip_input[node]
  elif len(management_ip_input) < len(hosts) and internal_network:
    vboxnet_ips, interfaces = set_vboxnet_ips(hosts, interfaces, vboxnet_ips, change_subnet=False)
    for node in hosts:
      management_ip[node] = {}
  return management_ip, vboxnet_ips, interfaces

def set_vboxnet_ips(hosts, interfaces, vboxnet_ips, change_subnet=False):
  for node in range(0, len(hosts)):
    if hosts[node] not in interfaces.keys():
      interfaces[hosts[node]] = []
    if node == 0:
      vboxip = get_vboxnet_ip(change_subnet)
    else:
      vboxip = get_vboxnet_ip()
    vboxnet_ips[hosts[node]] = vboxip
    interfaces[hosts[node]].append({'name': 'h_only', 'ip': '%s'%(vboxip), 'netmask':'%s'%('255.255.255.0'), 'host_only': True})
  return vboxnet_ips, interfaces

# setting up internal_networks
@static_var("icounter", 1)
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

@static_var("scounter", 1)
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


def insert_topo_info(template, name, hosts, host_names, flavour_dict, switches=[], management_ips={}, vboxnet_ips={}, ctrl_data_ips={}, contrail_version=None):
  topo_info = {}
  print(os.path.join(par_dir, name))
  topo_info['contrail_version'] = contrail_version
  topo_info['switches'] = switches
  topo_info['hosts'] = hosts
  topo_info['template'] = template
  topo_info['dirname'] = os.path.join(par_dir, name)
  topo_info['host_vboxnet_ip'] = host_vboxnet_ip
  topo_info['management_data'] = management_ips
  topo_info['vboxnet_interfaces'] = vboxnet_ips
  topo_info['ctrl_data_ip'] = ctrl_data_ips
  topo_info['hostnames'] = host_names
  topo_info['flavour'] = flavour_dict

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
    print("failed to create workspace")
    print(e)
    sys.exit()
  return dirname

def destroy_workspace(dirname):
  try:
    os.chdir("/root")
    shutil.rmtree(dirname)
  except Exception as e:
    print("failed to delete workspace %s"%(dirname))
    print(e)
    sys.exit()


############### topology creation and provisioning

def get_contrail_command(inputs, name, flavour, management_ip, interfaces, vm_ip):
  x = vm.CENTOS77(name, flavour, management_ip, interfaces, [\
      {'method': 'ansible', 'path': "\"%s\""%(os.path.join(ansible_scripts_path, 'ui.yml')), 'variables': {'vm_ip': vm_ip, 'contrail_version': inputs['contrail_version'], 'ntp_server': 'ntp.juniper.net', 'registry': inputs['registry'], 'vagrant_root': "%s"%os.path.join(par_dir, inputs['name'])}}, \
      {'method': 'shell', 'path': "\"%s\""%(os.path.join(ansible_scripts_path, 'scripts/docker.sh'))},
      {'method': 'file', 'source': "\"%s\""%(os.path.join(ansible_scripts_path, 'scripts/cc.sh')), 'destination': "\"/tmp/cc.sh\""},
      {'method': 'shell', 'inline': "\"chmod +x /tmp/cc.sh && /tmp/cc.sh\""}])
  return x

def three_node(inputs):
  # validate input fields
  set_defaults_three_node(inputs)
  nodes_count = 3
  nodes_count = nodes_count + inputs['additional_nodes']
  set_defaults(inputs)

  Schema({'name' : And(lambda value: validate_name(value), lambda value: validate_topology_name_creation(value)),
    'additional_nodes': And(int, int),
    Optional('management_ip'): And([And(str, lambda ip: Regex(r'^[\d]{1,3}\.[\d]{1,3}\.[\d]{1,3}\.[\d]{1,3}$').validate(ip), lambda ip: validate_managementip(ip))], lambda ip_list: len(ip_list) == len(set(ip_list)), lambda ip_list: validate_fip_count(ip_list, nodes_count, inputs['contrail_command'], inputs['internal_network'])),
    Optional('netmask') : And(str, lambda netmask: Regex(r'^[\d]{1,3}\.[\d]{1,3}\.[\d]{1,3}\.[\d]{1,3}$').validate(netmask)),
    Optional('gateway') : And(str, lambda gateway: Regex(r'^[\d]{1,3}\.[\d]{1,3}\.[\d]{1,3}\.[\d]{1,3}$').validate(gateway)),
    Optional('contrail_version'): And(str, lambda version: validate_if_contrail_image_is_present(version, inputs['registry'])),
    Optional('flavour') : And(str, lambda flavour: validate_flavour(flavour)), 
    Optional('contrail_command'): bool,
    Optional('kolla_external_vip_address'): And(str, lambda ip: Regex(r'^[\d]{1,3}\.[\d]{1,3}\.[\d]{1,3}\.[\d]{1,3}$').validate(ip)),
    Optional('additional_compute') : int,
    Optional('additional_control'): int,
    Optional('dpdk_computes'): And(int, lambda n: validate_tn_dpdk_computes(inputs,n)),
    Optional('registry'): And(str, lambda repo: validate_registry(repo)),
    Optional('openstack_version'): str,
    Optional('contrail_deployer_branch'): And(str, lambda value: validate_deployer_branch(value)),
    Optional('internal_network'): bool,
    Optional('template'): str}).validate(inputs)

  format_management_ip(inputs)
  hosts = get_keys('node', nodes_count)
  interfaces = {}
  if inputs['contrail_command']:
    hosts.append('command')
  
  management_data, vboxnet_ip, interfaces = set_management_ips(hosts[::-1], inputs['management_ip'], interfaces, {}, inputs['internal_network'])
  # add contrail_command_to_hosts
  if 'kolla_external_vip_address' in inputs.keys():
    kolla_evip = inputs['kolla_external_vip_address']
  else:
    kolla_evip = ""
    if vboxnet_ip != {}:
      kolla_evip_dict, _ = set_vboxnet_ips(['kolla-evip'], {}, {}, change_subnet=False)
      kolla_evip = kolla_evip_dict['kolla-evip']

  # control_data_ip is hostonly ip
  ctrl_data_ip, interfaces = set_vboxnet_ips(hosts, interfaces, {}, change_subnet=True)
  ctrl_data_gateway = host_vboxnet_ip[-1]

  #kolla_ivip_dict, interface_dummy = set_vboxnet_ips(['kolla-ivip'], {}, {}, change_subnet=False)
  #kolla_ivip = kolla_ivip_dict['kolla-ivip']

  host_names = get_host_names(inputs['name'], {}, hosts)
  host_instance = []
  computes_controllers = []
  release = "undefined"

  if 'contrail_version' in inputs.keys():
    contrail_version = inputs['contrail_version']
    if 'contrail_deployer_branch' not in inputs.keys():
      release, inputs['contrail_deployer_branch'] = get_contrail_deployer_branch(inputs['contrail_version'])
  image = get_centos_image(release) 

  for node in hosts:
    if node is not 'command':
      host_instance.append((node, image(host_names[node], get_flavour(inputs, "medium"), management_data[node], interfaces[node], [
                           {'method': 'ansible', 'path': "\"%s\"" % (os.path.join(ansible_scripts_path, 'base_pkgs.yml')), 'variables': {}}])))
      computes_controllers.append({'host':"{}".format(host_names[node]), 'ip': ctrl_data_ip[node], 'mip': management_ip(management_data, vboxnet_ip, node)})

  if 'contrail_version' in inputs.keys():
    primary = computes_controllers.pop()
    contrail_host = host_instance.pop()
    computes = host_instance[:(inputs['additional_compute']+2)]
    computes_ip = computes_controllers[:(inputs['additional_compute']+2)]
    #controls = host_instance[(inputs['additional_compute']+2):]
    controls_ip = computes_controllers[(inputs['additional_compute']+2):]
  # increase computes size
    for compute_node in computes:
      print(compute_node)
      compute_node[1].flavour = get_flavour(inputs, "large")
    contrail_host[1].provision.append({'method': 'ansible', 'path': "\"%s\""%(os.path.join(ansible_scripts_path, 'multinode.yml')), 'variables':{'primary':primary, 'controls': controls_ip, 'openstack_version': inputs['openstack_version'], 'computes': computes_ip, 'registry': inputs['registry'], 'ntp_server': 'ntp.juniper.net', 'kolla_evip': kolla_evip, 'ctrl_data_gateway': ctrl_data_gateway, 'contrail_version': inputs['contrail_version'], 'vagrant_root': "%s"%(os.path.join(par_dir, inputs['name'])), 'dpdk_computes':inputs['dpdk_computes'], 'contrail_deployer_branch':inputs['contrail_deployer_branch']}})
    contrail_host[1].provision.extend([{'method':'file', 'source':"\"%s\""%(os.path.join(ansible_scripts_path, "scripts/all.sh")), 'destination': "\"/tmp/all.sh\""}, {'method': 'shell', 'inline': "\"/bin/sh /tmp/all.sh\"" }])
    host_instance.append(contrail_host)

    if inputs['contrail_command']:
      host_instance.append(('command', get_contrail_command(inputs, name = host_names['command'], flavour=get_flavour(inputs, "medium"), management_ip=management_data['command'], interfaces=interfaces['command'], vm_ip=management_ip(management_data, vboxnet_ip, 'command'))))
  else:
    contrail_version = None
  flavour_dict = get_flavour_from_host_instance(host_instance)
  if not is_memory_sufficient(flavour_dict):
    sys.exit()
  dirname = create_workspace(inputs['name'])
  vm.generate_vagrant_file([node[1] for node in host_instance], [], file_name=os.path.join(dirname, "Vagrantfile"))
  insert_topo_info(inputs['template'], inputs['name'], hosts, host_names, management_ips=management_data, vboxnet_ips=vboxnet_ip, ctrl_data_ips=ctrl_data_ip, contrail_version=contrail_version, flavour_dict=flavour_dict)
  return dirname

# depends on input parameters
# 1 switch , 3 nodes topology
def three_node_vqfx(inputs):
  # validate input fields
  set_defaults_three_node(inputs)
  # number of nodes
  nodes_count = 3
  # adding additional nodes as per input file
  nodes_count = nodes_count + inputs['additional_nodes']
  set_defaults(inputs)
  
  Schema({'name' : And(lambda value: validate_name(value), lambda value: validate_topology_name_creation(value)),
    'additional_nodes': And(int, lambda n: validate_tnv_additional_nodes(inputs, n)),
    Optional('dpdk_computes'): And(int, lambda n: validate_tnv_dpdk_computes(inputs, n)),
    Optional('management_ip'): And([And(str, lambda ip: Regex(r'^[\d]{1,3}\.[\d]{1,3}\.[\d]{1,3}\.[\d]{1,3}$').validate(ip), lambda ip: validate_managementip(ip))], lambda ip_list: len(ip_list) == len(set(ip_list)), lambda ip_list: validate_fip_count(ip_list, nodes_count, inputs['contrail_command'], inputs['internal_network'])),
    Optional('netmask') : And(str, lambda netmask: Regex(r'^[\d]{1,3}\.[\d]{1,3}\.[\d]{1,3}\.[\d]{1,3}$').validate(netmask)),
    Optional('gateway') : And(str, lambda gateway: Regex(r'^[\d]{1,3}\.[\d]{1,3}\.[\d]{1,3}\.[\d]{1,3}$').validate(gateway)),
    Optional('contrail_version'): And(str, lambda version: validate_if_contrail_image_is_present(version, inputs['registry'])),
    Optional('internal_network'): bool,
    Optional('flavour') : And(str, lambda flavour: validate_flavour(flavour)),
    Optional('kolla_external_vip_address'): And(str, lambda ip: Regex(r'^[\d]{1,3}\.[\d]{1,3}\.[\d]{1,3}\.[\d]{1,3}$').validate(ip)),
    Optional('contrail_command'): bool,
    Optional('template') : str,
    Optional('registry') : And(str, lambda repo: validate_registry(repo)),
    Optional('additional_compute') : int,
    Optional('additional_control'): int,
    Optional('openstack_version'): str,
    Optional('contrail_deployer_branch'): And(str, lambda value: validate_deployer_branch(value))}).validate(inputs)

  format_management_ip(inputs)

  ctrl_data_ip = {}
  management_data = {}
  vboxnet_ip = {}
  # setting up keys for all the nodes
  hosts = get_keys('node', nodes_count)
  # setting up keys for all the switches
  switches = get_keys('switch', 1)
  # setting management ips if given for nodes and setting up vboxnet interface if there is less management ips
  interfaces = {}
  # setting up interfaces
  if inputs['contrail_command']:
    hosts.append('command')

  management_data, vboxnet_ip, interfaces = set_management_ips(hosts[::-1], inputs['management_ip'], interfaces, {}, inputs['internal_network'])
  
  if 'kolla_external_vip_address' in inputs.keys():
    kolla_evip = inputs['kolla_external_vip_address']
  else:
    kolla_evip = ""
    if vboxnet_ip != {}:
      kolla_evip_dict, _ = set_vboxnet_ips(['kolla-evip'], {}, {})
      kolla_evip = kolla_evip_dict['kolla-evip']
  # add contrail_command_to_hosts  

  ctrl_data_ip, ctrl_data_gateway, interfaces = set_up_switch_host_interfaces(interfaces, hosts, switches[0])
  #kolla_ivip = str(ctrl_data_gateway.rsplit(".", 1)[0] + "." + str(len(ctrl_data_ip)+2))
  # setting up dummy hostname //?? required??
  host_names = {}
  host_names = get_host_names(inputs['name'], host_names, hosts)
  host_names = get_host_names(inputs['name'], host_names, switches)

  switch_instance = []
  computes_controllers = []
  host_instance = []
  release = "undefined"
  
  if 'contrail_version' in inputs.keys():
    contrail_version = inputs['contrail_version']
    if 'contrail_deployer_branch' not in inputs.keys():
      release, inputs['contrail_deployer_branch'] = get_contrail_deployer_branch(inputs['contrail_version'])
  image = get_centos_image(release)  
  
  for node in hosts:
    if node is not 'command':
      host_instance.append((node, image(name=host_names[node], flavour=get_flavour(inputs, "medium"), management_ip=management_data[node], interfaces=interfaces[node], provision=[{'method': 'ansible', 'path': "\"%s\""%(os.path.join(ansible_scripts_path, 'base_pkgs.yml')), 'variables':{}}])))
      computes_controllers.append({'host':"{}".format(host_names[node]), 'ip': ctrl_data_ip[node], 'mip': management_ip(management_data, vboxnet_ip, node)})
  # take out the last node instance make it controller and install contrail with this as host
  if 'contrail_version' in inputs.keys():
    #update_kernel(release, host_instance)
    primary = computes_controllers.pop()
    contrail_host = host_instance.pop()
    computes = host_instance[:(inputs['additional_compute']+2)]
    computes_ip = computes_controllers[:(inputs['additional_compute']+2)]
    #controls = host_instance[(inputs['additional_compute']+2):]
    controls_ip = computes_controllers[(inputs['additional_compute']+2):]
    # allocate more memory for computes
    for compute_node in computes:
      print(compute_node)
      compute_node[1].flavour = get_flavour(inputs, "large")
    contrail_host[1].provision.append({'method': 'ansible', 'path': "\"%s\""%(os.path.join(ansible_scripts_path, 'multinode.yml')), 'variables':{'primary':primary, 'controls': controls_ip, 'openstack_version': inputs['openstack_version'], 'kvrouter_id': "101", 'computes': computes_ip, 'kolla_evip': kolla_evip, 'kolla_ivip': kolla_evip, 'ctrl_data_gateway': ctrl_data_gateway, 'registry': inputs['registry'], 'ntp_server': 'ntp.juniper.net', 'contrail_version': inputs['contrail_version'], 'vagrant_root': "%s"%(os.path.join(par_dir, inputs['name'])), 'dpdk_computes':inputs['dpdk_computes'], 'contrail_deployer_branch':inputs['contrail_deployer_branch']}})
    contrail_host[1].provision.extend([{'method':'file', 'source':"\"%s\""%(os.path.join(ansible_scripts_path, "scripts/all.sh")), 'destination': "\"/tmp/all.sh\""}, {'method': 'shell', 'inline': "\"/bin/sh /tmp/all.sh\"" }])
    host_instance.append(contrail_host)
    
    if inputs['contrail_command']:
      host_instance.append(('command', get_contrail_command(inputs, name = host_names['command'], flavour=get_flavour(inputs, "medium"), management_ip=management_data['command'], interfaces=interfaces['command'], vm_ip=management_ip(management_data, vboxnet_ip, 'command'))))
  
  else:
    contrail_version = None

  for switch in switches:
    switch_instance.append(vm.VQFX(host_names[switch], ctrl_data_gateway, interfaces[switch]))
  flavour_dict = get_flavour_from_host_instance(host_instance)
  if not is_memory_sufficient(flavour_dict):
    sys.exit()
  dirname = create_workspace(inputs['name'])
  vm.generate_vagrant_file([node[1] for node in host_instance], switch_instance, file_name=os.path.join(dirname, "Vagrantfile"))
  insert_topo_info(inputs['template'], inputs['name'], hosts, host_names, flavour_dict=flavour_dict, switches=switches, management_ips=management_data, vboxnet_ips=vboxnet_ip, ctrl_data_ips=ctrl_data_ip, contrail_version=contrail_version)
  return dirname

def devenv(inputs):
  # validate schema
  if 'internal_network' not in inputs.keys():
    inputs['internal_network'] = False

  Schema({'name' : And(lambda value: validate_name(value), lambda value: validate_topology_name_creation(value)),
    'branch' : And(str, lambda value: validate_devenv_branch(value)),
    Optional('management_ip') : And(str, lambda ip: Regex(r'^[\d]{1,3}\.[\d]{1,3}\.[\d]{1,3}\.[\d]{1,3}$').validate(ip), lambda ip: validate_managementip(ip)),
    Optional('netmask') : And(str, lambda netmask: Regex(r'^[\d]{1,3}\.[\d]{1,3}\.[\d]{1,3}\.[\d]{1,3}$').validate(netmask)),
    Optional('gateway') : And(str, lambda gateway: Regex(r'^[\d]{1,3}\.[\d]{1,3}\.[\d]{1,3}\.[\d]{1,3}$').validate(gateway)),
    Optional('internal_network') : bool,
    Optional('flavour') : And(str, lambda flavour: validate_flavour(flavour)),
    Optional('template') : str}).validate(inputs)
  
  format_management_ip(inputs)
  #single device
  # CENTOS(name, {management_ip}, [interfaces], [provision])
  interfaces = {}
  interfaces['node1'] = []
  management_ip, vboxnet_ip, interfaces = set_management_ips(['node1'], inputs['management_ip'], interfaces, {}, inputs['internal_network'])
  print(management_ip, interfaces)
  image = vm.CENTOS77
  if inputs['branch'][0] == 'R':
    image = get_centos_image(inputs['branch'][1:])
  s1 = image(str(inputs['name']+"-node1"), get_flavour(inputs, "large"), management_ip['node1'], interfaces['node1'], [{'method': 'ansible', 'path': "\"%s\""%(os.path.join(ansible_scripts_path, check_for_devenv_vm_init_script(inputs['branch']))), 'variables': {'branch': inputs['branch']}}])
  # no switches one server
  if not is_memory_sufficient({'node1': get_flavour(inputs, "large")}):
    sys.exit()
  dirname = create_workspace(inputs['name'])
  vm.generate_vagrant_file([s1], [], file_name=os.path.join(dirname, "Vagrantfile"))
  insert_topo_info(inputs['template'], inputs['name'], ['node1'], {'node1': str(inputs['name']+"-node1")}, flavour_dict={
                   'node1': get_flavour(inputs, "large")}, management_ips=management_ip, vboxnet_ips=vboxnet_ip, ctrl_data_ips={}, contrail_version=None)
  return dirname

def all_in_one(inputs):
  # validate schema

  set_defaults(inputs)

  if 'dpdk_compute' not in inputs.keys():
    inputs['dpdk_compute'] = False

  Schema({'name' : And(lambda value: validate_name(value), lambda value: validate_topology_name_creation(value)),
    Optional('management_ip'): And([And(str, lambda ip: Regex(r'^[\d]{1,3}\.[\d]{1,3}\.[\d]{1,3}\.[\d]{1,3}$').validate(ip), lambda ip: validate_managementip(ip))], lambda ip_list: len(ip_list) == len(set(ip_list)), lambda ip_list: validate_fip_count(ip_list, 1, inputs['contrail_command'], inputs['internal_network'])),
    Optional('netmask') : And(str, lambda netmask: Regex(r'^[\d]{1,3}\.[\d]{1,3}\.[\d]{1,3}\.[\d]{1,3}$').validate(netmask)),
    Optional('gateway') : And(str, lambda gateway: Regex(r'^[\d]{1,3}\.[\d]{1,3}\.[\d]{1,3}\.[\d]{1,3}$').validate(gateway)),
    Optional('contrail_version'): And(str, lambda version: validate_if_contrail_image_is_present(version, inputs['registry'])),
    Optional('internal_network') : bool,
    Optional('flavour') : And(str, lambda flavour: validate_flavour(flavour)),
    Optional('contrail_command'): bool,
    Optional('template') : str,
    Optional('dpdk_compute') : bool,
    Optional('registry') : And(str, lambda repo: validate_registry(repo)),
    Optional('openstack_version'): str,
    Optional('contrail_deployer_branch'): And(str, lambda value: validate_deployer_branch(value))}).validate(inputs)
  
  format_management_ip(inputs)
  
  hosts = []
  host_names = {}
  hosts = get_keys('node', 1)

  if inputs['contrail_command']:
    hosts.append('command')

  host_names = get_host_names(inputs['name'], host_names, hosts)

  host_instance = []
  # provisioning for contrail role
  #vm_ip : inputs['management_ip']['ip']
  #ntp_server :
  #contrail_version :
  #vagrant_root :
  interfaces = {}
  management_data, vboxnet_ip, interfaces = set_management_ips(hosts, inputs['management_ip'], interfaces, {}, inputs['internal_network'])
  ctrl_data_ip = {}

  release = "undefined"
  
  if 'contrail_version' in inputs.keys():
    contrail_version = inputs['contrail_version']
    if 'contrail_deployer_branch' not in inputs.keys():
      release, inputs['contrail_deployer_branch'] = get_contrail_deployer_branch(inputs['contrail_version'])
  image = get_centos_image(release) 

  for node in hosts:
    if node is not 'command':
      host_instance.append((node, image(name=host_names[node], flavour=get_flavour(inputs, "large"), management_ip=management_data[node], interfaces=interfaces[node], provision=[{'method': 'ansible', 'path': "\"%s\""%(os.path.join(ansible_scripts_path, 'base_pkgs.yml')), 'variables':{}}])))

  if 'contrail_version' in inputs.keys():
    contrail_version = inputs['contrail_version']
    if inputs['contrail_command']:
      if management_data['command'] != {}:
        command_vm_ip = management_data['command']['ip']
      if 'command' in vboxnet_ip.keys():
        command_vm_ip = vboxnet_ip['command']
    if management_data['node1'] != {}:
        vm_ip = management_data['node1']['ip']
        vm_gw = management_data['node1']['gateway']
    if 'node1' in vboxnet_ip.keys():
        vm_ip = vboxnet_ip['node1']
        vm_gw = host_vboxnet_ip[-1]
    if 'contrail_deployer_branch' not in inputs.keys():
      release, inputs['contrail_deployer_branch'] = get_contrail_deployer_branch(inputs['contrail_version'])
    host_instance[0][1].provision.extend([{'method': 'ansible', 'path': "\"%s\""%(os.path.join(ansible_scripts_path, 'all.yml')), 'variables': {'vm_ip': vm_ip, 'vm_gw': vm_gw, 'vm_name': str(inputs['name']+"-node1"), 'contrail_version': inputs['contrail_version'], 'openstack_version': inputs['openstack_version'], 'registry': inputs['registry'], 'dpdk_compute': int(inputs['dpdk_compute']), 'contrail_deployer_branch': inputs['contrail_deployer_branch'],'ntp_server': 'ntp.juniper.net', 'vagrant_root': "%s"%os.path.join(par_dir, inputs['name'])}},{'method':'file', 'source':"\"%s\""%(os.path.join(ansible_scripts_path, "scripts/all.sh")), 'destination': "\"/tmp/all.sh\""}, {'method': 'shell', 'inline': "\"/bin/sh /tmp/all.sh\""}])
  # install contrail_command when contrail command ip_address is given
    if inputs['contrail_command']:
      host_instance.append(('command', get_contrail_command(inputs, name=host_names['command'], flavour=get_flavour(inputs, "medium"), management_ip=management_data['command'], interfaces=interfaces['command'], vm_ip=command_vm_ip)))
  else:
    contrail_version = None
  flavour_dict = get_flavour_from_host_instance(host_instance)
  if not is_memory_sufficient(flavour_dict):
    sys.exit()
  dirname = create_workspace(inputs['name'])
  vm.generate_vagrant_file([node[1] for node in host_instance], [], file_name=os.path.join(dirname, "Vagrantfile"))
  insert_topo_info(inputs['template'], inputs['name'], hosts, host_names, flavour_dict=flavour_dict, management_ips=management_data, vboxnet_ips=vboxnet_ip, ctrl_data_ips=ctrl_data_ip, contrail_version=contrail_version)
  return dirname

##################### subparser functions
def mb_to_gb(value):
  return int(value/1024)

def clear_cache():
  try:
    op = subprocess.run('echo 3 > /proc/sys/vm/drop_caches',
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
  except subprocess.CalledProcessError as e:
    print("Could not clear Cache")
    print(e)
    sys.exit()
  if op.stderr:
    print("Could not clear Cache")
    sys.exit()

def get_memory_details(units):
  try:
    command = ['free']
    units = '-' + units
    command.append(units)
    op = subprocess.run(
        command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
  except subprocess.CalledProcessError as e:
    print("Error running command \"free %s\""%(units))
    print(e)
    sys.exit()
  else:
    mem_details_str = re.findall(
        r'(Mem:[\s\S]+)\nSwap', op.stdout.decode("UTF-8"))[0]
    mem_list = re.split(r'\s+',mem_details_str)
    mem_dict = {}
    #mem_dict['total'] = int(mem_list[1])
    #mem_dict['used'] = int(mem_list[2])
    #mem_dict['free'] = int(mem_list[3])
    mem_dict['available'] = int(mem_list[6])
    return mem_dict

def get_device_status(topology_name):
  if not os.path.exists(info_file):
    print("info file not found in path")
    sys.exit()
  with open(info_file, "r") as info_file_handler:
    info = json.load(info_file_handler)
  topology_name = args.topology_name
  topo_info = info[topology_name]
  hosts = topo_info['hosts']
  switches = topo_info['switches']
  dirname = topo_info['dirname']
  try:
    os.chdir(dirname)
    op = subprocess.run(
        ['vagrant', 'status'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
  except subprocess.CalledProcessError as e:
    print("vagrant status failed")
    print(e)
    sys.exit()
  else:
    node_status = {}
    for node in hosts:
      node_host_name = topo_info['hostnames'][node]
      node_status[node] = re.findall(r'{}[\s]+([\S\s]{{1,20}})[\s]+[(]virtualbox[)]'.format(node_host_name), op.stdout.decode("UTF-8"))[0]
    for switch in switches:
      switch_re_name = str(topo_info['hostnames'][switch] + '_re')
      node_status[switch] = re.findall(
          r'{}[\s]+([\S\s]{{1,20}})[\s]+[(]virtualbox[)]'.format(switch_re_name), op.stdout.decode("UTF-8"))[0]
    return node_status

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
  if instances_file_path != "DOES NOT EXIST":
    contrail_info = yaml.load(open(instances_file_path, "r"), Loader=yaml.FullLoader)
    table = PrettyTable()
    table.title = "Contrail Info"
    table.field_names = ['Fields', 'Values']
    table.add_row(["Contrail Version", contrail_info['contrail_configuration']['CONTRAIL_VERSION']])
    table.add_row(["Cloud Orchestrator", contrail_info['contrail_configuration']['CLOUD_ORCHESTRATOR']])
    if 'kolla_internal_vip_address' in contrail_info['kolla_config']['kolla_globals'].keys():
      table.add_row(["kolla_internal_vip_address", contrail_info['kolla_config']['kolla_globals']['kolla_internal_vip_address']])
    if 'kolla_external_vip_address' in contrail_info['kolla_config']['kolla_globals'].keys():
      table.add_row(["kolla_external_vip_address", contrail_info['kolla_config']['kolla_globals']['kolla_external_vip_address']])
    if 'contrail_api_interface_address' in contrail_info['kolla_config']['kolla_globals'].keys():
      table.add_row(["contrail_api_interface_address", contrail_info['kolla_config']['kolla_globals']['contrail_api_interface_address']])
    table.align["Fields"] = "l"
    table.align["Values"] = "l"
    print(table)
    print("\n")
  node_status = get_device_status(topology_name)
  for host in topo_info['hosts']:
    table = PrettyTable()
    table.title = str("NODE" + " ({})".format(node_status[host]))
    table.field_names = ['Fields', 'Values']
    table.add_row(["hostname", topo_info['hostnames'][host]])
    if 'flavour' in topo_info.keys():
      node_flavour = topo_info['flavour'][host]
      table.add_row(["vcpu", vm.flavour[node_flavour]['cpu']])
      table.add_row(["memory", str(vm.flavour[node_flavour]['memory'])+' MB'])
    if host not in topo_info['management_data'].keys() or topo_info['management_data'][host] == {}:
      table.add_row(["public ip", None])
    else:
      table.add_row(["public ip", topo_info['management_data'][host]['ip']])
      table.add_row(["netmask", topo_info['management_data'][host]['netmask']])
      table.add_row(["default gateway", topo_info['management_data'][host]['gateway']])
    if host not in topo_info['vboxnet_interfaces'].keys():
      table.add_row(["private ip", None])
    else:
      table.add_row(["private ip", topo_info['vboxnet_interfaces'][host]])
    if host not in topo_info['ctrl_data_ip'].keys():
      table.add_row(["control/data ip", None])
    else:
      table.add_row(["control/data ip", topo_info['ctrl_data_ip'][host]])
    if instances_file_path != "DOES NOT EXIST":
      contrail_info = yaml.load(open(instances_file_path, "r"), Loader=yaml.FullLoader)
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
  if 'switches' in topo_info.keys() and len(topo_info['switches']) != 0:
    for switch in topo_info['switches']:
      table = PrettyTable()
      table.title = str("SWITCH" + " ({})".format(node_status[switch]))
      table.field_names = ['Fields', 'Values']
      table.add_row(["RE name", str(topo_info['hostnames'][switch] + "_re")])
      table.add_row(["PFE name", str(topo_info['hostnames'][switch] + "_pfe")])
      table.align["Fields"] = "l"
      table.align["Values"] = "l"
      print(table)
      print("\n")

def show_resources(args):
  clear_cache()
  mem_details = get_memory_details('g')
  mem_table = PrettyTable(['Memory', 'Value in (GB)'])
  for key, value in mem_details.items():
    mem_table.add_row([key,value])
  print(mem_table)
  if not os.path.exists(info_file):
    print("info file not found in path")
    sys.exit()
  with open(info_file, "r") as info_file_handler:
    info = json.load(info_file_handler)
  table = PrettyTable(['Topology Name', 'Memory Used in (GB)'])
  for name, item in info.items():
    row = []
    row.append(name)
    total_memory = 0
    if 'flavour' in item.keys():
      for node in item['flavour']:
        flavour = item['flavour'][node]
        total_memory = total_memory + mb_to_gb(vm.flavour[flavour]['memory'])
    else:
      total_memory = None
    row.append(total_memory)
    table.add_row(row)
  print(table)

def poweron(args):
  vagrant_up(topology_name=args.topology_name)

def poweroff(args):
  vagrant_halt_command = ["vagrant", "halt"]
  topology_name = args.topology_name
  with open(info_file, "r") as info_file_handler:
    info = json.load(info_file_handler)
  topo_info = info[topology_name]
  dirname = topo_info['dirname']
  try:
    os.chdir(dirname)
  except Exception as e:
    print("cannot change directory to %s" % dirname)
    print(e)
    sys.exit()
  else:
    print(os.getcwd())
    if not os.path.exists(os.path.join(os.getcwd(), "Vagrantfile")):
      print("Vagrantfile does not exist in directory %s" % os.getcwd())
      sys.exit()
    try:
      op = subprocess.run(vagrant_halt_command,
                          stdout=sys.stdout, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as e:
      print("Could not run vagrant halt command")
      print(e)
      sys.exit()
    else:
      print("Virtual machines are halted")
     
def list_vm(args):
  if args.resources:
    show_resources(args)
    sys.exit()
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
  destroy_topo = input("Do you want to destroy the topology? (y or n)")
  if destroy_topo.lower() != "y":
    if destroy_topo.lower() != "n":
      print("Invalid input")
      sys.exit()
    else:
      sys.exit()
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
    print("vagrant destroy failed")
    print(e)
    sys.exit()
  if topo_info['host_vboxnet_ip'] != []:
    for honly_interface in topo_info['host_vboxnet_ip']:
      try:
        op = subprocess.run(vbox_list_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
      except subprocess.CalledProcessError as e:
        print("vboxmanage list hostonlyifs failed")
        print(e)
        sys.exit()
      else:
        print("vboxnet ip associated with the topology is %s"%honly_interface)
        vboxnet_ip = re.findall(r'Name:\s+(vboxnet\d)[\s\S]{{1,100}}IPAddress:\s+{}'.format(honly_interface), op.stdout.decode("UTF-8"))
        if vboxnet_ip == []:
          print("vboxnet interface name not found for ip address {} on host".format(honly_interface))
        else:
          vbox_remove_command_exec = vbox_remove_command[:]
          vbox_remove_command_exec.append(vboxnet_ip[0])
          try:
            op1 = subprocess.run(vbox_remove_command_exec, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
          except subprocess.CalledProcessError as e:
            print("Could not delete hostonly interface on the host machine")
            print(e)
            sys.exit()
  info = json.load(open(info_file, "r"))
  del info[args.topology_name]
  json.dump(info, open(info_file, "w"))
  print("destroy workspace")
  destroy_workspace(dirname)
  return

def rebuild(args):
  vagrant_destroy_command = ["vagrant", "destroy", "-f"]
  topology_name = args.topology_name
  with open(info_file, "r") as info_file_handler:
    info = json.load(info_file_handler)
  topo_info = info[topology_name]
  dirname = topo_info['dirname']
  try:
    os.chdir(dirname)
  except Exception as e:
    print("cannot change directory to %s"%dirname)
    print(e)
    sys.exit()
  else:
    print(os.getcwd())
    if not os.path.exists(os.path.join(os.getcwd(), "Vagrantfile")):
      print("Vagrantfile does not exist in directory %s"%os.getcwd())
      sys.exit()
    try:
      op = subprocess.run(vagrant_destroy_command, stdout=sys.stdout, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as e:
      print("Could not run vagrant destroy command")
      print(e)
      sys.exit()
    else:
      vagrant_up(dirname=dirname)

def vagrant_up(dirname="", topology_name=""):
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
    print("cannot change directory to %s"%dirname)
    print(e)
    sys.exit()
  else:
    print(os.getcwd())
    if not os.path.exists(os.path.join(os.getcwd(), "Vagrantfile")):
      print("Vagrantfile does not exist in directory %s"%os.getcwd()) 
      sys.exit()
    try:
      op = subprocess.run(vagrant_up_command, stdout=sys.stdout, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as e:
      print("Could not run vagrant up command")
      print(e)
      sys.exit()
  print("Virtual machines are up")

################ main function

if __name__ == '__main__':
  init(autoreset=True)
  global parser
  parser = argparse.ArgumentParser()
  subparser = parser.add_subparsers(dest='command')
  create_topology = subparser.add_parser("create", help="create vagrant file and bring up topology")
  retry_topology = subparser.add_parser("rebuild", help="retry building topology")
  list_topology = subparser.add_parser("list", help="list topology details")
  show_topology = subparser.add_parser("show", help="show individual topology details")
  delete_topology = subparser.add_parser("destroy", help="delete topology")
  poweron_topology = subparser.add_parser("poweron", help="power on all machines of given topology")
  poweroff_topology = subparser.add_parser("poweroff", help="power off all machines of given topology")
  # create topology has mandatory file name as argument
  create_topology.add_argument("file_name", help="path to the config file", type=lambda x: validate_file(x))

  retry_topology.add_argument("topology_name", help="name of the topology to be rebuilt", type=lambda x: validate_topology_name_deletion(x))
  # list global i.e., for all keys
  show_topology.add_argument("topology_name", help="name of the topology", type=lambda x: validate_topology_name_deletion(x))
  # destroy vm 
  delete_topology.add_argument("topology_name", help="name of the topology to be destroyed", type=lambda x: validate_topology_name_deletion(x))

  list_topology.add_argument("--resources", help="list available resources",
                             action="store_true", default=False)

  poweron_topology.add_argument("topology_name", help="name of the topology to be powered on",
                                type=lambda x: validate_topology_name_deletion(x))

  poweroff_topology.add_argument(
      "topology_name", help="name of the topology to be powered off", type=lambda x: validate_topology_name_deletion(x))
  

  args = parser.parse_args()
  #print(args)
  if args.command == "list":
    list_vm(args)
  elif args.command == None:
    parser.print_help()
  else:
    globals()[args.command](args)

