#!/bin/bash -e

if [ $# -lt 1 ]; then
    echo ""
    echo "Usage: create_user.sh <user-id> [password]"
    echo ""
    echo "Default password is 'Embe1mpls'"
    echo ""
fi

user_id=$1
password="Embe1mpls"
if [ $# -eq 2 ]; then
    password=$2
fi
echo "Creating user $user_id..."
adduser $user_id
echo "$user_id:$password" | chpasswd
usermod -aG wheel $user_id
usermod -aG vboxusers $user_id
echo "DONE"
