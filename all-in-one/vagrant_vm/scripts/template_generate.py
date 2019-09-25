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
from colorama import Fore, init
import subprocess
from schema import *
import vm_models as vm

############# global vars
par_dir = "/Users/aprathik/vm-spinner"

host_vboxnet_ip = ""

info_file = "/Users/aprathik/vm-spinner/change_file/vminfo.json"
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

def set_model(dict, keys, value):
  for key in keys:
    dict[key] = value
  return dict

def get_host_names(name, dict, list):
  for element in list:
    dict[element] = str(name+'-'+element)
  return dict

############# validation functions

def validate_name(name):
  return Regex('^[a-zA-Z][a-zA-Z0-9-]+[a-zA-Z0-9]$').validate(name)

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
    print("info file not found in path")
    return False
  with open(info_file, "r") as info_file_handler:
    info = json.load(info_file_handler)
  if name in info.keys():
    return False 
  return True

def validate_topology_name_deletion(name):
  if not os.path.exists(info_file):
    print("info file not found in path")
    parser.error("File %s not found in the path"%(info_file))
  with open(info_file, "r") as info_file_handler:
    info = json.load(info_file_handler)
  if name not in info.keys():
    parser.error("topology with name %s does not exist\n Check topology name"%(name)) 
  return name

def validate_topology_name_view(name):
  if not os.path.exists(info_file):
    print("info file not found in path")
    parser.error("File %s not found in the path"%(info_file))
  with open(info_file, "r") as info_file_handler:
    info = json.load(info_file_handler)
  print(name)
  if name != "all" and name not in info.keys():
    parser.error("topology with name %s does not exist\n Check topology name"%(name)) 
  return name

def parse_input_file(file_name):
  valid_templates = ['devenv', 'all_in_one', 'three_node_vqfx', 'three_node']
  inputs = Schema({'template' : And(str, lambda name: name in valid_templates), Optional(str) : object }).validate(yaml.load(open(file_name, "r"), Loader = yaml.FullLoader))
  return inputs

def validate_flavour(flavour):
  if flavour in vm.flavour.keys():
    return True
  parser.error("Flavour %s does not exist"%(flavour))

def validate_tnv_additional_nodes(inputs,n):
  if 'contrail_command_ip' in inputs.keys() and 'contrail_version' in inputs.keys():
    if n < 2:
      return True
    parser.error(Fore.RED + "Total number of nodes connected to switch cannot exceed 5")
  else:
    if n < 3:
      return True
    parser.error(Fore.RED + "Total number of nodes connected to switch cannot exceed 5")

def validate_tnv_dpdk_computes(inputs,n):
  an = inputs['additional_nodes']
  if n <= (2 + an):
    return True
  return parser.error("Total number of dpdk computes cannot be greater than {}".format(an+2))

def validate_contrail_command(inputs,command_ip):
  if 'contrail_version' in inputs.keys():
    return True
  parser.error("contrail version is to be specified")

