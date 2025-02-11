#!/bin/bash

# 获取当前节点的 IP 地址
CURRENT_NODE_IP=$(kubectl get node $(hostname) -o jsonpath='{.status.addresses[?(@.type=="InternalIP")].address}')

# 获取所有节点的 IP 地址
ALL_NODES_IPS=$(kubectl get nodes -o jsonpath='{.items[*].status.addresses[?(@.type=="InternalIP")].address}')

# 排除当前节点的 IP 地址
OTHER_NODES_IPS=$(echo $ALL_NODES_IPS | tr ' ' '\n' | grep -v $CURRENT_NODE_IP | tr '\n' ',')
OTHER_NODES_IPS=${OTHER_NODES_IPS%,}  # 去除最后一个逗号

echo $OTHER_NODES_IPS