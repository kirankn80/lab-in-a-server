from abc import abstractmethod
from colorama import Fore
import datetime
import os
import re
import subprocess
import sys
import vm_models as vm
import contents as db
from contents import Contents
import vagrant_wrappers as vagrant
from interface_handler import HostOnlyIfsHandler, VboxIp, InternalNetwork, VboxIPSwitch


class BasicTopology():
    os_version_map = {

        'centos-7.5': vm.CENTOS75,
        'centos-7.7': vm.CENTOS77,
        'centos-7.8': vm.CENTOS77,
        'centos-8.2': vm.CENTOS77,
        'ubuntu-20.04': vm.UBUNTU_20_04,
        'default': vm.CENTOS77
    }
    
    switch_map = {
        
        'default': vm.VQFX
    }

    unique_suffix = str(datetime.datetime.now().strftime("_%Y%m%d%m%s"))

    def __init__(self, template_name, input_vars, total_nodes, topo_info):
        self.name = input_vars.get('name', None)
        self.template_name = template_name
        self.input_vars = input_vars
        self.creation_date = str(
            datetime.datetime.now().strftime("%d %b, %Y"))
        self.ip_address_list = input_vars.get('management_ip', [])
        self.management_gateway = input_vars.get('gateway', None)
        self.netmask = input_vars.get('netmask', None)
        self.is_management_internal = input_vars.get('internal_network', False)
        self.flavour = input_vars.get('flavour', 'medium')
        self.os_version = input_vars.get('os_version', 'default')
        self.switch_type = input_vars.get('switch_type','default')
        self.switch = input_vars.get('switch', 1)
        self.contrail_command = input_vars.get('contrail_command', False)
        self.hosts = []
        self.switches = []
        # one liner info either devenv version or contrail version
        self.topo_info = topo_info
        self.total_nodes = total_nodes

    def validate_fields(self):
        if self.validate_name() and \
                self.validate_all_managementip() and \
                self.validate_os_version() and \
                self.validate_flavour() and \
                self.validate_netmask_gateway():
            print("all fields validated")
            return True
        else:
            sys.exit()

    def validate_name(self):
        if not re.match(r'^[a-zA-Z][a-zA-Z0-9-]*[a-zA-Z0-9]$', self.name):
            print(Fore.RED + "Note: " + Fore.WHITE +
                  "Name field can have letters, numbers and hyphen")
            return False
        if db.Contents.check_if_topo_exists(self.name):
            print(Fore.RED + "Note: " + Fore.WHITE +
                  "Topology exists with name %s" % (self.name))
            return False
        return True

    def validate_netmask_gateway(self):
        if self.netmask is not None and self.management_gateway is not None:
            if not re.match(
                r'^[\d]{1,3}\.[\d]{1,3}\.[\d]{1,3}\.[\d]{1,3}$',
                    self.netmask):
                print(Fore.RED + "Note:" + Fore.WHITE + "Invalid netmask.")
                return False
            if not re.match(
                r'^[\d]{1,3}\.[\d]{1,3}\.[\d]{1,3}\.[\d]{1,3}$',
                    self.management_gateway):
                print(Fore.RED + "Note:" + Fore.WHITE + "Invalid gateway.")
                return False
        return True

    def validate_all_managementip(self):
        if self.is_management_internal:
            return True
        if not isinstance(self.ip_address_list, list):
            print(Fore.RED + "Note:" + Fore.WHITE +
                  "IP address given should be in list")
            return False
        if len(self.ip_address_list) != self.total_nodes:
            print(Fore.RED + "Note:" + Fore.WHITE +
                  "Number or IP address given does not match the requirement")
            return False
        if len(self.ip_address_list) != len(set(self.ip_address_list)):
            print(Fore.RED + "Note:" + Fore.WHITE +
                  "IP address given should be unique")
            return False
        for ip_address in self.ip_address_list:
            if not re.match(
                r'^[\d]{1,3}\.[\d]{1,3}\.[\d]{1,3}\.[\d]{1,3}$',
                    ip_address):
                print(Fore.RED + "Note:" + Fore.WHITE +
                      "IP address is not in proper format")
                return False
            ping_test = ["ping", "-q", "-c", "1"]
            ping_test.append(ip_address)
            op = subprocess.run(
                ping_test, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if op.stderr:
                print(Fore.RED + "Note:" + Fore.WHITE +
                      "IP address error for %s" % (ip_address))
                return False
            packet_loss = re.findall(
                r"(\d{1,3}\.*\d*)% packet loss", op.stdout.decode("UTF-8"))
            if float(packet_loss[0]) != 100.0:
                print(Fore.RED + "Note:" + Fore.WHITE +
                      "%s is reachable" % (ip_address))
                return False
        return True

    def validate_os_version(self):
        if self.os_version in self.os_version_map.keys() or None:
            return True
        print(Fore.RED + "Note:" + Fore.WHITE +
              "Invalid Centos version. Available versions \
                - {}".format(self.os_version_map.keys()))
        return False

    def validate_flavour(self):
        if self.flavour is not None \
                and self.flavour not in vm.flavour.keys():
            print(Fore.RED + "Note:" + Fore.WHITE +
                  "Invalid Flavour. Available Falvours - \
                    {}".format(vm.flavour.keys()))
            return False
        return True

    # This is reached when either management_ip_input number matches
    # required ips or when internal_network is True
    def set_floating_ips(self):
        if self.netmask is not None and self.management_gateway is not None:
            # import pdb; pdb.set_trace()
            for node in self.hosts:
                node.set_management_ip(VboxIp(ip=self.ip_address_list.pop(),
                                              gateway=self.management_gateway,
                                              intf_type='bridge',
                                              netmask=self.netmask,
                                              name='mgmt').get_ip_dict())
        else:
            print(Fore.RED + "Note:" + Fore.WHITE +
                  "Please specify netmask and gateway fields")
            sys.exit()
        return

    def set_hostonly_ips(self, name):
        gateway = HostOnlyIfsHandler.vboxnet_get_hostonly_subnet()
        for node in self.hosts:
            node.add_interface(VboxIp
                               (ip=HostOnlyIfsHandler.get_next_ip(gateway),
                                gateway=gateway,
                                intf_type='host_only',
                                name=name).get_ip_dict())

    def set_host_names(self):
        for node in range(1, self.total_nodes + 1):
            self.hosts.append(self.os_version_map[
                self.os_version](
                    name=str(self.name + '-node' + str(node)),
                    flavour=self.flavour,
                    is_management_internal=self.is_management_internal))
        return
    
    def set_switch_names(self):
         for switch in range(1, self.switch + 1):
             self.switches.append(self.switch_map[
                self.switch_type](
                    name=str(self.name + '-switch' + str(switch)),
                    gateway= InternalNetwork.get_ctrl_subnet()))
         return
   
    def set_switch_host_interfaces(self,unique_name,node,switch):
        gateway = InternalNetwork.get_ctrl_subnet()
        ip = InternalNetwork.get_next_ip(gateway)
        intf_dict1 = VboxIp(ip = ip, gateway=gateway, unique_name = unique_name, name ='control_data').get_ip_dict()
        node.add_interface(intf_dict1)
        switch.add_interface(VboxIpSwitch(unique_name).get_ip_dict())
        
    def set_management_ips(self):
        if self.is_management_internal:
            self.set_hostonly_ips('mgmt')
        else:
            self.set_floating_ips()

    @abstractmethod
    def bring_up_topo(self):
        '''implemented in each topo'''

    @classmethod
    @abstractmethod
    def show(cls):
        '''implemented in each topo'''

    def create_topo(self):
        if not self.is_memory_sufficient():
            sys.exit()
        dirname = vagrant.Vagrant.create_workspace(self.name)
        # import pdb; pdb.set_trace()
        vm.generate_vagrant_file(
            self.hosts,
            self.switches,
            file_name=os.path.join(dirname, 'Vagrantfile'))
        Contents.insert(self.template_name, self.os_version, self.name,
                        self.hosts, self.switches,
                        self.is_management_internal, dirname, self.topo_info)
        return dirname

    def is_memory_sufficient(self):
        vagrant.Vagrant.clear_cache()
        mem_info = vagrant.Vagrant.get_available_memory_details('m')
        required_memory = self.total_nodes * vm.flavour[self.flavour]['memory']
        if (mem_info['available'] - required_memory) > 10240:
            return True
        else:
            print("Free memory is %d GB\n Memory required \
                is %d GB\n Spinning up the topology will cause \
                    the host machine to have memory %d GB\n Aborting \
                        due to shortage of memory \n" % (
                self.mb_to_gb(mem_info['available']),
                self.mb_to_gb(required_memory),
                self.mb_to_gb((
                    mem_info['available'] -
                    required_memory))))
            return False

    def mb_to_gb(self, value):
        return int(value / 1024)

    @classmethod
    def get_node_status(cls, topo_info):
        op = vagrant.Vagrant.vagrant_status(topo_info.get('dirname'))
        node_status = {}
        for node in topo_info['hosts']:
            node_status[node] = re.findall(
              r'{}[\s]+([\S\s]{{1,20}})[\s]+[(]virtualbox[)]'.format(node),
              op)[0]
        for switch in topo_info['switches']:
            switch_re_name = str(switch + '_re')
            node_status[switch] = re.findall(
              r'{}[\s]+([\S\s]{{1,20}})[\s]+[(]virtualbox[)]'
              .format(switch_re_name), op)[0]
        return node_status