def validate_tnv_inputs(inputs):
  if 'additional_nodes' not in inputs.keys():
    inputs['additional_nodes'] = 0
  if 'dpdk_computes' not in inputs.keys():
    inputs['dpdk_computes'] = 0

  """Schema({'name' : And(str, lambda value: Regex('^[a-zA-Z][a-zA-Z0-9-]+[a-zA-Z0-9]$').validate(value)),\
    'additional_nodes': And(int,lambda n: validate_tnv_additional_nodes(inputs,n)),
    'dpdk_computes': And(int, lambda n: validate_tnv_dpdk_computes(inputs,n)),
    Optional('management_ip'): \
    [{'ip' : And(str, lambda ip: validate_managementip(ip)), \
    'netmask' : And(str, lambda netmask: Regex('^[\d]{1,3}\.[\d]{1,3}\.[\d]{1,3}\.[\d]{1,3}$').validate(netmask)), \
    'gateway' : And(str, lambda gateway: Regex('^[\d]{1,3}\.[\d]{1,3}\.[\d]{1,3}\.[\d]{1,3}$').validate(gateway))}], \
    Optional('contrail_version'): str, 
    Optional('internal_network'): bool,
    Optional('flavour') : And(str, lambda flavour: validate_flavour(flavour)), \
    Optional('contrail_command_ip'): \
    And({'ip' : And(str, lambda ip: validate_managementip(ip)), \
    'netmask' : And(str, lambda netmask: Regex('^[\d]{1,3}\.[\d]{1,3}\.[\d]{1,3}\.[\d]{1,3}$').validate(netmask)), \
    'gateway' : And(str, lambda gateway: Regex('^[\d]{1,3}\.[\d]{1,3}\.[\d]{1,3}\.[\d]{1,3}$').validate(gateway))}, lambda x: validate_contrail_command(inputs,x)),
    Optional(str) : object}).validate(inputs)"""
  print(inputs)
  return inputs

def set_defaults(inputs):
  if 'internal_network' not in inputs.keys():
    inputs['internal_network'] = 0

  if 'management_ip' not in inputs.keys():
    inputs['management_ip'] = []

  if 'management_ip' in inputs.keys() and len(inputs['management_ip']) == 1:
    inputs['management_ip'] = [inputs['management_ip']]

  if 'flavour' not in inputs.keys():
    inputs['flavour'] = "small"

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
def insert_topo_info(name, hosts, host_names, management_ips = {}, vboxnet_ips = {}, ctrl_data_ips = {}):
  topo_info = {}
  print(os.path.join(par_dir, name))
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

def get_contrail_command(inputs,name,flavour,management_ip,interfaces):
  x = vm.CENTOS(name, flavour,management_ip, interfaces, [\
      {'method': 'ansible', 'path': 'ui.yml', 'variables': {'vm_ip': inputs['contrail_command_ip']['ip'], 'contrail_version': inputs['contrail_version'], 'ntp_server': 'ntp.juniper.net', 'vagrant_root': "%s"%os.path.join(par_dir,inputs['name'])}}, \
      {'method': 'shell', 'path': "\"/root/lab-in-a-server/all-in-one/vagrant_vm/ansible/scripts/docker.sh\""},
      {'method': 'file', 'source': "\"/root/lab-in-a-server/all-in-one/vagrant_vm/ansible/scripts/cc.sh\"", 'destination': "\"/tmp/cc.sh\""},
      {'method': 'shell', 'inline': "\"chmod +x /tmp/cc.sh && /tmp/cc.sh\""}])
  return x

