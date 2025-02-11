export OTHER_NODES_IPS="192.168.0.102"
export SLEEP_TIME=30
export CURRENT_NODE_IP="192.168.0.104"

docker build -t september9/network-test:v1.0 .
docker run -d \
  -e CURRENT_NODE_IP="192.168.0.102" \
  -e OTHER_NODES_IPS="192.168.0.104" \
  -e SLEEP_TIME=60 \
  --name network-test-instance \
  network-test:v1.0

docker tag network-test:v1.0 september9/network-test:v1.0

docker push september9/network-test:v1.0