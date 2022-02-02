import os
import yaml
import requests
from prettytable import PrettyTable
from . import vm_models as vm
from . import vagrant_wrappers as vagrant
from .base_template import BasicTopology
from .provisioners import AllInOneContrail, ContrailCommand


class AllInOne(BasicTopology):
    def __init__(self, input_params):
        self.dpdk_compute = input_params.get('dpdk_compute', 0)
        self.contrail_command = input_params.get('contrail_command', False)
        self.openstack_version = input_params.get(
                                'openstack_version', 'queens')
        self.contrail_version = input_params.get('contrail_version', 'None')
        self.registry = input_params.get('registry', 'svl-artifactory')
        self.total_nodes = 1 + int(self.contrail_command)
        self.command_node = None
        input_params['total_nodes'] = self.total_nodes
        super().__init__(
            "all_in_one",
            input_params,
            self.total_nodes,
            self.contrail_version)

    def validate_fields(self):
        if self.dpdk_compute <= 1 and \
         super().validate_fields():
            return True
        else:
            return False

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
                return branch, all_branches[branch]
        print("No matching version found \n checking out {} branch \
            in contrail ansible deployer".format("master"))
        return("master", "master")

    def provision_contrail(self):
        if self.contrail_version:
            if self.contrail_command:
                command_node = self.hosts[-1]  
                ContrailCommand().provision(command_node,
                                            self.contrail_version,
                                            self.registry)
            AllInOneContrail().provision(
                               self.hosts[0], self.contrail_version,
                               self.openstack_version, self.registry,
                               self.dpdk_compute,
                               self.get_contrail_deployer_branch()[1])

    @classmethod
    def show(cls, topo_info):
        dirname = topo_info['dirname']
        instances_file_path = os.path.join(dirname, "config/instances.yaml")
        if not os.path.exists(instances_file_path):
            instances_file_path = "DOES NOT EXIST"
        # import pdb; pdb.set_trace()
        if instances_file_path != "DOES NOT EXIST":
            contrail_info = yaml.load(
                    open(instances_file_path, "r"), Loader=yaml.FullLoader)
            table = PrettyTable()
            table.title = "Contrail Info"
            table.field_names = ['Fields', 'Values']
            table.add_row(["Contrail Version", contrail_info['contrail_configuration']['CONTRAIL_VERSION']])
            table.add_row(["Cloud Orchestrator", contrail_info['contrail_configuration']['CLOUD_ORCHESTRATOR']])
            if 'kolla_internal_vip_address' in contrail_info['kolla_config']['kolla_globals'].keys():     # noqa
                table.add_row(["kolla_internal_vip_address", contrail_info['kolla_config']['kolla_globals']['kolla_internal_vip_address']])
            if 'kolla_external_vip_address' in contrail_info['kolla_config']['kolla_globals'].keys():     # noqa
                table.add_row(["kolla_external_vip_address", contrail_info['kolla_config']['kolla_globals']['kolla_external_vip_address']])
            if 'contrail_api_interface_address' in contrail_info['kolla_config']['kolla_globals'].keys():     # noqa
                table.add_row(["contrail_api_interface_address",contrail_info['kolla_config']['kolla_globals']['contrail_api_interface_address']])
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
                table.add_row(["vcpu", vm.flavour[node_flavour]['cpu']])
                table.add_row(["memory", str(vm.flavour[node_flavour]['memory'])+' MB'])
                
            if host not in topo_info['management_data'].keys() or topo_info['management_data'][host] == {}:   # noqa
                table.add_row(["public ip", None])
            else:
                table.add_row(["public ip", topo_info['management_data'][host]['ip']])
                table.add_row(["netmask", topo_info['management_data'][host]['netmask']])
                table.add_row(["default gateway",topo_info['management_data'][host]['gateway']])
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
                if host in contrail_info['instances'].keys():
                    table.add_row(["roles", ""])
                    ins = contrail_info['instances'][host]
                    for role in ins['roles'].keys():
                        table.add_row(["", role])
                else:
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

    def bring_up_topo(self):
        self.validate_fields()
        self.set_host_names()
        self.set_management_ips()
        self.provision_contrail()
        dirname = self.create_topo()
        vagrant.Vagrant.vagrant_up(dirname)
