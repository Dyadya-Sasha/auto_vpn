from lib2to3.refactor import get_fixers_from_package
import subprocess
import paramiko
import sys
import configparser
import os

_user = "root"
_port = 3578
hostname_short = "combined-ipdr01"
hostname = ""
VPN_ip = ""
_5octets = ""
VPN_git = ""


def config_write():
    config_file = configparser.ConfigParser()
    config_file['DEFAULT'] = {}
    config_file['DEFAULT']['VPN_GIT_FOLDER'] = input("Enter location of VPN git folder: ")
    with open('config.ini', 'w') as f:
        config_file.write(f)


def config_read():
    global VPN_git
    config_file = configparser.ConfigParser()
    config_file.read('config.ini')
    VPN_git = config_file['DEFAULT']['VPN_GIT_FOLDER']
    print(VPN_git)


def ssh_connect():
    try:
        client1 = paramiko.client.SSHClient()
        client1.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client1.connect(sys.argv[1], port=_port, username=_user)
        _stdin1, _stdout1, _stderr1 = client1.exec_command(
            'sed -i 2d /etc/hosts; sed -i \'2i{}\''.format(hostname) + ' /etc/hosts;' + 'echo {}'.format(hostname_short) + ' > /etc/hostname; '
                                                                                                                           'hostname -F /etc/hostname;'
                                                                                                                           'hostname -f')
        print("\n----------------")
        print(_stdout1.read().decode())
    except TimeoutError:
        print("\n{}Host doesnt respond{}".format('\033[1m', '\033[0m'))
        sys.exit()
    finally:
        client1.close()


def set_credentials(segment, provider_name, city, ip):
    global hostname
    hostname = "127.0.1.1       combined-ipdr01.sorm-2-3.{}.{}.{}.prod.s8.norsi-trans.org   combined-ipdr01".format(segment, provider_name, city)
    global _5octets
    _5octets = "combined-ipdr01.sorm-2-3.{}.{}.{}".format(segment,provider_name, city)
    print("\n5 octets are {}\n".format(_5octets))
    global VPN_ip
    VPN_ip = ip


if __name__ == '__main__':
    if not os.path.isfile('config.ini'):
        choice = input("Do you want to create default settings config? (y/n) ")
        if choice == "y":
            config_write()
        else:
            pass
    if sys.argv[1] == "-s":
        config_write()
    else:
        pass

    config_read()
    print("---------------------\n" + "Script name is: ", sys.argv[0] + "\n---------------------")
    print("IP address is: ", sys.argv[1] + "\n---------------------")
    print("Segment is: ", sys.argv[2] + "\n---------------------")
    print("Provider name is: ", sys.argv[3] + "\n---------------------")
    print("City is: ", sys.argv[4] + "\n---------------------")
    print("IP address is (the last octet): ", sys.argv[5] + "\n---------------------")

    set_credentials(sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5])
    ssh_connect()

    ans = input("\nIs the FQDN correct? (y/n): ")  # Эта хуйня в винде почему то не работает
    match ans:
        case "y":
            print("OK")
            pass
        case "n":
            print("Exiting")
            sys.exit("Not correct FQDN")
        case _:
            print("Wrong answer, motherfucker!")
            sys.exit()

    print("\n========================\nPROCEEDING\n ============================")

    try:
        VPN_CMD = "cd {}/easy-rsa; ./easyrsa gen-req {} nopass; ./easyrsa sign-req client {}".format(VPN_git, _5octets, _5octets)
        subprocess.run(VPN_CMD, check=True, shell=True)

        VPN_CMD = "cd {}/ccd; touch {}; echo 'ifconfig-push 172.24.112.{} 255.255.240.0' > {}".format(VPN_git, _5octets, VPN_ip, _5octets)
        subprocess.run(VPN_CMD, check=True, shell=True)

        VPN_CMD = "cd {}/scripts; ./create_client_ovpn.sh {}".format(VPN_git, _5octets)
        subprocess.run(VPN_CMD, check=True, shell=True)

        VPN_CMD = "cd {}; git add --all; git commit -m \"Added VPN client '{}'\"; git push".format(VPN_git, _5octets)
        subprocess.run(VPN_CMD, check=True, shell=True)

        VPN_CMD = "cd {}/keys; scp -P{} sorm01-prod-dmz_{}.ovpn {}@{}:/root".format(VPN_git, _port, _5octets, _user, sys.argv[1])
        subprocess.run(VPN_CMD, check=True, shell=True)

        val = input("\n\nDO NOT FORGET TO RUN 'sudo /opt/puppetlabs/bin/puppet agent -tv' on VPN server ( <domain_name>@10.61.5.11 ), \
        OTHERWISE U WILL GET FAILED ON VPN AUTH. PRESS ANY KEY TO CONFIRM: ")

        print("Installing OpenVPN on remote host")
        #        ssh_Process = subprocess.run(['ssh {}'.format(VPN_CMD)], stdout=subprocess.PIPE, universal_newlines=True, shell=True, check=True)
        client = paramiko.client.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(sys.argv[1], port=_port, username=_user)
        _stdin, _stdout, _stderr = client.exec_command('ssh {}@{} -p{}'.format(_user, sys.argv[1], _port) + '; cd /etc/apt/sources.list.d/; rm nt.list*; apt update; apt -y install openvpn; ' +
                                                       'mv /root/sorm01-prod-dmz_{}.ovpn /etc/openvpn/sorm01-prod-dmz_{}.conf; '.format(_5octets, _5octets) +
                                                       'systemctl enable openvpn@sorm01-prod-dmz_{}; '.format(_5octets) +
                                                       'systemctl start openvpn@sorm01-prod-dmz_{}'.format(_5octets))
        _stdout.channel.set_combine_stderr(True)
        output = _stdout.readlines()

    except subprocess.CalledProcessError:
        print("Some shit happened :\'(")
    except FileNotFoundError:
        print("\nFile not found ")
    except TimeoutError:
        print("Time out!")
    except paramiko.SSHException as e:
        print("SSH error {}".format(e))
