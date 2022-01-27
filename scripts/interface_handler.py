import vagrant_wrappers as vagrant
import yaml
import os
import sys
import re
import datetime


class VboxIp():
    def __init__(self, ip, gateway, intf_type = None, netmask='255.255.255.0',
                 name=None, unique_name = None):
        self.ip = ip
        self.netmask = netmask
        self.gateway = gateway
        self.type = intf_type
        self.name = name
        self.unique_name = unique_name
        self.host_only = True if self.type == "host_only" else False
        self.prefixlen = self.set_prefixlen()

    def get_ip_dict(self):
        return self.__dict__

    def set_prefixlen(self):
        return sum([bin(int(x)).count('1') for x in self.netmask.split('.')])

        
class HostOnlyIfsHandler():

    available_hostonlyifs_ips = []
    used_hostonlyif_ips = {}

    @classmethod
    def get_next_ip(cls, subnet):
        ip = cls.used_hostonlyif_ips[subnet] 
        if ip == 254:
            print("ERROR: subnet exhausted for {}".format(subnet))
            sys.exit(0)
        ip = ip + 1
        cls.used_hostonlyif_ips[subnet] = ip
        subnet1 = subnet.split('.')[:-1]
        subnet1.append(str(ip))
        return str('.'.join(subnet1))
    
    @classmethod
    def get_all_valid_hostonly_ifs(cls):
        valid_vboxnet_ips = []
        for i in range(1, 250):
            valid_vboxnet_ips.append('192.168.{}.1'.format(i))
        return valid_vboxnet_ips

    @classmethod
    def vboxnet_get_hostonly_subnet(cls):
        if not cls.available_hostonlyifs_ips:
            op = vagrant.Vagrant.vboxmanage_list_hif()
            existing_vboxnet_tuples = re.findall(
                r'Name:\s+(vboxnet\d)[\s\S]{1,100}IPAddress:\s+([\d{1,3}\.]+)',
                op)
            host_only_ips = []
            for vbnet in existing_vboxnet_tuples:
                host_only_ips.append(vbnet[1])
            valid_vboxnet_ips = cls.get_all_valid_hostonly_ifs()
            cls.available_hostonlyifs_ips = list(
                set(valid_vboxnet_ips).difference(set(host_only_ips)))
        vbip = cls.available_hostonlyifs_ips.pop(0)
        cls.used_hostonlyif_ips[vbip] = 1
        return vbip

    @classmethod
    def get_gateway(cls, ip):
        input_ip = ip.split('.')[:-1]
        input_ip.append('1')
        ip_str = '.'.join(input_ip)
        return ip_str

class VboxIpSwitch():
    def __init__(self, unique_name = None):
      
        self.unique_name = unique_name
       
    def get_ip_dict(self):
        return self.__dict__

class InternalNetwork():
    
    used_ctrl_data_ips = {}
    unique_suffix = str(datetime.datetime.now().strftime("_%Y%m%d%m%s"))
    
    @classmethod
    def get_next_ip(cls, subnet):
        ip = cls.used_ctrl_data_ips[subnet] 
        if ip == 254:
            print("ERROR: subnet exhausted for {}".format(subnet))
            sys.exit(0)
        ip = ip + 1
        cls.used_ctrl_data_ips[subnet] = ip
        subnet1 = subnet.split('.')[:-1]
        subnet1.append(str(ip))
        return str('.'.join(subnet1))
   
    @classmethod
    def get_unique_name(cls,icounter):
        unique_name = str('i' + str(icounter) + cls.unique_suffix )
        return unique_name
        
    @classmethod
    def get_ctrl_subnet(cls):
         ctrl_data_subnet = {'octet1': '192', 'octet2': '168','octet3': 251}
         subnet = str(ctrl_data_subnet['octet1']+'.'+ctrl_data_subnet['octet2']+'.'+str(ctrl_data_subnet['octet3'])+'.'+str(1))
         ctrl_data_subnet['octet3'] += 1
         cls.used_ctrl_data_ips[subnet] = 1
         return subnet