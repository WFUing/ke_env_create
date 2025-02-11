# 使用 Python 基础镜像
FROM python:3.9-slim

# 设置工作目录
WORKDIR /app

# 复制项目文件到工作目录
COPY network_test.py .

RUN apt-get update && apt-get install -y iputils-ping iperf3

# 安装所需的依赖
RUN pip install paho-mqtt

# 运行 Python 脚本
CMD ["python", "network_test.py"]
