#!/bin/bash
yum clean all
rm -rf /var/cache/yum
yum makecache
