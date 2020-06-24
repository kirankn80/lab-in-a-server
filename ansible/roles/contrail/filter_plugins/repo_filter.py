import requests
import json
from builtins import object


class FilterModule(object):

    def filters(self):
        return {
            'get_deployer_repo': self.get_deployer_repo
        }

    def get_deployer_repo(self, branch_required):
        contrail_branches_info = requests.get(
            "https://api.github.com/repos/Juniper/contrail-ansible-deployer/branches").json()
        tf_branches_info = requests.get(
            "https://api.github.com/repos/tungstenfabric/tf-ansible-deployer/branches").json()
        tf_branches_info.reverse()
        contrail_branches_info.reverse()
        branches_info = tf_branches_info + contrail_branches_info
        repo = ''
        if branch_required == 'master':
            return "https://github.com/tungstenfabric/tf-ansible-deployer.git"
        for branch in branches_info:
            if branch['name'] == branch_required:
                repo = branch['commit']['url']
        if 'contrail-ansible-deployer' in repo:
            return "https://github.com/Juniper/contrail-ansible-deployer.git"
        else:
            return "https://github.com/tungstenfabric/tf-ansible-deployer.git"
