# k8s集群ip修改的情况

## 问题一：


```
(base) wds@cloud:~$ kubectl get nodes
E0125 15:20:04.198482    7304 memcache.go:265] couldn't get current server API group list: Get "https://192.168.28.45:6443/api?timeout=32s": context deadline exceeded - error from a previous attempt: read tcp 127.0.0.1:34728->127.0.0.1:7890: read: connection reset by peer
E0125 15:20:36.199297    7304 memcache.go:265] couldn't get current server API group list: Get "https://192.168.28.45:6443/api?timeout=32s": context deadline exceeded - error from a previous attempt: read tcp 127.0.0.1:44292->127.0.0.1:7890: read: connection reset by peer
```

关闭代理

```sh
unset http_proxy
unset https_proxy
unset HTTP_PROXY
unset HTTPS_PROXY
```

运行以下命令来检查当前的 kubeconfig 文件：

```sh
kubectl config view
```

修改 kubeconfig 文件，如果 IP 地址不正确，需要更新它：

```sh
kubectl config set-cluster kubernetes --server=https://192.168.0.104:6443
```

## 问题二：

```
(base) wds@cloud:~$ kubectl get nodes
E0125 15:24:03.927846    8961 memcache.go:265] couldn't get current server API group list: Get "https://192.168.0.104:6443/api?timeout=32s": dial tcp 192.168.0.104:6443: connect: connection refused
E0125 15:24:03.927953    8961 memcache.go:265] couldn't get current server API group list: Get "https://192.168.0.104:6443/api?timeout=32s": dial tcp 192.168.0.104:6443: connect: connection refused
E0125 15:24:03.929280    8961 memcache.go:265] couldn't get current server API group list: Get "https://192.168.0.104:6443/api?timeout=32s": dial tcp 192.168.0.104:6443: connect: connection refused
E0125 15:24:03.930673    8961 memcache.go:265] couldn't get current server API group list: Get "https://192.168.0.104:6443/api?timeout=32s": dial tcp 192.168.0.104:6443: connect: connection refused
E0125 15:24:03.931938    8961 memcache.go:265] couldn't get current server API group list: Get "https://192.168.0.104:6443/api?timeout=32s": dial tcp 192.168.0.104:6443: connect: connection refused
The connection to the server 192.168.0.104:6443 was refused - did you specify the right host or port?
```

httpGet 配置通常存在于以下文件中之一：

/etc/kubernetes/manifests/*

搜索包含 192.168.28.45 的配置文件
如果不确定文件位置，可以使用以下命令查找：

```sh
grep -r "192.168.28.45" /etc/kubernetes/manifests/
```

以下命令可以一次性修改 /etc/kubernetes/manifests/ 目录下所有包含 192.168.28.45 的文件内容，将其替换为 192.168.0.104：

```sh
sudo sed -i 's/192.168.28.45/192.168.0.104/g' /etc/kubernetes/manifests/*.yaml
```

## 问题三

```
(base) wds@cloud:~$ kubectl get nodes
E0125 16:15:56.853145   18119 memcache.go:265] couldn't get current server API group list: Get "https://192.168.0.104:6443/api?timeout=32s": tls: failed to verify certificate: x509: certificate is valid for 10.96.0.1, 192.168.28.45, not 192.168.0.104
E0125 16:15:56.854926   18119 memcache.go:265] couldn't get current server API group list: Get "https://192.168.0.104:6443/api?timeout=32s": tls: failed to verify certificate: x509: certificate is valid for 10.96.0.1, 192.168.28.45, not 192.168.0.104
E0125 16:15:56.856608   18119 memcache.go:265] couldn't get current server API group list: Get "https://192.168.0.104:6443/api?timeout=32s": tls: failed to verify certificate: x509: certificate is valid for 10.96.0.1, 192.168.28.45, not 192.168.0.104
E0125 16:15:56.858184   18119 memcache.go:265] couldn't get current server API group list: Get "https://192.168.0.104:6443/api?timeout=32s": tls: failed to verify certificate: x509: certificate is valid for 10.96.0.1, 192.168.28.45, not 192.168.0.104
E0125 16:15:56.860393   18119 memcache.go:265] couldn't get current server API group list: Get "https://192.168.0.104:6443/api?timeout=32s": tls: failed to verify certificate: x509: certificate is valid for 10.96.0.1, 192.168.28.45, not 192.168.0.104
```

重新生成证书

```sh
sudo kubeadm config print init-defaults | sudo tee /etc/kubernetes/kubeadm-config.yaml > /dev/null
```

```yaml
apiVersion: kubeadm.k8s.io/v1beta3
bootstrapTokens:
- groups:
  - system:bootstrappers:kubeadm:default-node-token
  token: abcdef.0123456789abcdef
  ttl: 24h0m0s
  usages:
  - signing
  - authentication
kind: InitConfiguration
localAPIEndpoint:
  advertiseAddress: 192.168.0.104
  bindPort: 6443
nodeRegistration:
  criSocket: unix:///var/run/containerd/containerd.sock
  imagePullPolicy: IfNotPresent
  name: node
  taints: null
---
apiServer:
  timeoutForControlPlane: 4m0s
  certSANs:
    - "127.0.0.1"
    - "192.168.0.104" # 控制平面节点的实际 IP 地址
    - "10.96.0.1"     # 默认的 ClusterIP
apiVersion: kubeadm.k8s.io/v1beta3
certificatesDir: /etc/kubernetes/pki
clusterName: kubernetes
controllerManager: {}
dns: {}
etcd:
  local:
    dataDir: /var/lib/etcd
imageRepository: registry.k8s.io
kind: ClusterConfiguration
kubernetesVersion: 1.27.0
networking:
  podSubnet: "10.244.0.0/16"  # 保持与 Flannel 默认配置一致
  dnsDomain: "cluster.local"
  serviceSubnet: "10.96.0.0/12"
scheduler: {}
```

重新生成证书，使用 kubeadm 重新生成 API 服务器的证书：

```sh
sudo kubeadm init phase kubeconfig admin --config /etc/kubernetes/kubeadm-config.yaml
```

```
sudo systemctl daemon-reload
sudo systemctl restart kubelet
```

