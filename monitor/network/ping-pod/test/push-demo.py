import requests
from prometheus_client import CollectorRegistry, Gauge, push_to_gateway

# Pushgateway 地址（ClusterIP 地址和端口）
PUSHGATEWAY_URL = "http://192.168.0.104:30091"

def push_metrics(data):
    """
    将接收到的网络测试数据推送到 Pushgateway。
    
    :param data: 网络测试数据，格式为
        {
            'type': 'network_test',
            'ip': '192.168.0.102',
            'data': {
                '192.168.0.104': {'ping_time': '119.0', 'bandwith': '174.0'},
                ...
            }
        }
    """
    # 创建 Prometheus 指标注册表
    registry = CollectorRegistry()

    # 定义两个指标：ping_time 和 bandwith
    ping_time_gauge = Gauge(
        'network_ping_time', 'Ping time between IPs',
        ['source_ip', 'target_ip'], registry=registry
    )
    bandwith_gauge = Gauge(
        'network_bandwidth', 'Network bandwidth between IPs',
        ['source_ip', 'target_ip'], registry=registry
    )

    # 解析数据并设置指标值
    source_ip = data['ip']
    for target_ip, metrics in data['data'].items():
        ping_time = float(metrics['ping_time'])
        bandwith = float(metrics['bandwith'])

        # 设置指标值
        ping_time_gauge.labels(source_ip=source_ip, target_ip=target_ip).set(ping_time)
        bandwith_gauge.labels(source_ip=source_ip, target_ip=target_ip).set(bandwith)

    # 推送指标到 Pushgateway
    try:
        push_to_gateway(PUSHGATEWAY_URL, job='network_test', registry=registry)
        print(f"Metrics successfully pushed to Pushgateway at {PUSHGATEWAY_URL}")
    except Exception as e:
        print(f"Failed to push metrics: {e}")

# 示例数据
http_data = {
    'type': 'network_test',
    'ip': '192.168.0.102',
    'data': {
        '192.168.0.104': {'ping_time': '119.0', 'bandwith': '174.0'},
        '192.168.0.105': {'ping_time': '130.5', 'bandwith': '162.0'}
    }
}

# 调用函数推送数据
push_metrics(http_data)