def three_node(inputs):
  # validate input fields
  """Schema({'name' : And(str, lambda value: Regex('^[a-zA-Z][a-zA-Z0-9-]+[a-zA-Z0-9]$').validate(value)),\
    'additional_nodes': And(int, lambda n: n < 3),
    'management_ip' : \
    [{'ip' : And(str, lambda ip: validate_managementip(ip)), \
    'netmask' : And(str, lambda netmask: Regex('^[\d]{1,3}\.[\d]{1,3}\.[\d]{1,3}\.[\d]{1,3}$').validate(netmask)), \
    'gateway' : And(str, lambda gateway: Regex('^[\d]{1,3}\.[\d]{1,3}\.[\d]{1,3}\.[\d]{1,3}$').validate(gateway))}], \
    'contrail_version': str, 
    Optional('flavour') : And(str, lambda flavour: validate_flavour(flavour)), \
    Optional('contrail_command_ip'): \
    {'ip' : And(str, lambda ip: validate_managementip(ip)), \
    'netmask' : And(str, lambda netmask: Regex('^[\d]{1,3}\.[\d]{1,3}\.[\d]{1,3}\.[\d]{1,3}$').validate(netmask)), \
    'gateway' : And(str, lambda gateway: Regex('^[\d]{1,3}\.[\d]{1,3}\.[\d]{1,3}\.[\d]{1,3}$').validate(gateway))},
    Optional(str) : object}).validate(inputs)"""
  
  set_defaults(inputs)

  nodes_count = 3
  nodes_count = nodes_count + inputs['additional_nodes']
  hosts = get_keys('node',nodes_count)
  model = {}
  model = set_model(model, hosts, 'CENTOS')
  interfaces = {}
  management_data, vboxnet_ip, interfaces = set_management_ips(hosts, inputs['management_ip'], interfaces, {}, inputs['internal_network'])
  # add contrail_command_to_hosts
  if 'contrail_command_ip' in inputs.keys():
    hosts.append('command')
  # control_data_ip is hostonly ip
  ctrl_data_ip, interfaces = set_vboxnet_ips(hosts, interfaces, {})
  host_names = get_host_names(inputs['name'], {}, hosts)
  host_instance = []
  computes = []
  for node in hosts:
    if node is not 'command':
      host_instance.append(vm.CENTOS(host_names[node], inputs['flavour'], management_data[node], interfaces[node], [{'method': 'ansible', 'path': 'base_pkgs.yml', 'variables':{}}]))
      computes.append({'host':"{}".format(host_names[node]), 'ip': ctrl_data_ip[node]})

  if 'contrail_version' in inputs.keys():
    primary = computes.pop()
    contrail_host = host_instance.pop()
    contrail_host.flavour = "small"
    contrail_host.provision.append({'method': 'ansible', 'path': 'multinode.yml', 'variables':{'controller':primary, 'computes': computes, 'ntp_server': 'ntp.juniper.net', 'contrail_version': inputs['contrail_version'], 'vagrant_root': "%s"%(os.path.join(par_dir,inputs['name'])), 'dpdk_computes':inputs['dpdk_computes']}})
    contrail_host.provision.extend([{'method':'file', 'source':"\"/root/lab-in-a-server/all-in-one/vagrant_vm/ansible/scripts/all.sh\"", 'destination': "\"/tmp/all.sh\""},{'method': 'shell', 'inline': "\"/bin/sh /tmp/all.sh\"" }])
    host_instance.append(contrail_host)


  if 'contrail_command_ip' in inputs.keys():
    hosts.append(get_contrail_command(inputs))
  dirname = create_workspace(inputs['name'])
  vm.generate_vagrant_file(host_instance, [], file_name=os.path.join(dirname,"Vagrantfile"))
  insert_topo_info(inputs['name'], hosts, host_names, management_ips = management_data, vboxnet_ips = vboxnet_ip, ctrl_data_ips = ctrl_data_ip)
  return dirname

