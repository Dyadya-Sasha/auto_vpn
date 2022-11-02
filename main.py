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
    config_file['DEFAULT']['PUPPET_GIT_FOLDER'] = input("Enter location of Puppet git folder: ")
    config_file['DEFAULT']['DOMAIN_NAME'] = input("Enter your domain name: ")
    with open('config.ini', 'w') as f:
        config_file.write(f)


def config_read():
    global VPN_git
    global PUPPET_GIT
    global DOMAIN_NAME
    config_file = configparser.ConfigParser()
    config_file.read('config.ini')
    VPN_git = config_file['DEFAULT']['VPN_GIT_FOLDER']
    PUPPET_GIT = config_file['DEFAULT']['PUPPET_GIT_FOLDER']
    DOMAIN_NAME = config_file['DEFAULT']['DOMAIN_NAME']
    print(VPN_git)
    print(PUPPET_GIT)


def ssh_connect():
    try:
        client1 = paramiko.client.SSHClient()
        client1.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client1.connect(sys.argv[1], port=_port, username=_user)
        _stdin1, _stdout1, _stderr1 = client1.exec_command(
            'sed -i 2d /etc/hosts; sed -i \'2i127.0.1.1     {}  combined-ipdr01\''.format(hostname) + ' /etc/hosts;' + 'sed -i 3d /etc/hosts; sed -i \'3i{}\' /etc/hosts;'.format(
                puppet_repo) + 'echo {}'.format(hostname_short) + ' > /etc/hostname; '
                                                                  'hostname -F '
                                                                  '/etc/hostname; '
                                                                  'hostname -f')
        print("\n----------------")
        print(_stdout1.read().decode())
    except TimeoutError:
        print("\n{}Host doesnt respond{}".format('\033[1m', '\033[0m'))
        sys.exit()
    finally:
        client1.close()


def set_credentials(sorm_type, segment, provider_name, city, ip):
    global hostname
    global hosts_line
    hostname = "{}.sorm-2-3.{}.{}.{}.prod.s8.norsi-trans.org".format(sorm_type, segment, provider_name, city)
    hosts_line = "127.0.1.1       {}   {}".format(hostname,sorm_type)
    global _5octets
    _5octets = "{}.sorm-2-3.{}.{}.{}".format(sorm_type, segment, provider_name, city)
    print("\n5 octets are {}\n".format(_5octets))
    global VPN_ip
    VPN_ip = ip


def puppet_prepare(sorm_type, segment, provider_name, city):
    sorm_type_corrected = sorm_type.rstrip(sorm_type[-2])
    puppet_cmd = "mkdir -p {}/s8/prod/{}/{}/{}/sorm-2-3/{}/nodes;".format(PUPPET_GIT, city, provider_name, segment, sorm_type)
    subprocess.run(puppet_cmd, check=True, shell=True)
    puppet_cmd = "cat /home/$USER/puppet_skel > {}/s8/prod/{}/{}/{}/sorm-2-3/{}/nodes/{}.sorm-2-3.{}.{}.{}.prod.s8.norsi-trans.org.yaml".format(PUPPET_GIT, city, provider_name,
                                                                                                                                                segment, sorm_type, sorm_type, segment, provider_name,
                                                                                                                                                city)
    subprocess.run(puppet_cmd, check=True, shell=True)


