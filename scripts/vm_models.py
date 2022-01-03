from abc import ABC
from enum import Enum
import os

ansible_scripts_path = "LAB_IN_A_SERVER_ANSIBLE_SCRIPTS_PATH"
par_dir = "VAGRANT_MACHINES_FOLDER_PATH"

flavour = {
  'xlarge': {'memory': 65536, 'cpu': 8, 'hugepages': '64000'},
  'large': {'memory': 32768, 'cpu': 16, 'hugepages': '32000'},
  'medium': {'memory': 32768, 'cpu': 4, 'hugepages': '32000'},
  'small': {'memory': 8192, 'cpu': 2, 'hugepages': '16000'},
  'tiny': {'memory': 8192, 'cpu': 2, 'hugepages': '16000'}
}


class Server():

    def __init__(self, name, flavour, is_management_internal, os_version):
        self.name = name
        self.flavour = flavour
        self.is_management_internal = is_management_internal
        self.os_version = os_version
        self.interfaces = []
        self.management_ip = {}
        self.provision = []

    def get_config(self):
        config = self.set_initialconfig()
        config = self.set_managementip(config)
        config = self.set_interfaces(config)
        config = self.set_ssh_password(config)
        config = self.provision_vm(config)
        config = self.set_endblock(config)
        return config

    def set_initialconfig(self, config, box):
        config = config + """
    srv_name = (\"{}\").to_sym
    config.vm.define srv_name do |srv|
      srv.vm.box = \"{}\"
      if Vagrant.has_plugin?("vagrant-vbguest")
        srv.vbguest.auto_update = false
      end
      srv.vm.hostname = \"{}\"
      srv.vm.provider "virtualbox" do |v|
        v.memory = {}
        v.cpus = {}
      end""".format(
          self.name, box, self.name,
          flavour[self.flavour]['memory'],
          flavour[self.flavour]['cpu'])
        return config

    def set_endblock(self, config):
        config = config + """
    end"""
        '''config.vm.provider :virtualbox do |vb|
      vb.auto_nat_dns_proxy = false
      vb.customize [\"modifyvm\",
      :{}, \"--memory\", \"{}\", \"--cpus\", \"{}\"]
    end """.format(self.name,
    flavour[self.flavour]['memory'], flavour[self.flavour]['cpu'])'''
        return config

    def set_ssh_password(self, config):
        config = config + """
      srv.vm.provision :ansible do |ansible|
        ansible.playbook = \"%s\"
      end""" % (os.path.join(ansible_scripts_path, 'setup.yml'))

        return config

    def provision_vm(self, config):
        for item in self.provision:
            if item['method'] == 'ansible':
                print(item)

                config = config + """
        srv.vm.provision :%s do |ansible|
        ansible.playbook = %s""" % (item['method'], item['path'])
                if item['variables']:
                    config = config + """
        ansible.extra_vars = {"""
                    for key, value in item['variables'].items():
                        if isinstance(value, str):
                            config = config + """
          {}: \"{}\",""".format(key, value)
                        else:
                            config = config + """
          {}: {},""".format(key, value)
                    config = config + """
        }"""
                config = config + """
      end"""
            else:
                param = """
      srv.vm.provision \"%s\", """ % (item['method'])
                for key, value in item.items():
                    if key != 'method':
                        param = param + """{}: {}, """.format(key, value)
                config = config + param[:-2]
        return config

    def get_ip_by_name(self, name):
        ip = None
        for intf in self.interfaces:
            if intf.get('name',None) == name:
                ip = intf.get('ip', None)
                break
        if self.management_ip.get('name',None) == name:
            ip = self.management_ip.get('ip', None)
        return ip

    def get_gw_by_name(self, name):
        gw = None
        for intf in self.interfaces:
            if intf.get('name', None) == name:
                gw = intf.get('gateway', None)
                break
        if self.management_ip.get('name', None) == name:
            gw = self.management_ip.get('gateway', None)
        return gw     
    def set_provisioner_list(self, provisioner_list):
        self.provision = provisioner_list

    def set_management_ip(self, management_ip_dict):
        self.management_ip = management_ip_dict

    def set_interface_list(self, interfaces_list):
        self.interfaces = interfaces_list

    def get_interface_list(self):
        return self.interfaces

    def add_interface(self, intf_dict):
        self.interfaces.append(intf_dict)

    def set_flavour(self, flavour):
        self.flavour = flavour

    def set_is_management_internal(self, value):
        self.is_management_internal = value

    def get_name(self):
        return self.name

    def get_topo_name(self):
        return self.name.split('-node')[0]

    def add_provisioner(self, provisioner_dict):
        self.provision.append(provisioner_dict)


