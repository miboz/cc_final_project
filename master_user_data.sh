#!/bin/bash

cd ~;
apt update -y;
apt upgrade -y;


# Setup cluster following https://www.digitalocean.com/community/tutorials/how-to-create-a-multi-node-mysql-cluster-on-ubuntu-18-04
# Download and then install mysql cluster master version
wget https://dev.mysql.com/get/Downloads/MySQL-Cluster-8.0/mysql-cluster-community-management-server_8.0.31-1ubuntu22.04_amd64.deb;
dpkg -i mysql-cluster-community-management-server_8.0.31-1ubuntu22.04_amd64.deb;


# Setup of the cluster master
# Comments in the config.ini file are left as in the digitalocean example
mkdir -p /var/lib/mysql-cluster;

echo "[ndbd default]
# Options affecting ndbd processes on all data nodes:
NoOfReplicas=3	# Number of replicas

[ndb_mgmd]
# Management process options:
hostname=ip-10.0.1.10.ec2.internal # Hostname of the manager
datadir=/var/lib/mysql-cluster 	# Directory for the log files

[ndbd]
hostname=ip-10.0.1.11.ec2.internal # Hostname/IP of the first data node
NodeId=2			# Node ID for this data node
datadir=/usr/local/mysql/data	# Remote directory for the data files

[ndbd]
hostname=ip-10.0.1.12.ec2.internal # Hostname/IP of the second data node
NodeId=3			# Node ID for this data node
datadir=/usr/local/mysql/data	# Remote directory for the data files

[ndbd]
hostname=ip-10.0.1.13.ec2.internal # Hostname/IP of the second data node
NodeId=4			# Node ID for this data node
datadir=/usr/local/mysql/data	# Remote directory for the data files

[mysqld]
# SQL node options:
hostname=ip-10.0.1.10.ec2.internal # In our case the MySQL server/client is on the same Droplet as the cluster manager" > /var/lib/mysql-cluster/config.ini;


ndb_mgmd -f /var/lib/mysql-cluster/config.ini;

pkill -f ndb_mgmd;

mkdir -p /etc/systemd/system/;
echo "[Unit]
Description=MySQL NDB Cluster Management Server
After=network.target auditd.service

[Service]
Type=forking
ExecStart=/usr/sbin/ndb_mgmd -f /var/lib/mysql-cluster/config.ini
ExecReload=/bin/kill -HUP $MAINPID
KillMode=process
Restart=on-failure

[Install]
WantedBy=multi-user.target" > /etc/systemd/system/ndb_mgmd.service;

# Run the master
systemctl daemon-reload;
systemctl enable ndb_mgmd;
systemctl start ndb_mgmd;
systemctl status ndb_mgmd;

# Allow connections from all slaves and proxy
ufw allow from 10.0.1.11;
ufw allow from 10.0.1.12;
ufw allow from 10.0.1.13;
ufw allow from 10.0.1.15; # Proxy address