import subprocess
import os
import time
import json
import paho.mqtt.client as mqtt

# 从环境变量中获取当前节点的 IP 地址
current_node_ip = os.getenv('CURRENT_NODE_IP')
if not current_node_ip:
    print("CURRENT_NODE_IP environment variable is not set.")
    exit(1)

# 获取集群内其他节点的 IP 地址列表
# 这里简单假设你已经通过某种方式获取到了所有节点的 IP 地址，存储在一个环境变量中
other_nodes_ips = os.getenv('OTHER_NODES_IPS', '').split(',')

# 获取 sleep 时间，默认为 60 秒
try:
    sleep_time = int(os.getenv('SLEEP_TIME', 60))
except ValueError:
    print("Invalid value for SLEEP_TIME environment variable. Using default value of 60 seconds.")
    sleep_time = 60

# MQTT 配置
MQTT_BROKER = "localhost"  # Mosquitto 服务器地址
MQTT_PORT = 1883
MQTT_TOPIC = "default/network"

# 创建 MQTT 客户端
client = mqtt.Client()
client.connect(MQTT_BROKER, MQTT_PORT, 60)


def parse_ping_time(output):
    """
    从 ping 输出中解析出时延
    """
    lines = output.splitlines()
    for line in lines:
        if "time=" in line:
            try:
                start = line.index("time=") + len("time=")
                end = line.index(" ms", start)
                return float(line[start:end])
            except (ValueError, IndexError):
                pass
    return None


def estimate_bandwidth(target_ip):
    """
    使用 iperf3 估算带宽
    """
    try:
        result = subprocess.run(['iperf3', '-c', target_ip, '-t', '5'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output = result.stdout.decode('utf-8')
        lines = output.splitlines()
        for line in reversed(lines):
            if "receiver" in line:
                parts = line.split()
                bandwidth_index = parts.index("Mbits/sec") - 1
                return float(parts[bandwidth_index])
    except Exception as e:
        print(f"Error estimating bandwidth to {target_ip}: {e}")
    return None


while True:
    data = {
        "type": "network_test",
        "ip": current_node_ip,
        "data": {}
    }

    for target_ip in other_nodes_ips:
        if target_ip != current_node_ip:
            try:
                # 执行 ping 命令
                result = subprocess.run(['ping', '-c', '1', target_ip], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                output = result.stdout.decode('utf-8')
                ping_time = parse_ping_time(output)

                # 估算带宽
                bandwidth = estimate_bandwidth(target_ip)

                data["data"][target_ip] = {
                    "ping_time": str(ping_time) if ping_time is not None else "N/A",
                    "bandwith": str(bandwidth) if bandwidth is not None else "N/A"
                }

            except Exception as e:
                print(f"Error pinging {target_ip}: {e}")
                data["data"][target_ip] = {
                    "ping_time": "N/A",
                    "bandwith": "N/A"
                }

    # 将数据转换为 JSON 格式
    json_data = json.dumps(data, ensure_ascii=False)

    print(json_data)

    # 发布消息到 MQTT 主题
    client.publish(MQTT_TOPIC, json_data)

    time.sleep(sleep_time)  # 每隔 sleep_time 秒执行一次 ping 操作