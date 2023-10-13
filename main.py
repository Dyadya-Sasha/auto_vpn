import select
from lib2to3.refactor import get_fixers_from_package
import subprocess
import paramiko
import sys
import configparser
import os
from time import sleep

_user = "root"
_port = 3578
hostname_short = "combined-ipdr01"
hostname = ""
hosts_line = ""
VPN_ip = ""
_5octets = ""
VPN_git = ""
PUPPET_GIT = ""
DOMAIN_NAME = ""
puppet_repo = "172.24.112.1    master01.main01.puppet.infra.prod.int.local.norsi-trans.org\n"


def config_write():
    config_file = configparser.ConfigParser()
    config_file['DEFAULT'] = {}
    config_file['DEFAULT']['VPN_GIT_FOLDER'] = input("Enter location of VPN git folder: ")
    # config_file['DEFAULT']['PUPPET_GIT_FOLDER'] = input("Enter location of Puppet git folder: ")
    config_file['DEFAULT']['DOMAIN_NAME'] = input("Enter your domain username: ")
    with open('config.ini', 'w') as f:
        config_file.write(f)


def config_read():
    global VPN_git
    # global PUPPET_GIT
    global DOMAIN_NAME
    config_file = configparser.ConfigParser()
    config_file.read('config.ini')
    VPN_git = config_file['DEFAULT']['VPN_GIT_FOLDER']
    DOMAIN_NAME = config_file['DEFAULT']['DOMAIN_NAME']
    # PUPPET_GIT = config_file['DEFAULT']['PUPPET_GIT_FOLDER']

    print("VPN_GIT is at {}".format(VPN_git))
    print("DOMAIN NAME is {}".format(DOMAIN_NAME))
    # print(PUPPET_GIT)


def readlines(stdout):
    line = ''
    while stdout.channel.recv_ready():
        line += stdout.readline(1)
    return line


if __name__ == '__main__':
    #    if len(sys.argv) < 7:
    #        sys.exit("Not enough parameters")

    if not os.path.isfile('config.ini'):
        choice = input("Do you want to create default settings config? (y/n) ")
        if choice == "y":
            config_write()
        else:
            pass

    config_read()

    IP_address = input("Enter full ip address of sorm: ")
    Sorm_name = str(input("Enter name of sorm (first 5 octets): "))

    try:
        VPN_CMD = "cd {}/easy-rsa; ./easyrsa gen-req {} nopass; ./easyrsa sign-req client {}".format(VPN_git, Sorm_name, Sorm_name)
        subprocess.run(VPN_CMD, check=True, shell=True)

        VPN_CMD = "cd {}/ccd; touch {}; echo 'ifconfig-push {} 255.255.240.0' > {}".format(VPN_git, Sorm_name, IP_address, Sorm_name)
        subprocess.run(VPN_CMD, check=True, shell=True)

        VPN_CMD = "cd {}/scripts; ./create_client_ovpn.sh {}".format(VPN_git, Sorm_name)
        subprocess.run(VPN_CMD, check=True, shell=True)

        VPN_CMD = "cd {}; git pull".format(VPN_git)
        subprocess.run(VPN_CMD, check=True, shell=True)

        VPN_CMD = "cd {}; git add --all; git commit -m \"Added VPN client '{}'\"; git push".format(VPN_git, Sorm_name)
        subprocess.run(VPN_CMD, check=True, shell=True)
        #
        # VPN_CMD = "cd {}/keys; scp -P{} sorm01-prod-dmz_{}.ovpn {}@{}:/root".format(VPN_git, _port, _5octets, _user, sys.argv[1])
        # subprocess.run(VPN_CMD, check=True, shell=True)

        print("\n\nRUNNING PUPPET AGENT ON VPNGW")

        vpn_ssh = paramiko.client.SSHClient()
        vpn_ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        vpn_ssh.connect('10.61.5.11', username=DOMAIN_NAME)
        _stdout_, _stdin_, _stderr_ = vpn_ssh.exec_command('sudo /opt/puppetlabs/bin/puppet agent -tv', get_pty=True)

        exit_status = _stdout_.channel.recv_exit_status()
        print(exit_status)
        if exit_status == 2:
            print("Puppet agent on VPN did its work successfully")
        else:
            print("Puppet agent on VPN failed")
        vpn_ssh.close()
        sleep(6)
    except subprocess.CalledProcessError:
        print("Some shit happened :\'(")
    except FileNotFoundError:
        print("\nFile not found ")
    except TimeoutError:
        print("Time out!")
    except paramiko.SSHException as e:
        print("SSH error {}".format(e))
