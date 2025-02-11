import os
from flask import Flask, request, jsonify
from prometheus_client import CollectorRegistry, Gauge, push_to_gateway

# 从环境变量读取 Pushgateway 地址和 Flask 服务端口
PUSHGATEWAY_URL = os.getenv("PUSHGATEWAY_URL", "http://localhost:30091")  # 默认值为 localhost:9091
FLASK_PORT = int(os.getenv("FLASK_PORT", 8080))  # 默认端口为 18080

app = Flask(__name__)

@app.route('/network', methods=['POST'])
def handle_message():
    try:
        data = request.get_json(force=True)
        print(f"Received message: {data}")
        push_metrics(data)
        return jsonify({"status": "success", "received_data": data}), 200
    except Exception as e:
        print(f"Error processing request: {e}")
        return jsonify({"status": "failed", "message": "Invalid JSON format"}), 400

def push_metrics(data):
    registry = CollectorRegistry()
    ping_time_gauge = Gauge(
        'network_ping_time', 'Ping time between IPs',
        ['source_ip', 'target_ip'], registry=registry
    )
    bandwith_gauge = Gauge(
        'network_bandwidth', 'Network bandwidth between IPs',
        ['source_ip', 'target_ip'], registry=registry
    )

    source_ip = data['ip']
    for target_ip, metrics in data['data'].items():
        ping_time = float(metrics['ping_time'])
        bandwith = float(metrics['bandwith'])
        ping_time_gauge.labels(source_ip=source_ip, target_ip=target_ip).set(ping_time)
        bandwith_gauge.labels(source_ip=source_ip, target_ip=target_ip).set(bandwith)

    try:
        push_to_gateway(PUSHGATEWAY_URL, job='network_test', registry=registry)
        print(f"Metrics successfully pushed to Pushgateway at {PUSHGATEWAY_URL}")
    except Exception as e:
        print(f"Failed to push metrics: {e}")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=FLASK_PORT)  # 使用从环境变量获取的端口
