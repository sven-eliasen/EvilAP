#!/usr/bin/python3

import sys
import os
import subprocess
import json
from scapy.all import *

def analyse_pckt(pckt: packet):
	ip = pckt.sprintf("{IP:%IP.src%}")
	data = pckt.sprintf("{Raw:%Raw.load%}")

	if data[:4] == "'GET" and data.find("Referer") == -1:
		arr = data.split("\\r\\n")
		arr2 = arr[1].split(" ")
		print(f"'{ip}' visited '{arr2[1]}'")

print("Checking privilege...")
if os.geteuid() != 0:
	sys.exit("You need to be root to execute this script !")

print("Done !")
print("Checking arguments/interfaces...")

if len(sys.argv) < 3:
	sys.exit("Usage: ./main.py INTERFACE_EXT INTERFACE_AP")

# Check both interfaces if they exists
for i in range(1,3):
	if not os.path.exists(f"/sys/class/net/{sys.argv[i]}/"):
		print(f"{sys.argv[i]} interface not found !")
		exit()

print("Done !")
print("Setting up paquet redirection to internet...")

# Activate redirection
f = open("/proc/sys/net/ipv4/ip_forward", "w")
f.write("1")
f.close()

# Allow redirection on firewall
os.system(f"iptables -I POSTROUTING -t nat -o {sys.argv[1]} -j MASQUERADE")

print("Done !")
print("Creating config files...")

f = open("/tmp/dnsmasq.conf", "w")
f.write(f"\
interface={sys.argv[2]}\n\
dhcp-range=192.168.1.50,192.168.1.150,12h\n\
dhcp-option=6,8.8.8.8\n\
dhcp-option=3,192.168.1.1")
f.close()

# Set AP ip address
os.system(f"ip addr add 192.168.1.1/24 dev {sys.argv[2]}")

f = open("/tmp/hostapd.conf", "w")
f.write(f"\
interface={sys.argv[2]}\n\
ssid=Camionette du FBI\n\
hw_mode=g\n\
channel=6")
f.close()

print("Done !")
print("Starting hostapd and dnsmasq...")

# Killing process that could be using port 53
os.system("sudo service systemd-resolved stop")

dnsmasq_p = subprocess.Popen(["dnsmasq", "-d", "-C", "/tmp/dnsmasq.conf"], stdout=subprocess.DEVNULL)
#hostapd_p = subprocess.Popen(["hostapd", "/tmp/hostapd.conf"], stdout=subprocess.DEVNULL)
hostapd_p = subprocess.Popen(["hostapd", "/tmp/hostapd.conf"])


print("Done ! You should see 'Camionette du FBI' wifi")
print("Ctrl-C when you're done...")

try:
	sniff(iface=sys.argv[2], filter="tcp", prn=analyse_pckt)
except KeyboardInterrupt:
	print("Exiting scan...")

dnsmasq_p.terminate()
hostapd_p.terminate()

# clean
os.system("sudo service systemd-resolved restart")
os.system("iptables --flush")

exit(0)