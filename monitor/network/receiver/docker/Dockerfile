# 使用轻量级 Python 基础镜像
FROM python:3.9-slim

# 设置工作目录
WORKDIR /app

# 复制当前目录的内容到容器中
COPY receiver.py .

# 安装所需的 Python 库
RUN pip install --no-cache-dir flask prometheus_client

# 暴露服务端口（通过环境变量控制）
EXPOSE 18080

# 启动应用程序（通过环境变量传递端口和 Pushgateway URL）
CMD ["python", "receiver.py"]
