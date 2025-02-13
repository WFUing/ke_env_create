## 部署

```sh
kubectl apply -f build/crds/istio/
kubectl apply -f build/agent/resources/
kubectl get all -n kubeedge -o wide

kubectl delete -f build/crds/istio/
kubectl delete -f build/agent/resources/

openssl rand -base64 32
```

## 文档

- https://edgemesh.netlify.app/zh/
- https://zhuanlan.zhihu.com/p/585749690

kubectl delete -f https://raw.githubusercontent.com/kubeedge/kubeedge/master/build/deployment.yaml

cat <<EOF | kubectl delete -f -
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