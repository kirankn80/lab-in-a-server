export LC_ALL=en_US.UTF-8
export LANG=en_US.UTF-8
export LANGUAGE=en_US.UTF-8
export LC_TYPE=en_US.UTF-8

cd /root/contrail-dev-env

make create-repo 
make sync
make setup
make dep
python3 /root/contrail/third_party/fetch_packages.py
 