# depends on input parameters
# 1 switch , 3 nodes topology
def three_node_vqfx(inputs):
  # validate input fields
  inputs = validate_tnv_inputs(inputs)
  
  ctrl_data_ip = {}
  management_data = {}
  vboxnet_ips = {}

  set_defaults(inputs)
  # number of nodes 
  nodes_count = 3
  # adding additional nodes as per input file
  nodes_count = nodes_count + inputs['additional_nodes']
  # setting up keys for all the nodes
  hosts = get_keys('node',nodes_count)
  # setting up keys for all the switches
  switches = get_keys('switch', 1)
  # add contrail_command_to_hosts
  # setting up the base box
  model = {}
  model = set_model(model, hosts,'CENTOS')
  model = set_model(model, switches,'VQFX')
  # setting management ips if given for nodes and setting up vboxnet interface if there is less management ips
  interfaces = {}
  # setting up interfaces
  management_data, vboxnet_ip, interfaces = set_management_ips(hosts, inputs['management_ip'], interfaces, {}, inputs['internal_network'])
  if 'contrail_command_ip' in inputs.keys():
    hosts.append('command')
  ctrl_data_ip, gateway, interfaces = set_up_switch_host_interfaces(interfaces, hosts, switches[0])
  # setting up dummy hostname //?? required??
  host_names = {}
  host_names = get_host_names(inputs['name'], host_names, hosts)
  host_names = get_host_names(inputs['name'], host_names, switches)
  switch_instance = []
  computes = []
  host_instance = []
  for node in hosts:
    if node is not 'command':
      host_instance.append(vm.CENTOS(name=host_names[node], flavour=inputs['flavour'], management_ip=management_data[node], interfaces=interfaces[node], provision=[{'method': 'ansible', 'path': 'base_pkgs.yml', 'variables':{}}]))
      computes.append({'host':"{}".format(host_names[node]), 'ip': ctrl_data_ip[node]})
  # take out the last node instance make it controller and install contrail with this as host
  if 'contrail_version' in inputs.keys():
    primary = computes.pop()
    contrail_host = host_instance.pop()
    contrail_host.flavour = "small"
    contrail_host.provision.append({'method': 'ansible', 'path': 'multinode.yml', 'variables':{'controller':primary, 'computes': computes, 'ntp_server': 'ntp.juniper.net', 'contrail_version': inputs['contrail_version'], 'vagrant_root': "%s"%(os.path.join(par_dir,inputs['name'])), 'dpdk_computes':inputs['dpdk_computes']}})
    contrail_host.provision.extend([{'method':'file', 'source':"\"/root/lab-in-a-server/all-in-one/vagrant_vm/ansible/scripts/all.sh\"", 'destination': "\"/tmp/all.sh\""},{'method': 'shell', 'inline': "\"/bin/sh /tmp/all.sh\"" }])
    host_instance.append(contrail_host)

  if 'contrail_command_ip' in inputs.keys():
    host_instance.append(get_contrail_command(inputs,name = host_names['command'], flavour="low", management_ip=inputs['contrail_command_ip'], interfaces=interfaces['command']))

  for switch in switches:
    switch_instance.append(vm.VQFX(host_names[switch], gateway, interfaces[switch]))

  dirname = create_workspace(inputs['name'])
  vm.generate_vagrant_file(host_instance, switch_instance, file_name=os.path.join(dirname,"Vagrantfile"))
  insert_topo_info(inputs['name'], hosts, host_names, management_ips = management_data, vboxnet_ips = vboxnet_ip, ctrl_data_ips = ctrl_data_ip)
  pprint.pprint(interfaces) 
  pprint.pprint(hosts)
  pprint.pprint(model) 
  pprint.pprint(host_names)
  pprint.pprint(management_data)
  return dirname



def devenv(inputs):
  # validate schema 
  Schema({'name' : And(lambda value: validate_name(value), lambda value: validate_topology_name_creation(value)),\
   Optional('management_ip') : \
   {'ip' : And(str, lambda ip: validate_managementip(ip)), \
   'netmask' : And(str, lambda netmask: Regex('^[\d]{1,3}\.[\d]{1,3}\.[\d]{1,3}\.[\d]{1,3}$').validate(netmask)), \
   'gateway' : And(str, lambda gateway: Regex('^[\d]{1,3}\.[\d]{1,3}\.[\d]{1,3}\.[\d]{1,3}$').validate(gateway))}, \
   Optional('internal_network') : bool, \
   Optional(str) : object}).validate(inputs)
  
  set_defaults(inputs)
  #single device
  # CENTOS(name, {management_ip}, [interfaces], [provision])
  interfaces = {}
  interfaces['node1'] = []
  management_ip, vboxnet_ip, interfaces = set_management_ips(['node1'], inputs['management_ip'], interfaces, {}, inputs['internal_network'])
  print(management_ip, interfaces)
  s1 = vm.CENTOS(str(inputs['name']+"-devenv"), "large", management_ip['node1'], interfaces['node1'], [{'method': 'ansible', 'path': 'dev-lite.yml', 'variables': {}}])
  # no switches one server
  dirname = create_workspace(inputs['name'])
  vm.generate_vagrant_file([s1], [], file_name=os.path.join(dirname,"Vagrantfile"))
  insert_topo_info(inputs['name'], ['node1'], {'node1': str(inputs['name']+"-devenv")}, management_ips = management_ip, vboxnet_ips = vboxnet_ip, ctrl_data_ips = {})
  return dirname

