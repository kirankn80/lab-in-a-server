from abc import ABC
from enum import Enum
import os

class Server(ABC):

  def __init__(self, name, management_ip={}, interfaces=[], provision=[]):
    self.name = name
    self.interfaces = interfaces
    self.management_ip = management_ip
    self.provision = provision

  def get_config(self):
    config = self.set_initialconfig()
    config = self.set_managementip(config)
    config = self.set_interfaces(config)
    config = self.provision_vm(config)
    config = self.set_endblock(config)
    return config

  def set_initialconfig(self, config, box):
    config = config + """
    srv_name = (\"%s\").to_sym
    config.vm.define srv_name do |srv|
      srv.vm.box = \"%s\"
      if Vagrant.has_plugin?("vagrant-vbguest")
        srv.vbguest.auto_update = false
      end
      srv.vm.hostname = \"%s\"
      srv.vm.network \"public_network\", auto_config: false, bridge: \'eno1\'"""%(self.name, box, self.name)
    return config

  def set_interfaces(self, config):
    for interface in self.interfaces:
      if interface['host_only']:
        config = config + """
      srv.vm.network \'private_network\', ip: \"%s\", netmask: \"%s\", nic_type: \'82540EM\'"""%(interface['ip'], interface['netmask'])
      else :
        config = config + """
      srv.vm.network \'private_network\', ip: \"%s\", netmask: \"%s\", nic_type: \'82540EM\', virtualbox__intnet: \"%s\""""%(interface['ip'], interface['netmask'], interface['name'])
    return config

  def set_endblock(self, config):
    config = config + """
    end
    config.vm.provider :virtualbox do |vb|
      vb.auto_nat_dns_proxy = false
      vb.customize [\"modifyvm\", :id, \"--memory\", \"32768\", \"--cpus\", \"7\"]
    end """
    return config

  def set_managementip(self, config):
    pass

  def provision_vm(self, config):
    for item in self.provision:
      if item['method'] == 'shell':
        config = config + """
      srv.vm.provision \"shell\", path: \"/root/lab-in-a-server/all-in-one/vagrant_vm/ansible/%s\""""%(item['path'])
      if item['method'] == 'ansible':
        config = config + """
      srv.vm.provision :ansible do |ansible|
        ansible.playbook = \"/root/lab-in-a-server/all-in-one/vagrant_vm/ansible/%s\""""%(item['path'])
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
    return config

class CENTOS(Server):

  box = "kirankn/centOS-7.5"

  def __init__(self, name, management_ip={}, interfaces=[], provision=[]):
    super().__init__(name, management_ip, interfaces, provision)

  def set_initialconfig(self):
    return super().set_initialconfig("", self.box)

  def set_managementip(self, config):
    if self.management_ip:
      config = config + """
      srv.vm.provision :ansible do |ansible|
        ansible.playbook = \"/root/lab-in-a-server/all-in-one/vagrant_vm/ansible/network.yml\"
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
      end"""%(self.management_ip['gateway'], self.management_ip['ip'], self.management_ip['netmask'])
    return config


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

  def setup_box(self,image_for="RE"):
    if image_for == "RE":
        box = self.rebox
    else:
        box = self.pfebox
    config = """config.vm.define %s do |VAR_PLACEHOLDER|
    VAR_PLACEHOLDER.ssh.insert_key = false
    VAR_PLACEHOLDER.vm.box = \'%s\'
    VAR_PLACEHOLDER.vm.boot_timeout = 600
    VAR_PLACEHOLDER.vm.synced_folder \'.\',\'/vagrant\', disabled: true
    VAR_PLACEHOLDER.vm.network \'private_network\',auto_config: false, nic_type: \'82540EM\', virtualbox__intnet: \"%s\"
    end
    """%(str(image_for.lower()+"_name"),box,str(self.name+"_internal"))
    return config.replace("VAR_PLACEHOLDER",str(self.name+image_for.lower()))

  def get_config(self):
    #define PFE block
    config = """
    re_name = (\"%s\").to_sym
    pfe_name = (\"%s\").to_sym
    """%(self.re_name,self.pfe_name)
    config = config + self.setup_box("PFE")
    # End pfe set up block and define RE hostname block
    config = config + self.setup_box("RE")
    config = config + """config.vm.define %s do |VAR_PLACEHOLDER|
    VAR_PLACEHOLDER.vm.hostname = \"%s\"
    VAR_PLACEHOLDER.vm.network \'private_network\',auto_config: false, nic_type: \'82540EM\', virtualbox__intnet: \"%s\"
    end"""%("re_name",str(self.name+"re"),str(self.name+"_reserved_bridge"))
    config = config.replace("VAR_PLACEHOLDER",str(self.name+"re"))
    config = config + """
    config.vm.define %s do |VAR_PLACEHOLDER|"""%("re_name")
    config = config.replace("VAR_PLACEHOLDER",str(self.name+"re"))
    for interface in self.interfaces:
        config = config + self.setup_internal_network(str(self.name+"re"),interface)
    config = config + """
    end"""
    return config

  def setup_internal_network(self, var, interface):
    interface_config = """
      %s.vm.network \'private_network\', auto_config: false, nic_type: \'82540EM\',virtualbox__intnet: \"%s\""""%(var,interface)
    return interface_config

def get_common_file_contents(api_version):
  common_content = """VAGRANTFILE_API_VERSION = \"%s\"
  vagrant_root = File.dirname(__FILE__)
  Vagrant.configure(VAGRANTFILE_API_VERSION) do |config|"""%(api_version)
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

def generate_vagrant_file(hosts,switches,file_name="Vagrantfile"):
  with open(file_name, 'w') as f:
    f.write(get_common_file_contents(2))
    f.write(get_devices(switches))
    f.write(get_devices(hosts))
    f.write(append_end_block())

if __name__ == '__main__':
  hosts = []
  switches = []
  hosts.append(CENTOS("h1", { 'ip' : '', 'netmask':'','gateway': 'x.x.x.x'}, [{'name': 'i1','ip': '','netmask':'','host_only': 'false'},{'name':'i2','ip':'','netmask':'','host_only':'false'}], [{'method': 'ansible', 'path': 'devenv.yml', 'variables': {'xyz': 'abc','mno': 34}}]))
  switches.append(VQFX("s1", ['s1','s2','s3']))
  generate_vagrant_file(hosts,switches)
