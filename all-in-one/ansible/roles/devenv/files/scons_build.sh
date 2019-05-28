#!/bin/bash

cd /root/contrail-dev-env
make setup
export KERNEL_VER=3.10.0-693.el7.x86_64
export KERNELDIR=/lib/modules/$KERNEL_VER/build
cd /root/contrail
scons --kernel-dir=$KERNELDIR
