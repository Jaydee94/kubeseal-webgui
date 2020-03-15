from kubernetes import client, config

#<<<observe below line of code >>>
#uses default config file loccated at ~/.kube/config
config.load_kube_config()

v1 = client.CoreV1Api()
print("Listing pods with their IPs:")
ret = v1.list_pod_for_all_namespaces(watch=False)
for i in ret.items:
    print("%s\t%s\t%s" % (i.status.pod_ip, i.metadata.namespace, i.metadata.name))

res = v1.list_namespaced_pod(namespace='default',watch=False)
for i in res.items:
    print("%s\t%s\t%s" % (i.status.pod_ip, i.metadata.namespace, i.metadata.name))