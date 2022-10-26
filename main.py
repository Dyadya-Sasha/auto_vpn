# This is a sample Python script.

# Press Shift+F10 to execute it or replace it with your code.
# Press Double Shift to search everywhere for classes, files, tool windows, actions, and settings.

import subprocess
import paramiko
import sys
import configparser

# ip = "192.168.0.155"
_user = "user"
_port = 3578
_password = "qweqwe"
hostname = ""


def config():
    config_file = configparser.ConfigParser()
    config_file['DEFAULT'] = {}
    config_file['DEFAULT']['PUPPET_GIT_FOLDER'] = input("Enter location of Puppet git folder: ")
    with open('config.ini', 'w') as f:
        config_file.write(f)


def ssh_connect():
    client = paramiko.client.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(sys.argv[1], port=_port, username=_user, password=_password)
    _stdin, _stdout, _stderr = client.exec_command('cd /home/user; echo {}'.format(hostname) + '> test_file;'
                                                                                               'hostname -f')

    print(_stdout.read().decode())
    client.close()


def set_hostname(host_name):
    global hostname
    hostname = "ubuntu.home.{}".format(host_name)


if __name__ == '__main__':
    choice = input("Do you want to create default settings config? (y/n) ")
    if choice == "y":
        config()
    else:
        pass

    set_hostname(sys.argv[2])
    print("---------------------\n" + "Script name is: ", sys.argv[0] + "\n---------------------")
    print("IP address is: ", sys.argv[1] + "\n---------------------")
    print("Hostname is: ", sys.argv[2] + "\n---------------------")
#    print(hostname)
    ssh_connect()
    ans = input("Is the FQDN correct? (y/n): ")
    match ans:
        case "y":
            print("OK")
            pass
        case "n":
            print("Exiting")
            sys.exit("Not correct FQDN")
        case _:
            print("Wrong answer, motherfucker!")
    print("PROCEEDING")
    cmd = "ssh {}@{} -p{}".format(_user, sys.argv[1], _port)
    input_cmd = "cd /home/user/TEST; echo 'HUI' >> test"
    res = subprocess.run(cmd, stdout=subprocess.PIPE, input=input_cmd, check=True
                         , shell=True
                         , text=True)

