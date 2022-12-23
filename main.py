from deployer import Deployer

d = Deployer()

d.create_stand_alone_instance()

print(d.sa_instance_id)
print(d.sa_public_ip)