def all_in_one(inputs):
  # validate schema
  hosts = []
  Schema({'name' : And(lambda value: validate_name(value), lambda value: validate_topology_name_creation(value)),\
    Optional('management_ip') : \
    {'ip' : And(str, lambda ip: validate_managementip(ip)), \
    'netmask' : And(str, lambda netmask: Regex('^[\d]{1,3}\.[\d]{1,3}\.[\d]{1,3}\.[\d]{1,3}$').validate(netmask)), \
    'gateway' : And(str, lambda gateway: Regex('^[\d]{1,3}\.[\d]{1,3}\.[\d]{1,3}\.[\d]{1,3}$').validate(gateway))}, \
    Optional('contrail_version'): str, \
    Optional('internal_network') : bool, \
    Optional('flavour') : And(str, lambda flavour: validate_flavour(flavour)), \
    Optional('contrail_command_ip'): \
    {'ip' : And(str, lambda ip: validate_managementip(ip)), \
    'netmask' : And(str, lambda netmask: Regex('^[\d]{1,3}\.[\d]{1,3}\.[\d]{1,3}\.[\d]{1,3}$').validate(netmask)), \
    'gateway' : And(str, lambda gateway: Regex('^[\d]{1,3}\.[\d]{1,3}\.[\d]{1,3}\.[\d]{1,3}$').validate(gateway))}, \
    Optional(str) : object}).validate(inputs)

  set_defaults(inputs)
  # provisioning for contrail role 
  #vm_ip : inputs['management_ip']['ip']
  #ntp_server : 
  #contrail_version :
  #vagrant_root :
  interfaces = {}
  interfaces['node1'] = []
  management_ip, vboxnet_ip, interfaces = set_management_ips(['node1'], inputs['management_ip'], interfaces, {}, inputs['internal_network'])
  if 'contrail_version' in inputs.keys():
    if inputs['management_ip'] != []:
      vm_ip = management_ip['node1']['ip']
    else:
      vm_ip = vboxnet_ip['node1']
    hosts.append(vm.CENTOS(str(inputs['name']+"-aio"), inputs['flavour'], management_ip['node1'], interfaces['node1'], [{'method': 'ansible', 'path': 'all.yml', 'variables': {'vm_ip': vm_ip, 'contrail_version': inputs['contrail_version'], 'ntp_server': 'ntp.juniper.net', 'vagrant_root': "%s"%os.path.join(par_dir,inputs['name'])}},{'method':'file', 'source':"\"/root/lab-in-a-server/all-in-one/vagrant_vm/ansible/scripts/all.sh\"", 'destination': "\"/tmp/all.sh\""}, {'method': 'shell', 'inline': "\"/bin/sh /tmp/all.sh\""}]))
  # install contrail_command when contrail command ip_address is given
    if 'contrail_command_ip' in inputs.keys():
      hosts.append(get_contrail_command(inputs,name=str(inputs['name']+"-command"),flavour="low", management_ip=inputs['contrail_command_ip'], interfaces=[]))
  else:
    hosts.append(vm.CENTOS(str(inputs['name']+"-aio"), inputs['flavour'], management_ip['node1'], interfaces['node1'], [{'method': 'ansible', 'path': 'setup.yml', 'variables': {}}]))
  dirname = create_workspace(inputs['name'])
  vm.generate_vagrant_file(hosts, [], file_name=os.path.join(dirname,"Vagrantfile"))
  insert_topo_info(inputs['name'], ['node1'], {'node1': str(inputs['name']+"-aio")}, management_ips = management_ip, vboxnet_ips = vboxnet_ip, ctrl_data_ips = {})
  return dirname