class CENTOS(Server):

    def set_managementip(self, config):
        if not self.is_management_internal:
            config = config + """
        srv.vm.network \"public_network\", auto_config: false, bridge: \'eno1\'
        srv.vm.provision :ansible do |ansible|
          ansible.playbook = \"%s\"
          ansible.extra_vars = {
            vm_interface: \"eth1\",
            vm_gateway_ip: \"%s\",
            vm_ip: \"%s\",
            vm_netmask: \"%s\",
            vm_dns1: \"172.21.200.60\",
            vm_dns2: \"8.8.8.8\",
            vm_domain: \"englab.juniper.net jnpr.net juniper.net\",
            ntp_server: \"ntp.juniper.net\"
          }
        end
        srv.vm.provision \"shell\", path: \"%s\"""" % (
             os.path.join(ansible_scripts_path, 'network.yml'),
             self.management_ip['gateway'], self.management_ip['ip'],
             self.management_ip['netmask'],
             os.path.join(ansible_scripts_path, 'scripts/set-centos-gw.sh'))
        return config

    def set_interfaces(self, config):
        if self.management_ip:
            ifcount = 2
        else:
            ifcount = 1
        for interface in self.interfaces:
            print(interface)
            if interface['host_only']:
                config = config + """
      srv.vm.network \'private_network\', ip: \"%s\", netmask: \"%s\", nic_type: \'82540EM\'""" % (interface['ip'], interface['netmask'])
            else:
                config = config + """
      srv.vm.network \'private_network\', ip: \"%s\", netmask: \"%s\", nic_type: \'82540EM\', virtualbox__intnet: \"%s\"""" % (interface['ip'], interface['netmask'], interface['name'])
            config = config + """
      srv.vm.provision :ansible do |ansible|
        ansible.playbook = \"%s\"
        ansible.extra_vars = {
          interface_name: \"%s\",
          ip_address: \"%s\",
          netmask: \"%s\"
        }
      end
      srv.vm.provision \"shell\", inline: \"/bin/sh /tmp/config-%s.sh\"""" % (os.path.join(ansible_scripts_path, "set_interface.yml"),str("ifcfg-eth"+str(ifcount)), interface['ip'],interface['netmask'], str("ifcfg-eth"+str(ifcount)))
            ifcount += 1
        return config


class CENTOS75(CENTOS):

    box = "kirankn/centOS-7.5"

    def __init__(self, name, flavour="medium",
                 is_management_internal=False, os_version="centos-7.5"):
        super().__init__(name, flavour, is_management_internal, os_version)

    def set_initialconfig(self):
        return super().set_initialconfig("", self.box)


class CENTOS77(CENTOS):

    box = "kirankn/centOS-7.7"

    def __init__(self, name, flavour="medium",
                 is_management_internal=False, os_version="centos-7.7"):
        super().__init__(name, flavour, is_management_internal, os_version)

    def set_initialconfig(self):
        return super().set_initialconfig("", self.box)


class UBUNTU(Server):

    def set_managementip(self, config):
        if not self.is_management_internal:
            config = config + """
      srv.vm.network \"public_network\", auto_config: false, bridge: \'eno1\'
      srv.vm.provision :ansible do |ansible|
        ansible.playbook = \"%s\"
        ansible.extra_vars = {
          vm_ip: \"%s\",
          prefixlen: \"%s\",
          vm_gateway_ip: \"%s\"
          }
      end """ % (os.path.join(ansible_scripts_path, 'network.yml'),
                 self.management_ip['ip'],
                 self.management_ip['prefixlen'],
                 self.management_ip['gateway'])
        return config

    def set_interfaces(self, config):
        for interface in self.interfaces:
            print(interface)
            if interface['host_only']:
                config = config + """
              srv.vm.network \'private_network\',
                ip: \"%s\",
                netmask: \"%s\",
                nic_type: \'82540EM\'""" % (
                    interface['ip'], interface['netmask'])
            else:
                config = config + """
              srv.vm.network \'private_network\',
                ip: \"%s\",
                netmask: \"%s\",
                nic_type: \'82540EM\',
                virtualbox__intnet: \"%s\"""" % (
                    interface['ip'], interface['netmask'], interface['name'])

        return config


class UBUNTU_20_04(UBUNTU):
    box = "lab-in-a-server/ubuntu-focal64"

    def __init__(self, name, flavour="medium",
                 is_management_internal=False, os_version="ubuntu-20.04"):
        super().__init__(name, flavour, is_management_internal, os_version)

    def set_initialconfig(self):
        return super().set_initialconfig("", self.box)


class Switch():

    def __init__(self, name, interfaces=[]):
        self.name = name
        self.re_name = str(name+"_re")
        self.pfe_name = str(name+"_pfe")
        self.interfaces = interfaces

    def setup_box(self):
        pass

    def get_config(self):
        pass


