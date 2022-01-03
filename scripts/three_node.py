from base_template import BasicTopology
from colorama import Fore, init
import json
import os
import re
import sys
import subprocess
import yaml
import requests
from prettytable import PrettyTable
import vm_models as vm
import vagrant_wrappers as vagrant
from provisioners import Basepkgs, ThreeNodeContrail, ContrailCommand
from interface_handler import HostOnlyIfsHandler, VboxIp


class ThreeNode(BasicTopology):
    def __init__(self, input_params):
        self.dpdk_compute = input_params.get('dpdk_computes', 0)
        self.contrail_command = input_params.get('contrail_command', False)
        self.openstack_version = input_params.get('openstack_version', 'queens')
        self.contrail_version = input_params.get('contrail_version', 'None')
        self.registry = input_params.get('registry', 'svl-artifactory')
        self.additional_compute = input_params.get('additional_compute',0)
        self.additional_control = input_params.get('additional_control',0)
        self.flavour = input_params.get('flavour', 'medium')
        self.kolla_external_vip_address = input_params.get('kolla_external_vip_address', [])
        self.total_nodes = 3 + self.additional_compute + self.additional_control + int(self.contrail_command)
        self.total_compute = 2 + self.additional_compute
        self.total_control = 1 + self.additional_control
        self.huge_pages = vm.flavour[self.flavour]['hugepages']
        self.compute_info = []
        self.control_info = []
        self.primary_control = None
        
        input_params['total_nodes'] = self.total_nodes
        super().__init__(
            "three_node",
            input_params,
            self.total_nodes,
            self.contrail_version)

    def validate_fields(self):
        if self.dpdk_compute <= self.total_compute and \
           self.validate_kolla_external_vip_address() and \
           super().validate_fields():
            return True
        else:
            return False
        
    def validate_kolla_external_vip_address(self):
        if self.total_control > 1 :
            if self.is_management_internal:
                return True
        if not isinstance(self.kolla_external_vip_address, list):
            print(Fore.RED + "Note:" + Fore.WHITE +
                  "IP address given should be in list")
            return False
        if 'kolla_external_vip_address' not in  self.input_params.keys():
            print(Fore.RED + "Note:" + Fore.WHITE +
                  "Kolla external_vip_address is present in the input file")
            return False
        if 'kolla_external_vip_address' in self.input_params.keys(): 
            if not re.match(
                r'^[\d]{1,3}\.[\d]{1,3}\.[\d]{1,3}\.[\d]{1,3}$',
                    self.kolla_external_vip_address[0]):
                print(Fore.RED + "Note:" + Fore.WHITE +
                      "IP address is not in proper format")
                return False
            ping_test = ["ping", "-q", "-c", "1"]
            ping_test.append(self.kolla_external_vip_address[0])
            op = subprocess.run(
                ping_test, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if op.stderr:
                print(Fore.RED + "Note:" + Fore.WHITE +
                      "IP address error for %s" % (self.kolla_external_vip_address[0]))
                return False
            packet_loss = re.findall(
                r"(\d{1,3}\.*\d*)% packet loss", op.stdout.decode("UTF-8"))
            if float(packet_loss[0]) != 100.0:
                print(Fore.RED + "Note:" + Fore.WHITE +
                      "%s is reachable" % (self.kolla_external_vip_address[0]))
                return False
        return True 
              
    def get_contrail_deployer_branch(self):
        contrail_list_branch_api = "https://api.github.com/repos/Juniper/contrail-ansible-deployer/branches"  # noqa
        tf_list_branch_api = "https://api.github.com/repos/tungstenfabric/tf-ansible-deployer/branches"  # noqa
        branches_info = requests.get(
                        contrail_list_branch_api).json() + requests.get(
                        tf_list_branch_api).json()
        branches_info.reverse()
        all_branches = {}
        for branch in branches_info:
            branch_name = branch['name']
            if branch_name[0] == "R":
                branch_name = branch_name[1:]
            all_branches[str(branch_name)] = branch['name']
        for branch in all_branches.keys():
            if branch in self.contrail_version:
                print("checking out {} branch in \
                    contrail ansible deployer".format(
                        all_branches[branch]))
                return all_branches[branch]
        print("No matching version found \n checking out {} branch \
            in contrail ansible deployer".format("master"))
        return "master"   
            
    def provision_contrail(self):
        if self.contrail_version:
            if self.contrail_command:
                command_node = self.hosts[-1]
                ContrailCommand().provision(command_node,
                                            self.contrail_version,
                                            self.registry)
            ThreeNodeContrail().provision(
                            self.primary_control, self.contrail_version,
                            self.openstack_version, self.registry,
                            self.dpdk_compute,
                            self.get_contrail_deployer_branch(),self.compute_info,self.control_info, self.kolla_external_vip_address,self.huge_pages)   
    
    def get_control_compute_info(self):
        import pdb; pdb.set_trace()
        self.compute_info = self.get_contrail_ip_info(0,self.total_compute)
        self.control_info = self.get_contrail_ip_info(self.total_compute, (self.total_compute + self.total_control - 1))
        self.primary_control = self.hosts[self.total_compute + self.total_control -1]
        self.kolla_external_vip_address = HostOnlyIfsHandler.get_next_ip(self.primary_control.get_gw_by_name('mgmt'))
        
    def get_contrail_ip_info(self,start,end):
        host_list = []
        for host in self.hosts[start:end]:
            host_info_dict = {}
            host_info_dict['host'] = host.get_name()
            host_info_dict['ip'] = host.get_ip_by_name('control_data')
            host_info_dict['mip'] = host.get_ip_by_name('mgmt')
            host_list.append(host_info_dict) 
        return host_list    
                   
    @classmethod
    def show(cls, topo_info):
        dirname = topo_info['dirname']
        instances_file_path = os.path.join(dirname, "config/instances.yaml")
        if not os.path.exists(instances_file_path):
            instances_file_path = "DOES NOT EXIST"
        if instances_file_path != "DOES NOT EXIST":
            contrail_info = yaml.load(
                    open(instances_file_path, "r"), Loader=yaml.FullLoader)
            table = PrettyTable()
            table.title = "Contrail Info"
            table.field_names = ['Fields', 'Values']
            table.add_row(
               ["Contrail Version",
                contrail_info['contrail_configuration']['CONTRAIL_VERSION']])
            table.add_row(
               ["Cloud Orchestrator",
                contrail_info['contrail_configuration']['CLOUD_ORCHESTRATOR']])
            if 'kolla_internal_vip_address' in contrail_info['kolla_config']['kolla_globals'].keys():     # noqa
                table.add_row(
                    ["kolla_internal_vip_address",
                     contrail_info['kolla_config']
                     ['kolla_globals']['kolla_internal_vip_address']])
            if 'kolla_external_vip_address' in contrail_info['kolla_config']['kolla_globals'].keys():     # noqa
                table.add_row(
                    ["kolla_external_vip_address",
                     contrail_info['kolla_config']
                     ['kolla_globals']['kolla_external_vip_address']])
            if 'contrail_api_interface_address' in contrail_info['kolla_config']['kolla_globals'].keys():     # noqa
                table.add_row(
                    ["contrail_api_interface_address",
                     contrail_info['kolla_config']
                     ['kolla_globals']['contrail_api_interface_address']])
            table.align["Fields"] = "l"
            table.align["Values"] = "l"
            print(table)
            print("\n")
        node_status = cls.get_node_status(topo_info)
        for host in topo_info['hosts']:
            table = PrettyTable()
            table.title = str("NODE" + " ({})".format(node_status[host]))
            table.field_names = ['Fields', 'Values']
            table.add_row(["hostname", host])
            if 'flavour' in topo_info.keys():
                node_flavour = topo_info['flavour'][host]
                table.add_row(
                    ["vcpu", vm.flavour[node_flavour]['cpu']])
                table.add_row(
                    ["memory", str(vm.flavour[node_flavour]['memory'])+' MB'])
            if host not in topo_info['management_data'].keys() or topo_info['management_data'][host] == {}:   # noqa
                table.add_row(["public ip", None])
            else:
                table.add_row(
                    ["public ip", topo_info['management_data'][host]['ip']])
                table.add_row(
                    ["netmask", topo_info['management_data'][host]['netmask']])
                table.add_row(
                    ["default gateway",
                     topo_info['management_data'][host]['gateway']])
            if host not in topo_info['vboxnet_interfaces'].keys():
                table.add_row(["private ip", None])
            else:
                table.add_row(
                    ["private ip", topo_info['vboxnet_interfaces'][host]])
            if host not in topo_info['ctrl_data_ip'].keys():
                table.add_row(["control/data ip", None])
            else:
                table.add_row(
                    ["control/data ip", topo_info['ctrl_data_ip'][host]])
            if instances_file_path != "DOES NOT EXIST":
                contrail_info = yaml.load(
                    open(instances_file_path, "r"), Loader=yaml.FullLoader)
                if host in contrail_info['instances'].keys():
                    table.add_row(["roles", ""])
                    ins = contrail_info['instances'][host]
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
                table.title = str(
                    "SWITCH" + " ({})".format(node_status[switch]))
                table.field_names = ['Fields', 'Values']
                table.add_row(["RE name", str(switch + "_re")])
                table.add_row(["PFE name", str(switch + "_pfe")])
                table.align["Fields"] = "l"
                table.align["Values"] = "l"
                print(table)
                print("\n")
                          
    def set_ctrl_data_ips(self):
        self.set_hostonly_ips('control_data')

    def bring_up_topo(self):
        self.validate_fields()
        self.set_host_names()
        self.set_management_ips()
        self.set_ctrl_data_ips()
        self.get_control_compute_info()
        self.provision_contrail()
        dirname = self.create_topo()
        vagrant.Vagrant.vagrant_up(dirname)