##################### subparser functions

def print_info(args, topology_name, topo_info):
  all_args = 0
  if not (args.publicip or args.hostnames or args.privateip or args.ctrldataip or args.dirname):
    all_args = 1
  if args.publicip or all_args:
    print(Fore.BLUE + "public ip:")
    for k,v in topo_info['management_data'].items():
      print(Fore.GREEN + "%s : "%(topo_info['hostnames'][k])+ Fore.WHITE + "%s"%(v))
  if args.hostnames or all_args:
    print(Fore.BLUE + "hostname:")
    for k,v in topo_info['hostnames'].items():
      print(Fore.GREEN + "%s"%(v))
  if args.privateip or all_args:
    print(Fore.BLUE + "private ip:")
    for k,v in topo_info['vboxnet_interfaces'].items():
      print(Fore.GREEN + "%s : "%(topo_info['hostnames'][k])+ Fore.WHITE + "%s"%(v))
  if args.ctrldataip or all_args:
    print(Fore.BLUE + "control data interfaces:")
    for k,v in topo_info['ctrl_data_ip'].items():
      print(Fore.GREEN + "%s : "%(topo_info['hostnames'][k])+ Fore.WHITE + "%s"%(v))
  if args.dirname or all_args:
    print(Fore.BLUE + "working directory:")
    print(Fore.GREEN + topology_name + " : "+Fore.WHITE+topo_info['dirname'])
  

def create(args):
  input_vars = parse_input_file(args.file_name)
  dir_name = globals()[input_vars['template']](input_vars)
  vagrant_up(dir_name)

def view(args):
  topology_name = args.topology_name
  if not os.path.exists(info_file):
    print("info file not found in path")
    sys.exit()
  with open(info_file, "r") as info_file_handler:
    info = json.load(info_file_handler)
  if topology_name != "all" and topology_name not in info.keys():
    print("topology %s not found"%(topology_name))
    sys.exit()
  if topology_name != "all":
    print(Fore.CYAN + "%s"%topology_name)
    topo_info = info[topology_name]
    #print(topo_info)
    print_info(args,topology_name, topo_info)
  if topology_name == "all":
    for k,v in info.items():
      print(Fore.RED +"topology name: " + Fore.WHITE + "%s"%k)
      print_info(args,k,v)

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
  list_topology = subparser.add_parser("view", help = "list topology details")
  delete_topology = subparser.add_parser("destroy", help = "delete topology")
  # create topology has mandatory file name as argument
  create_topology.add_argument("file_name", help = "path to the config file", type = lambda x: validate_file(x))
  # list global i.e., for all keys
  list_topology.add_argument("topology_name", help = "name of the topology or \"all\" for global status ", type = lambda x: validate_topology_name_view(x))
  # list management ips
  list_topology.add_argument("--publicip", help = "list management ip", action = "store_true")
  # list  host_names
  list_topology.add_argument("--hostnames", help = "list nodes in topology", action = "store_true")
  # list  vboxnets
  list_topology.add_argument("--privateip", help = "list all virtualbox networks", action = "store_true")
  # list  ctrl_data_ips
  list_topology.add_argument("--ctrldataip", help = "list all control data interfaces", action = "store_true")
  # list dirname
  list_topology.add_argument("--dirname", help = "directory where the topology is present", action = "store_true")
  # destroy vm 
  delete_topology.add_argument("topology_name", help = "name of the topology to be destroyed",  type = lambda x: validate_topology_name_deletion(x))
  
  args = parser.parse_args()
  print(args)
  #print(args.command)
  globals()[args.command](args)
  #input_vars = parse_input_file(args.file_name)
  #pprint.pprint(input_vars)
  #print(globals())
  #config = globals()[input_vars['template']](input_vars)
  #three_node({'name':'abc', 'management_ips':{}, 'additional_nodes':0})
  #print(globals())

