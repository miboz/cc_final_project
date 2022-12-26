from deployer import Deployer
from pprint import pprint

d = Deployer()

d.create_standalone_instance()
d.create_cluster()

print('Stand-alone id: ', d.sa_instance_id)
print()

print('Cluster ids:')
pprint(d.cluster_instance_ids)
print()

