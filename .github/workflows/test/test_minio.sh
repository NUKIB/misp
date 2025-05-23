#/bin/bash

# Script for testing MinIO connection:
# - Spins up a MinIO container and creates a bucket
# - Add event to MISP
# - Add attachment to event
# - Check that attachment has been stored in MinIO bucket 

# MinIO container is put on same bridge network as MISP
# MinIO client (mc) and MISP REST API is used 

set -e

MINIO_ROOT_USER=$1
MINIO_ROOT_PASSWORD=$2
BUCKET_NAME=$3
AUTHKEY=$4
if [ `arch` == "x86_64" ]; then MINIO_ARCH=amd64; else MINIO_ARCH=arm64; fi

if [[ (-z MINIO_ROOT_USER) || (-z MINIO_ROOT_PASSWORD) || (-z BUCKET_NAME) || (-z AUTHKEY) ]]; then
    echo "Missing env vars: "  $MINIO_ROOT_USER "/" $MINIO_ROOT_PASSWORD "/" $BUCKET_NAME "/" $AUTHKEY
fi


echo "Setup MinIO container"
NETWORK=$(docker inspect misp --format="{{ .HostConfig.NetworkMode }}")
docker run -d --expose 9000 --network $NETWORK -e MINIO_ROOT_USER=$MINIO_ROOT_USER -e MINIO_ROOT_PASSWORD=$MINIO_ROOT_PASSWORD --quiet --name minio quay.io/minio/minio:latest server /data

echo "Ensure MinIO client exists"
curl -o ./mc -# https://dl.min.io/client/mc/release/linux-${MINIO_ARCH}/mc && chmod +x ./mc

echo "Create bucket"
MINIO_IP=$(docker inspect minio --format="{{ .NetworkSettings.Networks.$NETWORK.IPAddress }}")
python3 .github/workflows/wait.py --ignore-http-error http://$MINIO_IP:9000
echo "Minio IP" $MINIO_IP
./mc alias set minio http://$MINIO_IP:9000 $MINIO_ROOT_USER $MINIO_ROOT_PASSWORD
./mc mb minio/$BUCKET_NAME 

echo "Create event"
curl -X POST -H "Authorization: $AUTHKEY"  -H "Accept: application/json" -H "Content-type: application/json" --data "@.github/workflows/test/add_event.json" http://localhost:8080/events/add -o ./resp_event.json
EVENT_ID=$(cat ./resp_event.json | jq .[] | jq ."id" | tr -d '"')

echo "Add attachment to event"
echo "{\"msg\": \"Hello World\"}" > ./send.json
DATA=$(cat ./send.json | base64)
FILENAME=testfile
echo "{\"request\":{\"files\":[{\"filename\":\"$FILENAME\",\"data\":\"$DATA\"}], \"category\":\"Payload delivery\",\"info\":\"some info\"}}" > ./obj.json
until curl -X POST -H "Authorization: $AUTHKEY" -H "Accept: application/json" -H "Content-type: application/json" --data "@./obj.json" --write-out "%{http_code}" http://localhost:8080/events/upload_sample/$EVENT_ID  | grep -q "200"; do echo -n "."; sleep 5; done; echo " done"

echo "Download attachment from bucket"
OBJ=$(./mc find minio/$BUCKET_NAME/$EVENT_ID)
if [[ -z $OBJ ]]; then
    echo "Found no objects in bucket"
    exit 1
fi
./mc get $OBJ saved.zip
unzip -P "infected" saved.zip -d ./saved
FETCHED=$(cat ./saved/*.filename.txt)
if [[ "$FETCHED" -eq "$FILENAME" ]]; then
    echo "Equal"
else
    echo "Fetched obj and sent object not the same"
    exit 1
fi

echo "Stop MinIO container"
docker stop minio