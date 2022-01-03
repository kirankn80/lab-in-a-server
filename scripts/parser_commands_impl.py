import os
import sys
import yaml
import re
from prettytable import PrettyTable
from colorama import Fore, init
from dev_env import DevEnv
import vm_models as vm
import vagrant_wrappers as vagrant
from contents import Contents
from all_in_one import AllInOne
from three_node import ThreeNode


class LabParser():

    topo_dict = {
       'all_in_one': AllInOne,
       'devenv': DevEnv,
       'three_node':ThreeNode
    }

    @classmethod
    def mb_to_gb(cls, value):
        return int(value/1024)

    @classmethod
    def parse_input_file(cls, file_name):
        try:
            input_parameters = yaml.load(
                open(file_name, "r"), Loader=yaml.FullLoader)
            return input_parameters
        except yaml.YAMLError as e:
            print(e)
            sys.exit()

    @classmethod
    def create(cls, args):
        # import pdb; pdb.set_trace()
        input_params = cls.parse_input_file(args.file_name)
        if 'template' not in input_params.keys():
            print(Fore.RED + "Note: " + Fore.WHITE +
                  "value for template is not specified")
            sys.exit()
        if input_params.get('template') not in cls.topo_dict.keys():
            print(Fore.RED + "Note: " + Fore.WHITE +
                  "Invalid template. Template should be one in {}"
                  .format(cls.topo_dict.keys()))
            sys.exit()
        template = input_params.get('template')
        cls.topo_dict[template](input_params).bring_up_topo()

    @classmethod
    def rebuild(cls, args):
        topology_name = args.topology_name
        info = Contents.get_topo_info(topology_name)
        dirname = info['dirname']
        vagrant.Vagrant.vagrant_destoy(dirname)
        vagrant.Vagrant.vagrant_up(dirname)

    @classmethod
    def poweron(cls, args):
        topology_name = args.topology_name
        info = Contents.get_topo_info(topology_name)
        dirname = info['dirname']
        vagrant.Vagrant.vagrant_up(dirname)

    @classmethod
    def poweroff(cls, args):
        topology_name = args.topology_name
        info = Contents.get_topo_info(topology_name)
        dirname = info['dirname']
        vagrant.Vagrant.vagrant_halt(dirname)

    @classmethod
    def show_resources(cls, args):
        vagrant.Vagrant.clear_cache()
        mem_details = vagrant.Vagrant.get_available_memory_details('g')
        mem_table = PrettyTable(['Memory', 'Value in (GB)'])
        for key, value in mem_details.items():
            mem_table.add_row([key, value])
            print(mem_table)
        info = Contents.get_all_contents()
        table = PrettyTable(['Topology Name', 'Memory Used in (GB)'])
        for name, item in info.items():
            row = []
            row.append(name)
            total_memory = 0
            if 'flavour' in item.keys():
                for node in item['flavour']:
                    flavour = item['flavour'][node]
                    total_memory = total_memory + cls.mb_to_gb(
                        vm.flavour[flavour]['memory'])
            else:
                total_memory = None
            row.append(total_memory)
            table.add_row(row)
        print(table)

    @classmethod
    def list_vm(cls, args):
        if args.resources:
            cls.show_resources(args)
            sys.exit()
        info = Contents.get_all_contents()
        table = PrettyTable(['Topology Name', 'Template',
                            'Contrail Version/DevBranch', 'Working Directory'])
        for name, item in info.items():
            row = []
            row.append(name)
            row.append(item['template'])
            row.append(item['topo_info'])
            row.append(item['dirname'])
            table.add_row(row)
        print(table)

    @classmethod
    def destroy(cls, args):
        destroy_topo = input("Do you want to destroy the topology? (y or n)")
        if destroy_topo.lower() != "y":
            if destroy_topo.lower() != "n":
                print("Invalid input")
                sys.exit()
            else:
                sys.exit()
        # import pdb; pdb.set_trace()
        topo_info = Contents.get_topo_info(args.topology_name)
        dirname = topo_info['dirname']
        vagrant.Vagrant.vagrant_destoy(dirname)
        if topo_info['host_vboxnet_ip'] != []:
            for honly_interface in topo_info['host_vboxnet_ip']:
                op = vagrant.Vagrant.vboxmanage_list_hif()
                print(
                    "vboxnet ip associated with the topology is %s"
                    % honly_interface)
                vboxnet_ip = re.findall(
                    r'Name:\s+(vboxnet\d)[\s\S]{{1,100}}IPAddress:\s+{}'
                    .format(honly_interface), op)
                if vboxnet_ip == []:
                    print(
                     """vboxnet interface name
                      not found for ip address {} on host"""
                     .format(honly_interface))
                else:
                    vagrant.Vagrant.vboxmanage_remove_hif(vboxnet_ip[0])
        Contents.delete_content(args.topology_name)
        vagrant.Vagrant.destroy_workspace(dirname)

    @classmethod
    def show(cls, args):
        topo_info = Contents.get_topo_info(args.topology_name)
        cls.topo_dict[topo_info['template']].show(topo_info)
