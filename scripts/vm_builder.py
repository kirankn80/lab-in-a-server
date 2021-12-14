import argparse
from typing import ClassVar
from colorama import Fore, init
import os
import sys
import yaml
import parser_commands_impl as actions
import vagrant_wrappers as vagrant
from contents import Contents
from all_in_one import AllInOne
from dev_env import DevEnv


def validate_file(file_name):
    if not os.path.exists(file_name):
        parser.error("File %s not found in the path" % (file_name))
    else:
        return file_name


def validate_topology_name_deletion(name):
    is_topo_present = Contents.check_if_topo_exists(name)
    if not is_topo_present:
        parser.error(
         "topology with name %s does not exist\n Check topology name" % (name))
    return name


if __name__ == '__main__':
    init(autoreset=True)
    global parser
    parser = argparse.ArgumentParser()
    subparser = parser.add_subparsers(dest='command')
    create_topology = subparser.add_parser(
        "create", help="create vagrant file and bring up topology")
    retry_topology = subparser.add_parser(
        "rebuild", help="retry building topology")
    list_topology = subparser.add_parser("list", help="list topology details")
    show_topology = subparser.add_parser(
        "show", help="show individual topology details")
    delete_topology = subparser.add_parser("destroy", help="delete topology")
    poweron_topology = subparser.add_parser(
        "poweron", help="power on all machines of given topology")
    poweroff_topology = subparser.add_parser(
        "poweroff", help="power off all machines of given topology")
    # create topology has mandatory file name as argument
    create_topology.add_argument(
        "file_name",
        help="path to the config file",
        type=lambda x: validate_file(x))

    retry_topology.add_argument(
        "topology_name",
        help="name of the topology to be rebuilt",
        type=lambda x: validate_topology_name_deletion(x))
    # list global i.e., for all keys
    show_topology.add_argument(
        "topology_name",
        help="name of the topology",
        type=lambda x: validate_topology_name_deletion(x))
    # destroy vm
    delete_topology.add_argument(
        "topology_name",
        help="name of the topology to be destroyed",
        type=lambda x: validate_topology_name_deletion(x))

    list_topology.add_argument(
        "--resources",
        help="list available resources",
        action="store_true", default=False)

    poweron_topology.add_argument(
        "topology_name",
        help="name of the topology to be powered on",
        type=lambda x: validate_topology_name_deletion(x))

    poweroff_topology.add_argument(
      "topology_name",
      help="name of the topology to be powered off",
      type=lambda x: validate_topology_name_deletion(x))

    args = parser.parse_args()
    print(args)
    if args.command == "list":
        getattr(actions.LabParser, 'list_vm')(args)
    elif args.command is None:
        parser.print_help()
    else:
        getattr(actions.LabParser, args.command)(args)
