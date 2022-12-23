#!/bin/bash
yum update -y
yum install -y mysql
systemctl start mysqld