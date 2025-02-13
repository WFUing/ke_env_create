
## kubeedge 安装：

### 环境搭建：

- cloudcore：云端安装 k8s
- edgecore：边端安装containerd

#### 1. 安装docker/containerd

docker安装方式，**安装前记得配置代理**

- https://mirrors.tuna.tsinghua.edu.cn/help/docker-ce/

记得替换repo为国内镜像，如阿里云

```bash
apt install containerd
```

containerd会使用apt连同docker engine一同下载，但需要修改配置

```sh
# 保存默认配置
containerd config default > /etc/containerd/config.toml

# 修改配置
# sandbox_image = "registry.cn-hangzhou.aliyuncs.com/google_containers/pause:3.8"
# edgecore节点配置
[plugins."io.containerd.grpc.v1.cri"]
  sandbox_image = "kubeedge/pause:3.6"
SystemdCgroup = true # 注意不是systemd_cgroup = true！！

# 重启服务
systemctl daemon-reload
systemctl restart containerd
systemctl status containerd
```

#### 2. 配置代理/镜像加速

##### docker镜像加速

使用[阿里云容器镜像服务](https://cr.console.aliyun.com/cn-hangzhou/instances/mirrors)，内有配置文档。

##### containerd配置代理

```sh
cd /etc/systemd/system/containerd.service.d

vim /etc/systemd/system/containerd.service.d/http-proxy.conf
在http-proxy.conf中写入如下配置：

[Service]
Environment="HTTP_PROXY=http://127.0.0.1:65001"
Environment="HTTPS_PROXY=http://127.0.0.1:65001"
Environment="NO_PROXY=127.0.0.1,localhost,10.96.0.0/16,192.168.0.0/16,172.31.0.0/16"


systemctl daemon-reload

systemctl restart containerd
```

##### docker配置代理

```sh
cd /etc/systemd/system/docker.service.d

vim /etc/systemd/system/docker.service.d/http-proxy.conf
在http-proxy.conf中写入如下配置：

[Service]
Environment="HTTP_PROXY=http://127.0.0.1:65001"
Environment="HTTPS_PROXY=http://127.0.0.1:65001"
Environment="NO_PROXY=127.0.0.1,localhost,10.96.0.0/16,192.168.0.0/16,172.31.0.0/16"


systemctl daemon-reload

systemctl restart docker
```

#### 3. 搭建kubernetes集群

如果你一开始安装过k8s，并且有原来的文件残留，你可以用这个过程把它的文件先删光

```sh
sudo apt remove kubelet kubeadm kubectl
sudo rm -rf .kube/config
sudo rm -rf /etc/kubernetes/
sudo rm -r /etc/cni/net.d/
sudo rm -rf /var/lib/etcd/
sudo rm -rf /var/lib/kubelet/
```

可以用清华源，也可以用阿里源，这里使用阿里云的镜像构建 k8s

```sh
sudo apt-get update && sudo apt-get install -y apt-transport-https
curl https://mirrors.aliyun.com/kubernetes/apt/doc/apt-key.gpg | sudo apt-key add -
```

之后将阿里云的镜像地址写到 sources.list 当中

```sh
sudo vim /etc/apt/sources.list.d/kubernetes.list

# 写入下列内容
deb https://mirrors.aliyun.com/kubernetes/apt/ kubernetes-xenial main
```

退出后更新软件包，在ubuntu环境中，安装指定版本的三件套：

```sh
sudo apt-get update
sudo apt-get install -y kubelet=1.27.0-00 kubeadm=1.27.0-00 kubectl=1.27.0-00
```

用下面的初始化，后面的flannel会需要pod-network-cidr参数

```bash
kubeadm init --pod-network-cidr=10.244.0.0/16
```

![](images/eee.png)

这次初始化遇到三个问题

```bash
# 汇总解决方案
sudo modprobe br_netfilter
echo 1 | sudo tee /proc/sys/net/bridge/bridge-nf-call-iptables

echo 1 | sudo tee /proc/sys/net/ipv4/ip_forward
```


首先是 `[WARNING Swap]: swap is enabled; production deployments should disable swap unless testing the NodeSwap feature gate of the kubelet`

需要把虚拟存储交换关掉

```sh
(base) wds@wds-NucBox-K8:~$ sudo swapoff -a
(base) wds@wds-NucBox-K8:~$ sudo vim /etc/fstab
(base) wds@wds-NucBox-K8:~$ sudo mount -a
(base) wds@wds-NucBox-K8:~$ free -h
               total        used        free      shared  buff/cache   available
内存：          28Gi       4.6Gi       532Mi       241Mi        23Gi        23Gi
交换：            0B          0B          0B
```

然后是 `[ERROR FileContent--proc-sys-net-bridge-bridge-nf-call-iptables]: /proc/sys/net/bridge/bridge-nf-call-iptables does not exist`，这是之前配置的 br_netfilter 没有启动，运行下面的命令即可。

```sh
(base) wds@wds-NucBox-K8:~$ sudo modprobe br_netfilter
(base) wds@wds-NucBox-K8:~$ echo 1 | sudo tee /proc/sys/net/bridge/bridge-nf-call-iptables
1
```

**持久化内核参数**

1. 添加 br_netfilter 到模块加载列表：编辑 /etc/modules 文件，确保包含以下内容：

```
br_netfilter
```

2. 持久化内核参数：编辑 /etc/sysctl.conf 文件，添加以下行：

```
net.bridge.bridge-nf-call-iptables=1
```

然后应用更改：

```
sudo sysctl -p
```

这个问题同理 `[ERROR FileContent--proc-sys-net-ipv4-ip_forward]: /proc/sys/net/ipv4/ip_forward contents are not set to 1`

```sh
(base) wds@wds-NucBox-K8:~$ echo 1 | sudo tee /proc/sys/net/ipv4/ip_forward
1
```

解决网络问题：

创建集群时kubeproxy使用`ipvs`模式，也可以在创建`control plane`时解决一直hangs的问题，这需要：

```sh
cat <<EOF >> /etc/sysctl.conf
net.ipv4.ip_forward = 1
net.bridge.bridge-nf-call-iptables = 1
net.bridge.bridge-nf-call-ip6tables = 1
vm.swappiness = 0
EOF

cat <<EOF >> /etc/modules
ip_vs
ip_vs_rr
ip_vs_wrr
ip_vs_sh
nf_conntrack
nf_conntrack_ipv4
nf_conntrack_ipv6
br_netfilter
EOF
```

然后可以先**拉取镜像**

```sh
(base) wds@wds-NucBox-K8:~$ sudo kubeadm config images list
I0503 08:02:18.239000   90461 version.go:256] remote version is much newer: v1.30.0; falling back to: stable-1.27
W0503 08:02:19.105381   90461 images.go:80] could not find officially supported version of etcd for Kubernetes v1.27.13, falling back to the nearest etcd version (3.5.7-0)
registry.k8s.io/kube-apiserver:v1.27.13
registry.k8s.io/kube-controller-manager:v1.27.13
registry.k8s.io/kube-scheduler:v1.27.13
registry.k8s.io/kube-proxy:v1.27.13
registry.k8s.io/pause:3.9
registry.k8s.io/etcd:3.5.7-0
registry.k8s.io/coredns/coredns:v1.10.1


(base) wds@wds-NucBox-K8:~$ sudo kubeadm config images pull --image-repository registry.aliyuncs.com/google_containers
```

若是遇到下面的问题

![](images/eeq.png)

你可以用我上面的命令，用`--image-repository option`来指定拉去的仓库

![](images/aa.png)

然后初始化 `kubeadm init`

![](images/dd.png)

创建`kubeadm-config.yaml`文件：

```yaml
apiVersion: kubeadm.k8s.io/v1beta2
kind: ClusterConfiguration
kubernetesVersion: v1.20.9
controlPlaneEndpoint: 192.168.1.220:6443
imageRepository: registry.cn-hangzhou.aliyuncs.com/google_containers
networking:
  serviceSubnet: 10.96.0.0/16
  podSubnet: 172.31.0.0/16
---
apiVersion: kubeproxy.config.k8s.io/v1alpha1
kind: KubeProxyConfiguration
mode: ipvs
```

并使用kubeadm引导集群创建

```sh
kubeadm init --config kubeadm-config.yaml
```

#### 4. 边端环境配置

除了上面安装containerd，还需要配置cni

下载 CNI 插件版本并解压：

```bash
wget https://github.com/containernetworking/plugins/releases/download/v0.8.2/cni-plugins-linux-amd64-v0.8.2.tgz

# Extract the tarball
mkdir cni
tar -zxvf v0.2.0.tar.gz -C cni

mkdir -p /opt/cni/bin
cp ./cni/* /opt/cni/bin/
```

配置 CNI 插件：

```bash
mkdir -p /etc/cni/net.d/

cat >/etc/cni/net.d/bridge.conf <<EOF
{
  "cniVersion": "0.3.1",
  "name": "containerd-net",
  "type": "bridge",
  "bridge": "cni0",
  "isGateway": true,
  "ipMasq": true,
  "ipam": {
    "type": "host-local",
    "subnet": "10.88.0.0/16",
    "routes": [
      { "dst": "0.0.0.0/0" }
    ]
  }
}
EOF
```

#### 5. 安装kubeedge

[官方安装文档](https://kubeedge.io/zh/docs/setup/keadm_zh/)，[笔记](https://blog.csdn.net/weixin_43168190/article/details/127422527)

```
kubeadm join 192.168.28.45:6443 --token ccs0oj.37ymulijl1ivqmve \
        --discovery-token-ca-cert-hash sha256:38de662d56e65727886268ffc08bd454a2fefa7fb5365770c59a2c2e7054c93c 
```

##### 云端和边缘端 keadm安装：

```bash
wget https://github.com/kubeedge/kubeedge/releases/download/v1.19.0/keadm-v1.19.0-linux-amd64.tar.gz
tar -zxvf keadm-v1.19.0-linux-amd64.tar.gz
cp keadm-v1.19.0-linux-amd64/keadm/keadm /usr/local/bin/keadm
```


下载yaml、包时可能会因为gfw导致中断，只需要在相应路径中补齐即可。

```sh
# 地址形如
https://raw.githubusercontent.com/kubeedge/kubeedge/release-1.17/build/tools/cloudcore.service

https://raw.githubusercontent.com/kubeedge/kubeedge/release-1.17/build/crds/devices/devices_v1alpha2_devicemodel.yaml

# 目录结构
/etc/kubeedge
├── cloudcore.service
├── config
│   └── cloudcore.yaml
├── crds
│   ├── devices
│   │   ├── devices_v1alpha2_devicemodel.yaml
│   │   └── devices_v1alpha2_device.yaml
│   ├── reliablesyncs
│   │   ├── cluster_objectsync_v1alpha1.yaml
│   │   └── objectsync_v1alpha1.yaml
│   └── router
│       ├── router_v1_ruleEndpoint.yaml
│       └── router_v1_rule.yaml
├── kubeedge-v1.12.0-linux-amd64(解压所得)
│   ├── ......
└── kubeedge-v1.12.0-linux-amd64.tar.gz
```

##### 云端：

用下面的初始化，后面的flannel会需要pod-network-cidr参数

```bash
kubeadm init --pod-network-cidr=10.244.0.0/16
```

启动云端

```bash
keadm init --advertise-address=192.168.0.104 --kubeedge-version=v1.19.0 --kube-config=$HOME/.kube/config --set cloudCore.modules.dynamicController.enable=true,cloudCore.featureGates.requireAuthorization=true
# keadm deprecated init --kubeedge-version=1.19.0 --advertise-address=192.168.28.45 --kube-config=$HOME/.kube/config 
# --profile version=v1.19.0

keadm gettoken --kube-config=$HOME/.kube/config 

keadm reset --kube-config=$HOME/.kube/config 

kubectl taint node edge3 node.kubernetes.io/not-ready:NoExecute-
kubectl taint node edge3 node.kubernetes.io/not-ready:NoSchedule-

kubectl drain edge2 --ignore-daemonsets --delete-emptydir-data

```

边端加入

```bash
sudo keadm join --cloudcore-ipport=192.168.0.104:10000 --token=163daa1b34b16c7cd82269195878f279dc81e90457b409dd2d6fbeca0918d521.eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3MzgwNzQ3MzF9.iOd_tTQWSsHW9NBpSMMv29QFt6wIsTm18beS-1J4dvg --kubeedge-version=v1.19.0 --cgroupdriver=systemd --edgenode-name=edge3 --with-mqtt
```


清除边端环境

```bash

sudo systemctl stop edgecore
sudo crictl stopp $(sudo crictl pods -q)
sudo crictl rmp $(sudo crictl pods -q)
sudo crictl rmi $(sudo crictl images -q)

sudo ctr -n k8s.io images list | awk '{if(NR>1) print $1}' | xargs -I {} sudo ctr -n k8s.io images rm {}
sudo ctr -n k8s.io task list | awk '{if(NR>1) print $1}' | xargs -I {} sudo ctr -n k8s.io task kill {}
sudo ctr -n k8s.io containers list | awk '{if(NR>1) print $1}' | xargs -I {} sudo ctr -n k8s.io containers delete {}
kubectl get pods --all-namespaces -o wide | grep edge3 | awk '{print $2" -n "$1}' | xargs -I {} kubectl delete pod {} --grace-period=0 --force


sudo rm -f /var/lib/kubeedge/edgecore.db

# 可以这样进入数据库查看信息
sudo sqlite3 /var/lib/kubeedge/edgecore.db

ubuntu@edge3:~$ 
SQLite version 3.45.1 2024-01-30 16:01:20
Enter ".help" for usage hints.
sqlite> SELECT * FROM meta WHERE type='pod';
```

kubectl apply -f https://raw.githubusercontent.com/kubeedge/kubeedge/master/build/deployment.yaml

cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Service
metadata:
  name: nginx-svc
  namespace: default
spec:
  type: ClusterIP
  selector:
    app: nginx
  ports:
    - name: http-0
      port: 12345
      protocol: TCP
      targetPort: 80
EOF

kubectl run curlpod --image=radial/busyboxplus:curl -i --tty --rm --overrides='{"spec":{"nodeName":"edge3"}}'

sudo iptables -F
sudo iptables -X
sudo iptables -t nat -F
sudo iptables -t nat -X
sudo systemctl restart containerd

##### 边缘端：

```sh
keadm join --cloudcore-ipport=172.31.246.82:10000 --token=token_above

sudo keadm join --cloudcore-ipport=192.168.28.45:10000 --token=c6dba9e325b7ffe37011d5b1faaa51c8ad6a319317079c35e4bd52e097bca898.eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3MzQwMDMwNTd9.8QWQ1lXUUaphDIXKA2dcT1i-tFVMhBS1wM4X4rqWoeg --kubeedge-version=v1.10.0 --cgroupdriver=systemd
```

```bash
docker pull kubeedge/installation-package:v1.17.0
docker save -o installation-package-v1.17.0.tar kubeedge/installation-package:v1.17.0
docker save -o tensorflow_benchmark-v1.4.tar tensorflow_benchmark:v1.4

scp installation-package-v1.17.0.tar ubuntu@edge1:/path/to/destination

sudo ctr -n k8s.io images import /path/to/destination/installation-package-v1.17.0.tar

sudo ctr -n k8s.io images list | grep kubeedge


docker pull kubeedge/edgemesh-agent:v1.17.0

docker save -o edgemesh-agent-v1.17.0.tar kubeedge/edgemesh-agent:v1.17.0

scp edgemesh-agent-v1.17.0.tar ubuntu@192.168.28.58:~/

sudo ctr -n k8s.io images import  edgemesh-agent-v1.17.0.tar
```

##### 验证：

在云端运行，可以看到边缘节点已经加入（以edge,agent身份）。

```
kubectl get nodes
```

##### 边端配置

- https://release-1-19.docs.kubeedge.io/docs/advanced/metrics
- https://release-1-19.docs.kubeedge.io/docs/advanced/debug

### 场景模拟：

#### 1. 云端服务搭建

云端apply `cloud-index-configmap.yaml`

```yaml
kind: ConfigMap
apiVersion: v1
metadata:
  name: index-config
  namespace: default
data:
  index.html: |
    <h1>This is Cloud!</h1>
```

云端apply `cloud-nginx-deployment.yaml`

如果k8s集群中只有一台master，没有worker，则需要考虑节点容忍问题。

```yaml
apiVersion: apps/v1  # API版本
kind: Deployment  # API对象类型
metadata:
  name: nginx-deploy
  namespace: default
spec:
  selector:
    matchLabels:
      app: nginx
  replicas: 3  # Pod 副本数量
  minReadySeconds: 5
  strategy:  
    type: RollingUpdate  # 指定更新策略：RollingUpdate和Recreate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 1
  template:  # Pod 模板
    metadata:
      labels:
        app: nginx
    spec:
      nodeName: cloud-worker
      containers:
      - name: nginx
        image: nginx:1.7.9
        imagePullPolicy: IfNotPresent
        ports:
        - containerPort: 80
        volumeMounts:
        - name: nginx-volume    #自定义的名字和下面保持一致
          mountPath: /usr/share/nginx/html   # nginx 的首页站点目录，挂载点
      volumes:
      - name: nginx-volume     #自定义的名字和上面保持一致
        configMap:
          name: index-config       # cmap资源名称，需要挂载的资源

```

```sh
kubectl taint nodes --all node-role.kubernetes.io/control-plane-
kubectl taint nodes --all node-role.kubernetes.io/master-
```

云端apply `cloud-service-nodeport.yaml`

```yaml
apiVersion: v1
kind: Service
metadata:
  name: cloud-svc
  namespace: default
spec:
  selector:
    app: nginx
  type: NodePort
  ports:
  - port: 8000
    protocol: TCP
    targetPort: 80
    nodePort: 31823
```

#### 2. 边缘端服务搭建

##### 方式一：

云端apply `edge-index-configmap.yaml`

```yaml
kind: ConfigMap
apiVersion: v1
metadata:
  name: edge-index-config
  namespace: default
data:
  index.html: |
    <h1>This is Edge!</h1>
```

云端apply `edge-nginx-deployment.yaml`

pod会起在edge节点上

```yaml
apiVersion: apps/v1  # API版本
kind: Deployment  # API对象类型
metadata:
  name: edge-nginx-deploy
  namespace: default
spec:
  selector:
    matchLabels:
      app: edge-nginx
  replicas: 1  # Pod 副本数量
  minReadySeconds: 5
  strategy:  
    type: RollingUpdate  # 指定更新策略：RollingUpdate和Recreate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 1
  template:  # Pod 模板
    metadata:
      labels:
        app: edge-nginx
    spec:
      hostNetwork: true
      nodeName: edge-node
      containers:
      - name: nginx
        image: nginx:1.7.9
        imagePullPolicy: IfNotPresent
        ports:
        - containerPort: 80
        volumeMounts:
        - name: edge-nginx-volume    #自定义的名字和下面保持一致
          mountPath: /usr/share/nginx/html   # nginx 的首页站点目录，挂载点
      volumes:
      - name: edge-nginx-volume     #自定义的名字和上面保持一致
        configMap:
          name: edge-index-config       # cmap资源名称，需要挂载的资源
```

> kubeedge不支持Service资源类型，运行在edge-nodes上的pod不能架设service，无论是clusterip还是nodeport都不行。
>
> `hostNetwork: true`可以使用户使用主机ip访问到pod。

##### 方式二：

起一个nginx镜像的docker容器

#### 3. 虚服务（nginx代理）实现

在边缘节点的宿主机上，创建数据卷。

```sh
# linux
docker run --name virtual-svc -p 18002:80 -v /home/vsvc-nginx/nginx.conf:/etc/nginx/nginx.conf -v /home/vsvc-nginx/log:/var/log/nginx -v /home/vsvc-nginx/conf.d/default.conf:/etc/nginx/conf.d/default.conf -d nginx:1.7.9

# macos
docker run --name virtual-svc -p 18002:80 -v /Users/njuar/Documents/duhy/vsvc-nginx/nginx.conf:/etc/nginx/nginx.conf -v /Users/njuar/Documents/duhy/vsvc-nginx/log:/var/log/nginx -v /Users/njuar/Documents/duhy/vsvc-nginx/conf.d/default.conf:/etc/nginx/conf.d/default.conf -d nginx:1.7.9

docker exec -it --privileged containerid /bin/bash
```

`nginx.conf`保持镜像默认不变：

```nginx

user  nginx;
worker_processes  1;

error_log  /var/log/nginx/error.log warn;
pid        /var/run/nginx.pid;


events {
    worker_connections  1024;
}


http {
    include       /etc/nginx/mime.types;
    default_type  application/octet-stream;

    log_format  main  '$remote_addr - $remote_user [$time_local] "$request" '
                      '$status $body_bytes_sent "$http_referer" '
                      '"$http_user_agent" "$http_x_forwarded_for"';

    access_log  /var/log/nginx/access.log  main;

    sendfile        on;
    #tcp_nopush     on;

    keepalive_timeout  65;

    #gzip  on;

    include /etc/nginx/conf.d/*.conf;
}
```

`default.conf`

```nginx
upstream realservice {
    server 172.31.246.82:31823;     # 云端服务
    server 172.31.246.81:80 backup; # 边缘服务不跑在本机时可写，断网时不能用
    server 172.17.0.1:80 backup;    # 宿主机服务，彻底断网也能用
}

server {
    listen       80;
    server_name  localhost;

    #charset koi8-r;
    #access_log  /var/log/nginx/log/host.access.log  main;

    location / {
        proxy_pass http://realservice;
    #    root   /usr/share/nginx/html;
    #    index  index.html index.htm;
    }

    #error_page  404              /404.html;

    # redirect server error pages to the static page /50x.html
    #
    error_page   500 502 503 504  /50x.html;
    location = /50x.html {
        root   /usr/share/nginx/html;
    }

    # proxy the PHP scripts to Apache listening on 127.0.0.1:80
    #
    #location ~ \.php$ {
    #    proxy_pass   http://127.0.0.1;
    #}

    # pass the PHP scripts to FastCGI server listening on 127.0.0.1:9000
    #
    #location ~ \.php$ {
    #    root           html;
    #    fastcgi_pass   127.0.0.1:9000;
    #    fastcgi_index  index.php;
    #    fastcgi_param  SCRIPT_FILENAME  /scripts$fastcgi_script_name;
    #    include        fastcgi_params;
    #}

    # deny access to .htaccess files, if Apache's document root
    # concurs with nginx's one
    #
    #location ~ /\.ht {
    #    deny  all;
    #}
}
```

每次更新配置都需要restart一下容器



> 因为本例的nginx是跑在docker中的，这个配置文件最终是放在容器实例中的，如果在里面写localhost，localhost的含义也是nginx容器。
>
> 172.17.0.1的ip是docker容器与宿主机之间通信的虚拟ip，可通过`ifconfig`中的docker0项获取。

涉及的相关文档：

[upstream笔记](https://cloud.tencent.com/developer/article/1027545)

[使用到的nginx官方文档](http://nginx.org/en/docs/http/ngx_http_upstream_module.html)

Fail_timeout的默认时长是10s。

### 其他问题：

[一些别人遇到的问题及解决方法](https://huaweicloud.csdn.net/63563835d3efff3090b5af8a.html?spm=1001.2101.3001.6661.1&utm_medium=distribute.pc_relevant_t0.none-task-blog-2%7Edefault%7EBlogCommendFromBaidu%7Eactivity-1-125609761-blog-123493981.pc_relevant_multi_platform_whitelistv4&depth_1-utm_source=distribute.pc_relevant_t0.none-task-blog-2%7Edefault%7EBlogCommendFromBaidu%7Eactivity-1-125609761-blog-123493981.pc_relevant_multi_platform_whitelistv4&utm_relevant_index=1)

#### 1. nginx容器中安装vim

在容器实例中，

```sh
mv /etc/apt/sources.list /etc/apt/sources.list.bak
echo "deb http://mirrors.163.com/debian/ jessie main non-free contrib" >/etc/apt/sources.list
echo "deb http://mirrors.163.com/debian/ jessie-proposed-updates main non-free contrib" >>/etc/apt/sources.list
echo "deb-src http://mirrors.163.com/debian/ jessie main non-free contrib" >>/etc/apt/sources.list
echo "deb-src http://mirrors.163.com/debian/ jessie-proposed-updates main non-free contrib" >>/etc/apt/sources.list

apt-get update
apt-get install -y vim
```

#### 2. 边缘节点keadm join时，查看日志发现出错，要把edgecore.service停掉

```sh
systemctl stop edgecore

# 确认停止
systemctl status edgecore
```

#### 3. 再次执行keadm join

需要删除/清空`/etc/kubeedge`，删除mqtt容器实例（docker rm containerid）

#### 4. 云端重置

比如由keadm init变成keadm deprecated init时，[官方文档](https://kubeedge.io/zh/docs/setup/keadm_zh/#%E9%87%8D%E7%BD%AEkubeedge-master%E8%8A%82%E7%82%B9%E5%92%8C%E5%B7%A5%E4%BD%9C%E8%8A%82%E7%82%B9)

#### 5. 边缘节点上的pod日志查看

可以配置在云端配置`kubectl logs`，也可以直接查看边缘节点上的日志。

#### 6. 移除一个k8s node

```sh
主节点：
kubectl drain <node-name> --ignore-daemonsets --delete-local-data
kubectl delete node <node-name>
待删除（工作）节点：
kubeadm reset
```

然后按照提示检查一下目录是否都删除干净了

#### 7. 卸载k8s三件套

```sh
apt-mark unhold kubelet=1.20.9-00 kubeadm=1.20.9-00 kubectl=1.20.9-00
apt-get remove kubelet=1.20.9-00 kubeadm=1.20.9-00 kubectl=1.20.9-00
apt-get purge kubelet=1.20.9-00 kubeadm=1.20.9-00 kubectl=1.20.9-00

其他配件使用 docker rmi 移除镜像
```

#### 8. 再次打印join命令

```sh
kubeadm token create --print-join-command
```

#### 9. containerd如何查看k8s拉取的镜像和起的容器

需要添加名称空间namespace

```sh
ctr --namespace k8s.io images ls

ctr --namespace k8s.io containers ls
```

#### 10. 使非root用户也能够使用kubectl

```sh
sudo cp -r /root/.kube $HOME/
(实质是 sudo cp -i /etc/kubernetes/admin.conf $HOME/.kube/config)
sudo chown $(id -u):$(id -g) $HOME/.kube/config
```

#### 11. calico网络插件bird liveness probe failed，说是BGP建立不起联系

Readiness probe failed: calico/node is not ready: BIRD is not ready: Error querying BIRD: unable to connect to BIRDv4 socket: dial unix /var/run/calico/bird.ctl: connect: connection refused

![Bird liveness probe1](/Users/duhy/Documents/NJU/ICS/cloud-edge/Bird liveness probe1.png) 

![Bird liveness probe2](/Users/duhy/Documents/NJU/ICS/cloud-edge/Bird liveness probe2.png)

calico `IP_AUTODETECTION_METHOD`默认是`first found`，当一台机子上还有像172.18.0.1 br开头的docker网桥时，就会BGP联系不上。需要改成正则表达式方式`interface=enp.*`（根据具体情况修改），具体见文档[打开链接后点manifest标签](https://docs.tigera.io/calico/latest/reference/configure-calico-node)，[IP_AUTODETECTION_METHOD](https://docs.tigera.io/calico/latest/reference/configure-calico-node#ip-autodetection-methods)

> 补充：
>
> IPIP和VxLAN方式是互斥的，选了一个就不能是另外一个，VxLAN是一个UDP包，而IPIP对消息使用了自己的封装方式，具体可以参阅[文档](https://www.zentao.pm/blog/kubernetes-network-model-1379.html)。两者的选择对calico能否正常运行照理没有印象，下面使用的是VxLAN。

完整的环境变量如下：

```yaml
          env:
            # Use Kubernetes API as the backing datastore.
            - name: DATASTORE_TYPE
              value: "kubernetes"
            # Wait for the datastore.
            - name: WAIT_FOR_DATASTORE
              value: "true"
            # Set based on the k8s node name.
            - name: NODENAME
              valueFrom:
                fieldRef:
                  fieldPath: spec.nodeName
            # Choose the backend to use.
            - name: CALICO_NETWORKING_BACKEND
              valueFrom:
                configMapKeyRef:
                  name: calico-config
                  key: calico_backend
            # Cluster type to identify the deployment type
            - name: CLUSTER_TYPE
              value: "k8s,bgp"
#！！！重要部分（开始）
            # Auto-detect the BGP IP address.
            - name: IP
              value: "autodetect"
            - name: IP_AUTODETECTION_METHOD
              value: "interface=enp.*"
            # Enable IPIP
            - name: CALICO_IPV4POOL_IPIP
              value: "Never"
            # Enable or Disable VXLAN on the default IP pool.
            - name: CALICO_IPV4POOL_VXLAN
              value: "Always"
            # Enable or Disable VXLAN on the default IPv6 IP pool.
            - name: CALICO_IPV6POOL_VXLAN
              value: "Never"
#！！！重要部分（结束）
            # Set MTU for tunnel device used if ipip is enabled
            - name: FELIX_IPINIPMTU
              valueFrom:
                configMapKeyRef:
                  name: calico-config
                  key: veth_mtu
            # Set MTU for the VXLAN tunnel device.
            - name: FELIX_VXLANMTU
              valueFrom:
                configMapKeyRef:
                  name: calico-config
                  key: veth_mtu
            # Set MTU for the Wireguard tunnel device.
            - name: FELIX_WIREGUARDMTU
              valueFrom:
                configMapKeyRef:
                  name: calico-config
                  key: veth_mtu
            # The default IPv4 pool to create on startup if none exists. Pod IPs will be
            # chosen from this range. Changing this value after installation will have
            # no effect. This should fall within `--cluster-cidr`.
            # - name: CALICO_IPV4POOL_CIDR
            #   value: "192.168.0.0/16"
            # Disable file logging so `kubectl logs` works.
            - name: CALICO_DISABLE_FILE_LOGGING
              value: "true"
            # Set Felix endpoint to host default action to ACCEPT.
            - name: FELIX_DEFAULTENDPOINTTOHOSTACTION
              value: "ACCEPT"
            # Disable IPv6 on Kubernetes.
            - name: FELIX_IPV6SUPPORT
              value: "false"
            - name: FELIX_HEALTHENABLED
              value: "true"
```

#### 12. 网络插件安装正常，但worker节点一直NotReady，kubectl describe node nodename 显示

runtime network not ready: NetworkReady=false reason:NetworkPluginNotReady message:Network plugin returns error: cni plugin not initialized



在worker节点上尝试

```sh
systemctl stop apparmor 
systemctl disable apparmor 
systemctl restart containerd
```

(更新)

通过查看kubelet日志

```sh
journalctl -f -u kubelet
```

发现它会报"RemoveContainer from runtime service failed"Error，它尝试移除container但发现要移除的container已经not found的，此时重启containerd服务

```sh
systemctl restart containerd
```

就可以解决上述问题，所以有可能是第三行

#### 13. docker配置代理

见上

### 总结

总结一些排错的方法

```sh
kubectl describe {{resource type}} {{name}} -n {{namespace}}

kubectl get {{resource type}} {{name}} -n {{namespace}} -o yaml

针对pod
kubectl logs {{pod name}} -n {{namespace}}

查看kubelet日志
journalctl -f -u kubelet

重启containerd、重启kubelet
systemctl restart containerd

systemctl restart kubelet
```

