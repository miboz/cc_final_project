#!/bin/bash

cd root;
apt update -y;
apt upgrade -y;

# Sakila setup
apt install unzip -y;
wget http://downloads.mysql.com/docs/sakila-db.zip;
unzip sakila-db;

# Sakila integration with mysql
apt install mysql-server -y;
mysql < sakila-db/sakila-schema.sql;
mysql < sakila-db/sakila-data.sql;
# User already exists???
#mysql -e "CREATE USER 'root'@'localhost' IDENTIFIED BY 'root';";
mysql -e "GRANT ALL PRIVILEGES on sakila.* TO 'root'@'localhost';";

# Sysbench run
apt install sysbench -y;
#sysbench /usr/share/sysbench/oltp_read_write.lua prepare --db-driver=mysql --mysql-db=sakila --mysql-user=root --mysql_password=root --table-size=50000 --tables=10;
#sysbench /usr/share/sysbench/oltp_read_write.lua run --db-driver=mysql --mysql-db=sakila --mysql-user=root --mysql_password=root  --table-size=50000  --tables=10 --threads=8 --max-time=60 > s_a_benchmark;

# No password
sysbench /usr/share/sysbench/oltp_read_write.lua prepare --db-driver=mysql --mysql-db=sakila --mysql-user=root --table-size=50000 --tables=10;
sysbench /usr/share/sysbench/oltp_read_write.lua run --db-driver=mysql --mysql-db=sakila --mysql-user=root --table-size=50000  --tables=10 --threads=8 --max-time=60 > benchmark.txt;