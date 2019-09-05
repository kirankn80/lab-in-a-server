import argparse
import os
import yaml
import json
import random
import datetime
import pprint
import sys
from static_variables import resolve_static
from schema import *
import vm_models as vm

# append timestamp as suffix so that internal_network interface names are unique across
unique_suffix = str(datetime.datetime.now().strftime("_%Y%m%d%m%s"))

# function validating the existance of file
def validate_file(parser, file_name):
  if not os.path.exists(file_name):
    parser.error("File %s not found in the path"%(file_name))
  else:
    return file_name

def parse_input_file(file_name):
  valid_templates = ['devenv', 'all_in_one', 'three_node_vqfx', 'three_node']
  inputs = Schema({'template' : And(str, lambda name: name in valid_templates), Optional(str) : object }).validate(yaml.load(open(file_name, "r"), Loader = yaml.FullLoader))
  return inputs

def validate_name(name):
  Regex('^[a-zA-Z][a-zA-Z0-9-]+[a-zA-Z]$').validate(name)

# returns list of ip address belonging to same /24 subnet 
@resolve_static(static_variables={'octet3': 1})
def get_ctrl_data_ip(num):
  ctrl_data_subnet = { 'octet1': '192', 'octet2': '168'}
  ctrl_data_ip = []
  #ctrl_data_subnet['octet3'] = str(random.randrange(0,255))
  for octet4 in range(2, num+2):
    ctrl_data_ip.append(str(ctrl_data_subnet['octet1']+'.'+ctrl_data_subnet['octet2']+'.'+str(octet3)+'.'+str(octet4)))
  octet3 += 1
  return ctrl_data_ip

# to be replaced
def get_hostonly_ip():
  file = "/Users/aprathik/host_only_ip.json"
  vbnet = {}
  if not os.path.exists(file):
    print("Host only ip file not found in path")
    sys.exit()
  with open(file, "r") as host_only_ip:
    ip =json.load(host_only_ip)
    vbnet['oct1'] = ip['octet1']
    vbnet['oct2'] = ip['octet2']
    vbnet['oct3'] = ip['octet3']
    vbnet['oct4'] = ip['octet4']
    vbnet['netmask'] = ip['subnet']
    if int(ip['octet4']) < 254:
      ip['octet4'] = str(int(ip['octet4'])+1)
    elif int(ip['octet3']) == 254 and int(ip['octet4']) == 254:
      ip['octet3'] = str(2)
      ip['octet4'] = str(2)
    else:
      ip['octet3'] = str(int(ip['octet3'])+1)
      ip['octet4'] = str(2)
    json.dump(ip, open(file, "w"))
    return vbnet

def get_keys(prefix, num):
  list = []
  for i in range(1, num+1):
    list.append(prefix+str(i))
  return list

def set_model(dict, keys, value):
  for key in keys:
    dict[key] = value
  return dict

# assign one management ip to each host and {} when given number of management ip is less
def set_management_ips(hosts, management_ip_input):
  management_ip = {}
  for node in range(0,min(len(management_ip_input),len(hosts))):
    management_ip[hosts[node]] = management_ip_input[node]
  if len(management_ip_input)< len(hosts):
    for node in range(len(management_ip_input), len(hosts)):
      management_ip[hosts[node]] = {}
  return management_ip

def set_vboxnet_ips(hosts, interfaces):
  for node in range(0,len(hosts)):
    if hosts[node] in interfaces.keys():
      interfaces[hosts[node]].append({'name': 'h_only','ip': '%s'%(get_hostonly_ip()),'netmask':'%s'%('255.255.255.0'),'host_only': True})
    else:
      interfaces[hosts[node]] = []
      interfaces[hosts[node]].append({'name': 'h_only','ip': '%s'%(get_hostonly_ip()),'netmask':'%s'%('255.255.255.0'),'host_only': True})
  return interfaces

# can be removed 
def get_host_names(name, dict, list):
  for element in list:
    dict[element] = str(name+'-'+element)
  return dict

# setting up internal_networks
@resolve_static(static_variables={'icounter': 1})
def set_up_switch_host_interfaces(interfaces, hosts, switch, ctrl_data):
  if switch not in interfaces.keys():
    interfaces[switch] = []
  for i in range(0, len(hosts)):
    if hosts[i] not in interfaces:
      interfaces[hosts[i]] = []
    interfaces[hosts[i]].append({'name': str('i'+str(icounter)+unique_suffix), 'ip': ctrl_data[i], 'netmask':'255.255.255.0', 'host_only': False})
    interfaces[switch].append(str('i'+str(icounter)+unique_suffix))
    icounter += 1
  return interfaces 

@resolve_static(static_variables={'scounter': 1})
def set_up_switch_switch_interfaces(interfaces, switch1, switch2):
  if switch1 not in interfaces.keys():
    interfaces[switch1] = []
  if switch2 not in interfaces.keys():
    interfaces[switch2] = []
  interface = str('s'+str(scounter)+unique_suffix)
  interfaces[switch1].append(interface)
  interfaces[switch2].append(interface)
  scounter +=1
  return interfaces

