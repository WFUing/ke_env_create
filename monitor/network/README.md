## 网络信息监测

### ruleEndpoint_test

kubeedge 中的路由转发

可以查看文档 https://kubeedge.io/docs/developer/custom_message_deliver

### other-nodes-ips

在k8s中获取其他节点的ip

**部署**

```bash
kubectl apply -f other-nodes-ips/
```

### ping-pod

用 ping 和 iperf3 实现传输时延和带宽监测

部署

```bash
kubectl apply -f ping-pod/docker/ping-pod.yaml
```








kubectl port-forward -n monitoring service/grafana 3000:3000

kubectl exec -it update-all-nodes-ips-5tv99 -n monitoring -- /bin/sh

kubectl get configmap other-nodes-ips-config -n monitoring -o yaml

sudo iptables -P FORWARD ACCEPT