if __name__ == '__main__':
    #    if len(sys.argv) < 7:
    #        sys.exit("Not enough parameters")

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
    print("SORM name is : ", sys.argv[2] + "\n---------------------")
    print("Segment is: ", sys.argv[3] + "\n---------------------")
    print("Provider name is: ", sys.argv[4] + "\n---------------------")
    print("City is: ", sys.argv[5] + "\n---------------------")
    print("IP address is (the last octet): ", sys.argv[6] + "\n---------------------")

    set_credentials(sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5], sys.argv[6])
    puppet_prepare(sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5])
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

        print("\n\nRUNNING PUPPET AGENT ON VPNGW")

        vpn_ssh = client = paramiko.client.SSHClient()
        vpn_ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        vpn_ssh.connect('10.61.5.11', username=DOMAIN_NAME)
        _stdout_, _stdin_, _stderr_ = vpn_ssh.exec_command('sudo /opt/puppetlabs/bin/puppet agent -tv')
        exit_status = _stdout_.channel.recv_exit_status()
        print(exit_status)
        if exit_status == 2:
            print("Puppet agent on VPN did its work successfully")
        else:
            print("Puppet agent on VPN failed")
        vpn_ssh.close()
        sleep(6)

        val = input("\n\nDO NOT FORGET TO CORRECT IPTABLES RULES BEFORE CONTINUING. PRESS ENTER TO CONFIRM.")

        Puppet_push = ("cd {}; git add --all; git commit -m \"Added iptables for client '{}'\"; git push ".format(PUPPET_GIT, sys.argv[3]))
        print("\nPUSHING Puppet CMD {}".format(Puppet_push))
        subprocess.run(Puppet_push, check=True, shell=True)

        print("\nInstalling OpenVPN and puppet agent on remote host")
        client = paramiko.client.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(sys.argv[1], port=_port, username=_user)
        _stdin, _stdout, _stderr = client.exec_command(' cd /etc/apt/sources.list.d/; rm nt.list*; apt update; apt -y install openvpn && echo "OpenVPN installed";' +
                                                       'mv /root/sorm01-prod-dmz_{}.ovpn /etc/openvpn/sorm01-prod-dmz_{}.conf; '.format(_5octets, _5octets) +
                                                       'systemctl enable openvpn@sorm01-prod-dmz_{}; '.format(_5octets) +
                                                       'systemctl start openvpn@sorm01-prod-dmz_{};'.format(_5octets) + 'iptables-save > /etc/iptables.bkp;' + 'echo deb http://172.24.112.1/apt'
                                                                                                                                                               '.puppetlabs.com bionic puppet7 > '
                                                                                                                                                               '/etc/apt/sources.list.d/puppet7.list; '
                                                                                                                                                               'apt update;' +
                                                       'wget http://172.24.112.1/grcc/apt/puppet5.asc; cd /etc/apt/sources.list.d && apt-key add puppet5.asc && rm puppet5.asc; apt update; apt -y install puppet-agent && echo "Puppet agent installed";' +
                                                       'sudo /opt/puppetlabs/bin/puppet agent -tv --server master01.main01.puppet.infra.prod.int.local.norsi-trans.org')
        exit_status = _stdout.channel.recv_exit_status()
        print("\nSign cert request\n")
        print(exit_status)
        if exit_status == 2:
            print("\nCOMPLETED")
        else:
            print("\nSomething went wrong")
        client.close()

        puppet_ssh = client = paramiko.client.SSHClient()
        puppet_ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        puppet_ssh.connect('10.60.5.11', username=DOMAIN_NAME)
        _stdout_, _stdin_, _stderr_ = puppet_ssh.exec_command('sudo /opt/puppetlabs/bin/puppetserver ca sign --certname={}'.format(hostname))
        exit_status = _stdout_.channel.recv_exit_status()

        print("\npuppet git server exit status\n")
        print(exit_status)
        if exit_status == 1:
            print("Certificate onPuppet_git is signed successfully")
        else:
            print("Puppet agent on Puppet_git failed")
        puppet_ssh.close()

    #        final_exit = 1
    #        while final_exit != 0:
    #           client1 = paramiko.client.SSHClient()
    #           client1.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    #           client1.connect(sys.argv[1], port=_port, username=DOMAIN_NAME)
    #           _stdin1, _stdout1, _stderr1 = client1.exec_command('sudo /opt/puppetlabs/bin/puppet agent -tv --server master01.main01.puppet.infra.prod.int.local.norsi-trans.org')
    #           print("\n{}".format(final_exit))
    #           print("one mode final step")
    #           final_exit = _stdout1.channel.recv_exit_status()
    #           if final_exit == 0:
    #                print("Done!")

    except subprocess.CalledProcessError:
        print("Some shit happened :\'(")
    except FileNotFoundError:
        print("\nFile not found ")
    except TimeoutError:
        print("Time out!")
    except paramiko.SSHException as e:
        print("SSH error {}".format(e))
