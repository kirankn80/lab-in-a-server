from abc import ABC
from yaml.tokens import AnchorToken
from . import vagrant_wrappers as vagrant
import yaml
import os
import sys


class Provisioner(ABC):

    ansible_dir_path = "LAB_IN_A_SERVER_ANSIBLE_SCRIPTS_PATH"

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

   machines_dir  = "VAGRANT_MACHINES_FOLDER_PATH"


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
            'vagrant_root': os.path.join(self.machines_dir, host.get_topo_name())
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
            '/bin/sh /tmp/all.sh').get_dict())

    def provision(self, host, contrail_version,
                  openstack_version, registry,
                  dpdk_compute, contrail_deployer_branch):
        self.vars_dict = {
            'contrail_version': contrail_version,
            'vm_ip': host.get_ip_by_name('mgmt'),
            'vm_gw': host.get_gw_by_name('mgmt'),
            'vm_name': host.get_name(),
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

    def provision(self, host, branch):
        self.vars_dict = {
             'branch': branch}
        self.p_list[:0] = [AnsibleProvisioner(
            'dev-lite.yml', self.vars_dict).get_dict()]
        host.provision.extend(self.p_list)

class ThreeNodeContrail(BasicProvisioner):
    def __init__(self):
        self.p_list = []
        self.p_list.append(FileProvisioner(
            'scripts/all.sh', '/tmp/all.sh').get_dict())
        self.p_list.append(ShellInlineProvisioner(
            '/bin/sh /tmp/all.sh').get_dict())
    
    def provision(self, host, contrail_version,
                  openstack_version, registry,
                  dpdk_compute, contrail_deployer_branch,
                  computes,controls,kolla_evip,huge_pages):
    
        self.vars_dict = {
            'primary': {'host': host.get_name(),'ip': host.get_ip_by_name('control_data'),'mip': host.get_ip_by_name('mgmt')},
            'controls': controls,
            'openstack_version': openstack_version,
            'computes': computes,
            'registry': registry,
            'ntp_server': "ntp.juniper.net",
            'kolla_evip': kolla_evip,
            'ctrl_data_gateway': host.get_gw_by_name('control_data'),
            'contrail_version': contrail_version,
            'vagrant_root': os.path.join(self.machines_dir, host.get_topo_name()),
            'dpdk_computes': dpdk_compute,
            'contrail_deployer_branch': contrail_deployer_branch,
            'huge_pages': huge_pages
        }
        self.p_list[:0] = [AnsibleProvisioner(
            'multinode.yml', self.vars_dict).get_dict()]
        host.provision.extend(self.p_list)   
    
class ThreeNodeVqfxContrail(BasicProvisioner):
    def __init__(self):
        self.p_list = []
        self.p_list.append(FileProvisioner(
            'scripts/all.sh', '/tmp/all.sh').get_dict())
        self.p_list.append(ShellInlineProvisioner(
            '/bin/sh /tmp/all.sh').get_dict())
    
    def provision(self, host, contrail_version,
                  openstack_version, registry,
                  dpdk_compute,
                  contrail_deployer_branch,
                  computes,controls,kolla_evip,huge_pages):
    
        self.vars_dict = {
            'primary': {'host': host.get_name(),'ip': host.get_ip_by_name('control_data'),'mip': host.get_ip_by_name('mgmt')},
            'controls': controls,
            'openstack_version': openstack_version,
            'computes': computes,
            'registry': registry,
            'ntp_server': "ntp.juniper.net",
            'kolla_evip': kolla_evip,
            'ctrl_data_gateway': host.get_gw_by_name('control_data'),
            'contrail_version': contrail_version,
            'vagrant_root': os.path.join(self.machines_dir, host.get_topo_name()),
            'dpdk_computes': dpdk_compute,
            'contrail_deployer_branch': contrail_deployer_branch,
            'huge_pages': huge_pages
        }
        self.p_list[:0] = [AnsibleProvisioner(
            'multinode.yml', self.vars_dict).get_dict()]
        host.provision.extend(self.p_list)               
