from colorama import Fore, init
import os
import re
import shutil
import subprocess
import sys


class Vagrant():

    machine_dir = "VAGRANT_MACHINES_FOLDER_PATH"

    @classmethod
    def chdir(cls, dirname):
        try:
            os.chdir(dirname)
        except Exception as e:
            print("cannot change directory to %s" % dirname)
            print(e)
            sys.exit()
        if not os.path.exists(os.path.join(os.getcwd(), "Vagrantfile")):
            print(Fore.RED + "Note: " + Fore.WHITE +
                  "Vagrantfile is not present at - {} ".format(os.getcwd()))
            sys.exit()

    @classmethod
    def run_command(cls, command, shell=False):
        try:
            op = subprocess.run(command,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT,
                                shell=shell)
            print(op.stdout.decode("UTF-8"))
            return op.stdout.decode("UTF-8")
        except subprocess.CalledProcessError as e:
            print("Could not run {} command".format(command))
            print(e)
            sys.exit()

    @classmethod
    def vagrant_up(cls, dirname):
        command = ["vagrant", "up"]
        cls.chdir(dirname)
        op = cls.run_command(command)
        f = open("vagrantup.log","w")
        f.write("logs : " + op)

    @classmethod
    def vagrant_halt(cls, dirname):
        command = ["vagrant", "halt"]
        cls.chdir(dirname)
        cls.run_command(command)

    @classmethod
    def vagrant_provision(cls, dirname):
        command = ["vagrant", "provision"]
        cls.chdir(dirname)
        cls.run_command(command)

    @classmethod
    def vagrant_status(cls, dirname):
        command = ["vagrant", "status"]
        cls.chdir(dirname)
        op = cls.run_command(command)
        return op

    @classmethod
    def vagrant_destoy(cls, dirname):
        # import pdb; pdb.set_trace()
        command = ["vagrant", "destroy", "-f"]
        cls.chdir(dirname)
        cls.run_command(command)

    @classmethod
    def vboxmanage_list_hif(cls):
        command = ["vboxmanage", "list", "hostonlyifs"]
        op = cls.run_command(command)
        return op

    @classmethod
    def vboxmanage_remove_hif(cls, vbox_intf):
        command = ["vboxmanage", "hostonlyif", "remove"]
        command.append(vbox_intf)
        # import pdb; pdb.set_trace()
        cls.run_command(command)

    @classmethod
    def clear_cache(cls):
        command = ['echo 3 > /proc/sys/vm/drop_caches']
        cls.run_command(command, True)

    @classmethod
    def get_available_memory_details(cls, units):
        command = ['free', str('-'+units)]
        op = cls.run_command(command)
        mem_details_str = re.findall(
            r'(Mem:[\s\S]+)\nSwap', op)[0]
        mem_list = re.split(r'\s+', mem_details_str)
        mem_dict = {}
        mem_dict['available'] = int(mem_list[6])
        return mem_dict

    @classmethod
    def create_workspace(cls, name):
        dirname = os.path.join(cls.machine_dir, name)
        if os.path.exists(dirname):
            print(
                """directory %s exists already.
                   Delete the directory and try again"""
                % dirname)
            sys.exit()
        try:
            os.mkdir(dirname)
        except OSError as e:
            print("failed to create workspace")
            print(e)
            sys.exit()
        return dirname

    @classmethod
    def destroy_workspace(cls, name):
        dirname = os.path.join(cls.machine_dir, name)
        try:
            os.chdir("/root")
            shutil.rmtree(dirname)
        except Exception as e:
            print("failed to delete workspace %s" % (dirname))
            print(e)
            sys.exit()
