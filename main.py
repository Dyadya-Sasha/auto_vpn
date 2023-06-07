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


# def ssh_connect():
#     try:
#         client1 = paramiko.client.SSHClient()
#         client1.set_missing_host_key_policy(paramiko.AutoAddPolicy())
#         client1.connect(sys.argv[1], port=_port, username=_user)
#         _stdin1, _stdout1, _stderr1 = client1.exec_command(
#             'sed -i 2d /etc/hosts; sed -i \'2i127.0.1.1     {}  combined-ipdr01\''.format(hostname) + ' /etc/hosts;' + 'sed -i 3d /etc/hosts; sed -i \'3i{}\' /etc/hosts;'.format(
#                 puppet_repo) + 'echo {}'.format(hostname_short) + ' > /etc/hostname; '
#                                                                   'hostname -F '
#                                                                   '/etc/hostname; '
#                                                                   'hostname -f')
#         print("\n----------------")
#         print(_stdout1.read().decode())
#     except TimeoutError:
#         print("\n{}Host doesnt respond{}".format('\033[1m', '\033[0m'))
#         sys.exit()
#     finally:
#         client1.close()

def readlines(stdout):
    line = ''
    while stdout.channel.recv_ready():
        line += stdout.readline(1)
    return line

# def set_credentials(sorm_type, segment, provider_name, city, ip):
#     global hostname
#     global hosts_line
#     hostname = "{}.sorm-2-3.{}.{}.{}.prod.s8.norsi-trans.org".format(sorm_type, segment, provider_name, city)
#     hosts_line = "127.0.1.1       {}   {}".format(hostname, sorm_type)
#     global _5octets
#     _5octets = "{}.sorm-2-3.{}.{}.{}".format(sorm_type, segment, provider_name, city)
#     print("\n5 octets are {}\n".format(_5octets))
#     global VPN_ip
#     VPN_ip = ip


# def puppet_prepare(sorm_type, segment, provider_name, city):
#     sorm_type_corrected = sorm_type[:-2]
#     print("Corected SORM name is {}".format(sorm_type_corrected))
#     puppet_cmd = "mkdir -p {}/s8/prod/{}/{}/{}/sorm-2-3/{}/nodes;".format(PUPPET_GIT, city, provider_name, segment, sorm_type_corrected)
#     subprocess.run(puppet_cmd, check=True, shell=True)
#     puppet_cmd = "cat /home/$USER/puppet_skel > {}/s8/prod/{}/{}/{}/sorm-2-3/{}/nodes/{}.sorm-2-3.{}.{}.{}.prod.s8.norsi-trans.org.yaml".format(PUPPET_GIT, city, provider_name,
#                                                                                                                                                 segment, sorm_type_corrected, sorm_type, segment, provider_name,
#                                                                                                                                                 city)
#     subprocess.run(puppet_cmd, check=True, shell=True)


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

    # set_credentials(sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5], sys.argv[6])
    # puppet_prepare(sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5])
    # ssh_connect()
    #
    # ans = input("\nIs the FQDN correct? (y/n): ")  # Эта хуйня в винде почему то не работает
    # match ans:
    #     case "y":
    #         print("OK")
    #         pass
    #     case "n":
    #         print("Exiting")
    #         sys.exit("Not correct FQDN")
    #     case _:
    #         print("Wrong answer, motherfucker!")
    #         sys.exit()
    #
    # print("\n========================\nPROCEEDING\n ============================")

    try:
        VPN_CMD = "cd {}/easy-rsa; ./easyrsa gen-req {} nopass; ./easyrsa sign-req client {}".format(VPN_git, Sorm_name, Sorm_name)
        subprocess.run(VPN_CMD, check=True, shell=True)

        VPN_CMD = "cd {}/ccd; touch {}; echo 'ifconfig-push {} 255.255.240.0' > {}".format(VPN_git, Sorm_name, IP_address, Sorm_name)
        subprocess.run(VPN_CMD, check=True, shell=True)

        VPN_CMD = "cd {}/scripts; ./create_client_ovpn.sh {}".format(VPN_git, Sorm_name)
        subprocess.run(VPN_CMD, check=True, shell=True)

        VPN_CMD = "cd {}; git add --all; git commit -m \"Added VPN client '{}'\"; git push".format(VPN_git, Sorm_name)
        subprocess.run(VPN_CMD, check=True, shell=True)
        #
        # VPN_CMD = "cd {}/keys; scp -P{} sorm01-prod-dmz_{}.ovpn {}@{}:/root".format(VPN_git, _port, _5octets, _user, sys.argv[1])
        # subprocess.run(VPN_CMD, check=True, shell=True)

        print("\n\nRUNNING PUPPET AGENT ON VPNGW")

        vpn_ssh = paramiko.client.SSHClient()
        vpn_ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        vpn_ssh.connect('10.61.5.11', username="a.pivkin")
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
