Setup SSH access for your VMs
=============================

### Step 1: Add SSH key
1. Generate a ssh key pair if you have not already generated one. Follow instructions [here](https://help.github.com/articles/generating-a-new-ssh-key-and-adding-it-to-the-ssh-agent/#generating-a-new-ssh-key).
2. Copy the public key from `~/.ssh/id_rsa.pub` and add it to the `/root/.ssh/authorized_keys` file of your fab-server, the dev vm and the all_in_one vm. The developer sandbox is configured for access without authentication.
3. You should now be able to ssh as root into your fab-server and dev vm without needing a password.

    **Note: You will have to use `vagrant ssh` this time to get into your dev vm and all_in_one vm.**

### Step 2: Setup SSH access
There are two ways you can setup SSH access

#### 1. Using SSH ProxyJump
You can use the fab-server as a JumpHost to access the developer sandbox and the all_in_one vm

- Edit the `~/.ssh/config` file and make sure the configuration looks similar to this
   ```
   Host *
    AddKeysToAgent yes
    UseKeychain yes
    IdentityFile ~/.ssh/id_rsa
   Host fabX
    HostName fab-server0X.englab.juniper.net
    User root
   Host devX
    HostName 10.155.75.2X
    User root
   Host sbX
    HostName 10.155.75.2X
    Port 6622
    User root
    ProxyJump fabX
   Host allX
    HostName 10.155.75.3X
    User root
    ProxyJump fabX
   ```

     **Replace 'X' with the number of your fab-server**

#### 2. Using [sshuttle](https://github.com/sshuttle/sshuttle)
In this approach, you will use sshuttle to create a tunnel to the fab-server and redirect requests for the 10.155.75.0/24 ip range through the fab-server.
The advantage of this approach is that you can directly access the contrail services in your browser and applications running on your machine.

- Edit the `~/.ssh/config` file and make sure the configuration looks similar to this
   ```
   Host *
    AddKeysToAgent yes
    UseKeychain yes
    IdentityFile ~/.ssh/id_rsa
   Host fabX
    HostName fab-server0X.englab.juniper.net
    User root
   Host devX
    HostName 10.155.75.2X
    User root
   Host sbX
    HostName 10.155.75.2X
    Port 6622
    User root
    ProxyJump fabX
   Host allX
    HostName 10.155.75.3X
    User root
    ProxyJump fabX
   ```

     **Replace 'X' with the number of your fab-server**

     **Note: No 'ProxyJump'**

- Install sshuttle

   `brew install sshuttle`

- Run sshuttle

   `sshuttle -r fab2 10.155.75.0/24`

You should now be able to access the different services hosted on the all_in_one vm directly from you machine.
