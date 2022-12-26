#!/bin/bash

cd ~;
apt update -y;
apt upgrade -y;

# Download and then install mysql cluster slave version
wget https://dev.mysql.com/get/Downloads/MySQL-Cluster-8.0/mysql-cluster-community-data-node_8.0.31-1ubuntu22.04_amd64.deb;
apt install libclass-methodmaker-perl -y;
dpkg -i mysql-cluster-community-data-node_8.0.31-1ubuntu22.04_amd64.deb;

# Setup of the cluster slave
# Comments in the config.ini file are left as in the digitalocean example
echo "[mysql_cluster]
# Options for NDB Cluster processes:
ndb-connectstring=ip-10.0.1.10.ec2.internal  # location of cluster manager" > /etc/my.cnf;

mkdir -p /usr/local/mysql/data;
mkdir -p /etc/systemd/system/;

echo "[Unit]
Description=MySQL NDB Data Node Daemon
After=network.target auditd.service

[Service]
Type=forking
ExecStart=/usr/sbin/ndbd
ExecReload=/bin/kill -HUP $MAINPID
KillMode=process
Restart=on-failure

[Install]
WantedBy=multi-user.target" > /etc/systemd/system/ndbd.service;

# Run the slave
systemctl daemon-reload;
systemctl enable ndbd;
systemctl start ndbd;
systemctl status ndbd;