from abc import ABC

from yaml.tokens import AnchorToken
import vagrant_wrappers as vagrant
import yaml
import os
import sys

class Provisioner(ABC):
    
    ansible_dir_path = "/root/aprathi/lab-restructuring/ansible"
    
    def __init__(self, method):
       self.method = method
    
    def get_dict(self):
        return self.__dict__
    
class ShellFileProvisioner(Provisioner):
    def __init__(self, path):
        super().__init__('shell')
        self.path = "\"{}\"".format(
            os.path.join(self.ansible_dir_path, path))


class ShellInlineProvisioner(Provisioner):
    def __init__(self, cmd):
        super().__init__('shell')
        self.inline = "\"{}\"".format(cmd)

class AnsibleProvisioner(Provisioner):
    def __init__(self, path, vars={}):
        super().__init__('ansible')
        self.path = "\"{}\"".format(
            os.path.join(self.ansible_dir_path, path))
        self.variables = vars

class FileProvisioner(Provisioner):
    
    def __init__(self, source, destination):
        super().__init__('file')
        self.source = "\"{}\"".format(
            os.path.join(self.ansible_dir_path, source))
        self.destination = "\"{}\"".format(destination)


class BasicProvisioner(ABC):

    machines_dir = "VAGRANT_MACHINES_FOLDER_PATH"


class Basepkgs(BasicProvisioner):
    def __init__(self):
        self.p_list = []
        self.p_list.append(AnsibleProvisioner('base_pkgs.yml').get_dict())
    
    def provision(self, host):
        host.provision.extend(self.p_list)
        
    
class Devpkgs(BasicProvisioner):
    def __init__(self):
        self.p_list = []
        self.p_list.append(AnsibleProvisioner('dev_pkgs.yml').get_dict())
    
    def provision(self, host):
        host.provision.extend(self.p_list)


class ContrailCommand(BasicProvisioner):
    def __init__(self):
        self.p_list = []
        self.p_list.append(ShellFileProvisioner(
            'scripts/docker.sh').get_dict())
        self.p_list.append(FileProvisioner(
            'scripts/cc.sh', '/tmp/cc.sh').get_dict())
        self.p_list.append(ShellInlineProvisioner(
            'chmod +x /tmp/cc.sh && /tmp/cc.sh').get_dict())
    
    def provision(self, host, contrail_version, registry):
        self.vars_dict = {
            'contrail_version': contrail_version,
            'vm_ip': host.get_ip_by_name('mgmt'),
            'registry': registry,
            'vagrant_root': os.path.join(self.machines_dir, host.get_name())
        }
        self.p_list[:0] = [AnsibleProvisioner(
            'ui.yml', self.vars_dict).get_dict()]
        host.provision.extend(self.p_list)
        
class AllInOneContrail(BasicProvisioner):
    def __init__(self):
        self.p_list = []
        self.p_list.append(FileProvisioner(
            'scripts/all.sh', '/tmp/all.sh').get_dict())
        self.p_list.append(ShellInlineProvisioner(
            '/ bin/sh /tmp/all.sh').get_dict())
    
    def provision(self, host, contrail_version,
                  openstack_version, registry,
                  dpdk_compute, contrail_deployer_branch):
        self.vars_dict = {
            'contrail_version': contrail_version,
            'vm_ip': host.get_ip_by_name('mgmt'),
            'vm_gw': host.get_gw_by_name('mgmt'),
            'vm_name':host.get_name(),
            'openstack_version': openstack_version,
            'registry': registry,
            'dpdk_compute': dpdk_compute,
            'vagrant_root': os.path.join(self.machines_dir, host.get_name()),
            'contrail_deployer_branch': contrail_deployer_branch,
        }
        self.p_list[:0] = [AnsibleProvisioner(
            'all.yml', self.vars_dict).get_dict()]
        host.provision.extend(self.p_list)
    
class DevEnvContrail(BasicProvisioner):
    def __init__(self):
        self.p_list = []
        self.p_list.append(FileProvisioner(
            'scripts/dev_init.sh', '/tmp/dev_init.sh').get_dict())
        self.p_list.append(ShellInlineProvisioner(
            '/bin/sh /tmp/dev_init.sh').get_dict())
    def provision(self,host,branch):
        self.vars_dict = {
             'branch': branch }
        self.p_list[:0] = [AnsibleProvisioner(
            'dev-lite.yml', self.vars_dict).get_dict()]
        host.provision.extend(self.p_list)