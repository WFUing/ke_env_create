# ke-prom
 
在我的kubeedge中只需要部署 prometheus 和 push-gateway 即可

[kube-promethues](https://github.com/prometheus-operator/kube-prometheus.git) 是一个开源的项目，在 kubeedge 中这些不能部署

- grafana
- kube-state-metrics
- prometheus-adapter
- prometheus-operator

```shell
# Create the namespace and CRDs, and then wait for them to be available before creating the remaining resources
# Note that due to some CRD size we are using kubectl server-side apply feature which is generally available since kubernetes 1.22.
# If you are using previous kubernetes versions this feature may not be available and you would need to use kubectl create instead.
kubectl apply --server-side -f kube-promethues/manifests/setup
kubectl wait \
	--for condition=Established \
	--all CustomResourceDefinition \
	--namespace=monitoring
kubectl apply -f kube-promethues/manifests/
```

## 说明

- prometheus：部署Promethues Metrics API Server所需要的各资源配置清单。
- prometheus-adapter：部署基于prometheus的自定义指标API服务器所需要的各资源配置清单。
- podinfo：测试使用的podinfo相关的deployment和service对象的资源配置清单。
- node_exporter：于kubernetes集群各节点部署node_exporter。
- kube-state-metrics：聚合kubernetes资源对象，提供指标数据。
- alertmanager：部署AlertManager告警系统。

### 部署Prometheus

部署Prometheus监控系统

```bash
kubectl apply -f namespace.yaml
kubectl apply -f prometheus/ -n monitoring
```

删除

```bash
kubectl delete -f prometheus/ -n monitoring
```

查看Prometheus的configmap

```bash
kubectl describe configmap prometheus-config -n monitoring
```

实现 k8s node-port转发 

```bash
kubectl port-forward -n monitoring service/grafana 3000:3000

kubectl port-forward -n monitoring service/prometheus 9090:9090
```

实现 Prometheus 数据查询

```bash
curl -G 'http://127.0.0.1:9090/api/v1/query' --data-urlencode 'query=rate(node_network_receive_bytes_total[5m])'
```

### 部署push-gateway

```bash
kubectl apply -f push-gateway
```

### 部署node-exporter

```bash
kubectl apply -f node-exporter/
```

### 部署Kube-State-Metrics

部署kube-state-metrics，监控Kubernetes集群的服务指标。

```bash
kubectl apply -f kube-state-metrics/
```

### 部署AlertManager

部署AlertManager，为Prometheus-Server提供可用的告警发送服务。

```bash
kubectl apply -f alertmanager/
```

### 部署Prometheus Adpater

参考相关目录中的[README](prometheus-adpater/README.md)文件中的部署说明。



