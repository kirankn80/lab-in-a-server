import json
import os
import sys
import shutil
import interface_handler as IFHandler


class Contents():

    info_file = "LAB_IN_A_SERVER_INFO_FILE"

    par_dir = "VAGRANT_MACHINES_FOLDER_PATH"
    
    ansible_scripts_path = "LAB_IN_A_SERVER_ANSIBLE_SCRIPTS_PATH"

    @classmethod
    def get_all_contents(cls):
        if not os.path.exists(cls.info_file):
            print("info file not found in path")
            sys.exit()
        with open(cls.info_file, "r") as info_file_handler:
            info = json.load(info_file_handler)
        return info

    @classmethod
    def check_if_topo_exists(cls, topo_name):
        if not os.path.exists(cls.info_file):
            print("info file not found in path")
            return False
        with open(cls.info_file, "r") as info_file_handler:
            info = json.load(info_file_handler)
        if topo_name in info.keys():
            return True
        return False

    @classmethod
    def get_topo_info(cls, topo_name):
        if cls.check_if_topo_exists(topo_name):
            info = cls.get_all_contents()
            return info[topo_name]
        else:
            return {}

    @classmethod
    def write_to_file(cls, content_info):
        if not os.path.exists(cls.info_file):
            print("info file not found in path")
            sys.exit()
        json.dump(content_info, open(cls.info_file, "w"))

    @classmethod
    def delete_content(cls, key):
        if cls.check_if_topo_exists(key):
            info = cls.get_all_contents()
            del info[key]
            cls.write_to_file(info)
        else:
            print("topology %s does not exist" % (key))
            sys.exit()

    @classmethod
    def insert(cls, template_name, name, hosts, switches, is_management_internal, dirname, topo_def=""):
        topo_info = {}
        topo_info['switches'] = []
        topo_info['hosts'] = [host.name for host in hosts]
        topo_info['template'] = template_name
        topo_info['topo_info'] = topo_def
        topo_info['dirname'] = dirname
        topo_info['host_vboxnet_ip'] = IFHandler.HostOnlyIfsHandler.used_hostonlyif_ips
        topo_info['internal_network'] = is_management_internal
        topo_info['hostnames'] = [host.name for host in hosts]
        topo_info['flavour'], topo_info['management_data'], \
            topo_info['vboxnet_interfaces'], \
                topo_info['ctrl_data_ip'] = cls.get_dict_form(hosts,is_management_internal)
        
        if cls.check_if_topo_exists(name):
            sys.exit()
        info = cls.get_all_contents()
        info[name] = topo_info
        cls.write_to_file(info)
    
    @classmethod
    def get_dict_form(cls, hosts, is_management_internal=False):
        flavour_dict = {}
        management_data = {}
        vboxnet_interfaces_dict = {}
        ctrl_data_ip = {}
        for node in hosts:
            for intf in node.interfaces:
                if intf.get('name') == 'mgmt' and is_management_internal:
                    vboxnet_interfaces_dict[node.name] = intf.get('ip')
                    management_data[node.name] = {}
                if intf.get('name') == 'ctrl_data':
                    ctrl_data_ip[node.name] = intf.get('ip')      
            if not is_management_internal:
                management_data[node.name] = node.management_ip
            flavour_dict[node.name] = node.flavour
        return flavour_dict, management_data, vboxnet_interfaces_dict, ctrl_data_ip