def three_node(inputs):
  nodes_count = 3
  nodes_count = nodes_count + inputs['additional_nodes']
  hosts = get_keys('node',nodes_count)
  model = {}
  model = set_model(model, hosts, 'CENTOS')
  management_data = set_management_ips(hosts, inputs['management_ips'])
  interfaces = {}
  interfaces = set_vboxnet_ips(hosts, interfaces)
  host_names = get_host_names(inputs['name'], host_names, hosts)
  for node in hosts:
    host_instance.append(vm.CENTOS(host_names[node], management_data[node], interfaces[node], []))
  vm.generate_vagrant_file(host_instance, switch_instance)


# depends on input parameters
# 1 switch , 3 nodes topology
def three_node_vqfx(inputs):
  # number of switches in a three node topology
  switch_count = 1
  # number of nodes 
  nodes_count = 3
  # adding additional nodes as per input file
  nodes_count = nodes_count + inputs['additional_nodes']
  # getting control-data ip address for all the nodes
  ctrl_data_ip = get_ctrl_data_ip(nodes_count)
  # setting up keys for all the nodes
  hosts = get_keys('node',nodes_count)
  # setting up keys for all the switches
  switches = get_keys('switch', switch_count)
  # setting up the base box
  model = {}
  model = set_model(model, hosts,'CENTOS')
  model = set_model(model, switches,'VQFX')
  # setting management ips if given for nodes and setting up vboxnet interface if there is less management ips
  interfaces = {}
  management_data = set_management_ips(hosts, inputs['management_ips'])
  # setting up dummy hostname //?? required??
  host_names = {}
  host_names = get_host_names(inputs['name'], host_names, hosts)
  host_names = get_host_names(inputs['name'], host_names, switches)
  # setting up interfaces
  interfaces = set_up_switch_host_interfaces(interfaces, hosts, switches[0], ctrl_data_ip)
  host_instance = []
  switch_instance = []

  for node in hosts:
    host_instance.append(vm.CENTOS(host_names[node], management_data[node], interfaces[node], []))
  for switch in switches:
    switch_instance.append(vm.VQFX(host_names[switch], interfaces[switch]))

  vm.generate_vagrant_file(host_instance, switch_instance)

  pprint.pprint(interfaces) 
  pprint.pprint(hosts)
  pprint.pprint(model) 
  pprint.pprint(host_names)
  pprint.pprint(management_data)



def devenv(inputs):
  # validate schema 
  Schema({'name' : And(str, lambda value: Regex('^[a-zA-Z][a-zA-Z0-9-]+[a-zA-Z0-9]$').validate(value)),\
   'management_ip' : \
   {'ip' : And(str, lambda ip: Regex('^[0-9]+.[0-9]+.[0-9]+.[0-9]+$').validate(ip)), \
   'netmask' : And(str, lambda netmask: Regex('^[0-9]+.[0-9]+.[0-9]+.[0-9]+$').validate(netmask)), \
   'gateway' : And(str, lambda gateway: Regex('^^[0-9]+.[0-9]+.[0-9]+.[0-9]+$').validate(gateway))}, \
   Optional(str) : object}).validate(inputs)
  #single device
  # CENTOS(name, {management_ip}, [interfaces], [provision])
  s1 = vm.CENTOS(inputs['name'], {}, [{'name':'i2','ip':'192.168.3.2','netmask':'255.255.255.0','host_only':True }], [{'method': 'ansible', 'path': 'dev-lite.yml', 'variables': {}}])
  # no switches one server
  vm.generate_vagrant_file([s1], [])

def all_in_one(inputs):
  # validate schema
  hosts = []
  Schema({'name' : And(str, lambda value: Regex('^[a-zA-Z][a-zA-Z0-9-]+[a-zA-Z0-9]$').validate(value)),\
    'management_ip' : \
    {'ip' : And(str, lambda ip: Regex('^[0-9]+.[0-9]+.[0-9]+.[0-9]+$').validate(ip)), \
    'netmask' : And(str, lambda netmask: Regex('^[0-9]+.[0-9]+.[0-9]+.[0-9]+$').validate(netmask)), \
    'gateway' : And(str, lambda gateway: Regex('^^[0-9]+.[0-9]+.[0-9]+.[0-9]+$').validate(gateway))}, \
    'contrail_version': str, Optional(str) : object}).validate(inputs)
  if 'contrail_command_ip' in inputs.keys():
    hosts.append(vm.CENTOS(inputs['name'], inputs['contrail_command_ip'], {}, []))

  #single node
  # provisioning for contrail role 
  #vm_ip : inputs['management_ip']['ip']
  #ntp_server : 
  #contrail_version :
  #vagrant_root :
  hosts.append(vm.CENTOS(inputs['name'], inputs['management_ip'], {}, [{'method': 'ansible', 'path': 'all.yml', 'variables': {'vm_ip': inputs['management_ip']['ip'], 'contrail_version': inputs['contrail_version'], 'ntp_server': 'ntp.juniper.net', 'vagrant_root': 'vagrant_root'}}]))
  vm.generate_vagrant_file(hosts, [])



  











if __name__ == '__main__':
  parser = argparse.ArgumentParser()
  parser.add_argument("-f", "--file_name", required = True, help = "path to the config file", type = lambda x: validate_file(parser,x))
  args = parser.parse_args()
  input_vars = parse_input_file(args.file_name)
  pprint.pprint(input_vars)
  print(globals())
  config = globals()[input_vars['template']](input_vars)



