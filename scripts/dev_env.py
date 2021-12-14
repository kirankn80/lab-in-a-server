from base_template import BasicTopology
from colorama import Fore, init
import json
import os
import sys
import yaml
import requests
from prettytable import PrettyTable
import vm_models as vm
import vagrant_wrappers as vagrant
from provisioners import Basepkgs, DevEnvContrail, ContrailCommand


class DevEnv(BasicTopology):
    def __init__(self, input_params):
        self.branch = input_params.get('branch', None)
        self.registry = input_params.get('registry', 'svl-artifactory')
        self.internal_network = input_params.get('internal_network', False)
        self.total_nodes = 1
        input_params['total_nodes'] = self.total_nodes
        super().__init__("devenv", input_params, self.total_nodes, self.branch)

    def validate_fields(self):
        if self.branch and \
                super().validate_fields():
            return True

    def validate_devenv_branch(self):
        contrail_list_branch_api = "https://api.github.com/repos/Juniper/contrail-vnc/branches?per_page=1000"   # noqa
        tf_list_branch_api = "https://api.github.com/repos/tungstenfabric/tf-vnc/branches?per_page=1000"        # noqa
        branches_info = requests.get(contrail_list_branch_api).json(
        ) + requests.get(tf_list_branch_api).json()
        all_branches = []
        for branches in branches_info:
            all_branches.append(branches['name'])
        if self.branch in all_branches:
            return True
        else:
            print(Fore.RED + "Note: " + Fore.WHITE +
                  "The branch name can be one among - ")
            print(all_branches)
            return False

    def provision_contrail(self):
        if self.branch:
            # command_node = self.hosts[-1]
            # ContrailCommand().provision(command_node,
            #                             self.branch,
            #                             self.registry)
            # Basepkgs().provision(self.hosts[0])
            if self.os_version != "ubuntu-20.04":
                DevEnvContrail().provision(self.hosts[0], self.branch)

    @classmethod
    def show(cls, topo_info):
        dirname = topo_info['dirname']
        node_status = cls.get_node_status(topo_info)
        for host in topo_info['hosts']:
            table = PrettyTable()
            table.title = str("NODE" + " ({})".format(node_status[host]))
            table.field_names = ['Fields', 'Values']
            table.add_row(["hostname", host])
            if 'os_version' in topo_info.keys():
                node_os_version = topo_info['os_version']
                table.add_row(["os_version", node_os_version])
            if 'flavour' in topo_info.keys():
                node_flavour = topo_info['flavour'][host]
                table.add_row(["vcpu", vm.flavour[node_flavour]['cpu']])
                table.add_row(
                    ["memory",
                     str(vm.flavour[node_flavour]['memory']) + ' MB'])
            if host not in topo_info['management_data'].keys(
            ) or topo_info['management_data'][host] == {}:
                table.add_row(["public ip", None])
            else:
                table.add_row(["public ip",
                               topo_info['management_data'][host]['ip']])
                table.add_row(
                    ["netmask", topo_info['management_data'][host]['netmask']])
                table.add_row(["default gateway",
                               topo_info['management_data'][host]['gateway']])
            if host not in topo_info['vboxnet_interfaces'].keys():
                table.add_row(["private ip", None])
            else:
                table.add_row(["private ip",
                               topo_info['vboxnet_interfaces'][host]])
            table.align["Fields"] = "l"
            table.align["Values"] = "l"
            print(table)
            print("\n")

    def bring_up_topo(self):
        self.validate_fields()
        self.set_host_names()
        self.set_management_ips()
        self.provision_contrail()
        dirname = self.create_topo()
        vagrant.Vagrant.vagrant_up(dirname)