class VQFX(Switch):

    rebox = "juniper/vqfx10k-re"
    pfebox = "juniper/vqfx10k-pfe"

    def __init__(self, name, gateway, interfaces=[]):
        super().__init__(name, interfaces)
        self.gateway = gateway

    def setup_box(self, image_for="RE"):
        if image_for == "RE":
            box = self.rebox
        else:
            box = self.pfebox
        config = """config.vm.define %s do |VAR_PLACEHOLDER|
    VAR_PLACEHOLDER.ssh.insert_key = false
    VAR_PLACEHOLDER.vm.box = \'%s\'
    VAR_PLACEHOLDER.vm.boot_timeout = 1200
    VAR_PLACEHOLDER.vm.synced_folder \'.\',\'/vagrant\', disabled: true
    VAR_PLACEHOLDER.vm.network \'private_network\',auto_config: false,
        nic_type: \'82540EM\', virtualbox__intnet: \"%s\"
    end
    """ % (str(image_for.lower()+"_name"), box, str(self.name+"_internal"))
        return config.replace(
            "VAR_PLACEHOLDER", str("switch"+image_for.lower()))

    def get_config(self):
        # define PFE block
        config = """
    re_name = (\"%s\").to_sym
    pfe_name = (\"%s\").to_sym
    """ % (self.re_name, self.pfe_name)
        config = config + self.setup_box("PFE")
        # End pfe set up block and define RE hostname block
        config = config + self.setup_box("RE")
        config = config + """config.vm.define %s do |VAR_PLACEHOLDER|
    VAR_PLACEHOLDER.vm.hostname = \"%s\"
    VAR_PLACEHOLDER.vm.network \'private_network\',auto_config: false,
        nic_type: \'82540EM\', virtualbox__intnet: \"%s\"
    end""" % ("re_name", str(self.name+"re"),
              str(self.name+"_reserved_bridge"))
        config = config.replace("VAR_PLACEHOLDER", str("switch"+"re"))
        # settiing up interfaces to switch
        config = config + """
    config.vm.define %s do |VAR_PLACEHOLDER|""" % ("re_name")
        config = config.replace("VAR_PLACEHOLDER", str("switch"+"re"))
        # setting up physical connections
        for interface in self.interfaces:
            config = config + \
                self.setup_internal_network(str("switch"+"re"), interface)
        # configuring logical connection
        config = config + """
      VAR_PLACEHOLDER.vm.provision :ansible do |ansible|
        ansible.playbook = \"{}\"
        ansible.extra_vars = {{
          vagrant_root: \"{}\",
          switch_name: \"{}\",
          interface_count: {},
          vlan_id: {},
          gateway_ip: \"{}\"
      }}
      end""".format(os.path.join(ansible_scripts_path, 'switch_interface.yml'),
                    "%s" % os.path.join(par_dir, self.name.rsplit("-", 1)[0]),
                    self.re_name, len(self.interfaces), 101, self.gateway)
        config = config.replace("VAR_PLACEHOLDER", str("switch"+"re"))
        config = config + """
    end"""
        return config

    def setup_internal_network(self, var, interface):
        interface_config = """
      %s.vm.network \'private_network\', auto_config: false,
         nic_type: \'82540EM\',virtualbox__intnet: \"%s\"""" % (var, interface)
        return interface_config


def get_common_file_contents(api_version):
    common_content = """VAGRANTFILE_API_VERSION = \"%s\"
  vagrant_root = File.dirname(__FILE__)
  Vagrant.configure(VAGRANTFILE_API_VERSION) do |config|""" % (api_version)
    return common_content


def append_end_block():
    return """
  end
  """


def get_devices(devices):
    config = ""
    for device in devices:
        config = config + device.get_config()
    return config


def provision_groups(groups_dict, provision_playbook):
    config = """
  if !Vagrant::Util::Platform.windows?
    config.vm.provision "ansible" do |ansible|
      ansible.groups = {"""
    param = ""
    for key, value in groups_dict.items():
        param = param + """
        \"{}\" => {}, """.format(key, value)
    config = config + param[:-2]
    config = config + """
      }
      ansible.playbook = \"%s\"""" % (provision_playbook)
    config = config + """
    end"""
    return config


def generate_vagrant_file(hosts, switches, groups_dict={},
                          provision_playbook="", file_name="Vagrantfile"):
    with open(file_name, 'w') as f:
        f.write(get_common_file_contents(2))
        f.write(get_devices(switches))
        f.write(get_devices(hosts))
        if groups_dict:
            f.write(provision_groups(groups_dict, provision_playbook))
        f.write(append_end_block())
