# 🌌 DICOM Image Analysis with gRPC 🏥

![Python](https://img.shields.io/badge/python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![gRPC](https://img.shields.io/badge/gRPC-4285F4?style=for-the-badge&logo=grpc&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/postgres-336791?style=for-the-badge&logo=postgresql&logoColor=white)
![Docker](https://img.shields.io/badge/docker-2496ED?style=for-the-badge&logo=docker&logoColor=white)
![Kubernetes](https://img.shields.io/badge/kubernetes-326CE5?style=for-the-badge&logo=kubernetes&logoColor=white)
![Prometheus](https://img.shields.io/badge/prometheus-E6522C?style=for-the-badge&logo=prometheus&logoColor=white)
![Grafana](https://img.shields.io/badge/grafana-F46800?style=for-the-badge&logo=grafana&logoColor=white)

## 📖 Table of Contents
1. [Introduction](#1-introduction)
2. [Technologies Used](#2-technologies-used)
3. [Architecture Overview](#3-architecture-overview)
4. [Docker Installation & Deployment](#4-docker-installation--deployment)
   - [Pull Docker Containers](#41-pull-docker-containers)
   - [Start Services](#42-start-services)
   - [Prometheus & Grafana Setup](#43-prometheus--grafana-setup)
5. [Microservices Overview](#5-microservices-overview)
6. [Testing & Verification](#6-testing--verification)
7. [Kubernetes Deployment](#7-kubernetes-deployment)
   - [Kubernetes Components](#71-kubernetes-components)
   - [Kubernetes Deployment Files](#72-kubernetes-deployment-files)
   - [Deployment Process](#73-deployment-process)
   - [Verifying Deployment](#74-verifying-deployment)
   - [Next Steps](#75-next-steps)
8. [Development Tools](#8-development-tools)
9. [Future Enhancements](#9-future-enhancements)


1️⃣ Introduction

This project consists of **gRPC-based microservices** that analyze technical image quality of ultrasound air images **DICOM** on a CSC virtual server. 

Project provides both Docker and Kubernetes deployments.

If you want to deploy using Docker, see Section 4.
If you want to deploy using Kubernetes, see Section 7.

The architecture is composed of three main services:
- 🏷 **fetch_service (Worker-Node1)** – Retrieves DICOM images from the **Orthanc server**.
- 🛠 **analyze_service (Worker-Node2)** – Processes images and stores results in the database.
- 🐄 **PostgreSQL (Master-Node)** – Stores the analysis results.
- 🏥 **Orthanc (Master-Node)** - Stores ultrasound DICOM images.

---

2️⃣ 📌 Technologies Used
- ✅ **gRPC** – Efficient and fast communication between microservices  
- ✅ **Docker & Docker Hub** – Container management and deployment to CSC  
- ✅ **PostgreSQL** – Database for storing analysis results  
- ✅ **Python & pydicom** – DICOM image processing
- :x: **Kubernetes** – In progress
- :x: **Prometheus** – In progress
- :x: **Grafana** – In progress

---

3️⃣ 🔥 Architecture
```
[Orthanc]  → [fetch_service]  →  [analyze_service]  →  [PostgreSQL]
(Master-node) (Worker-Node1)      (Worker-Node2)       (Master-Node)
```
- **fetch_service** retrieves images from **Orthanc**.
- **analyze_service** processes the images and stores the results in the database.
- **PostgreSQL** stores the analysis data.

---

4️⃣ 🚀 Docker Installation & Deployment

## 4.1 Pull Docker Containers from Docker Hub
Log in to each CSC server and pull the necessary containers:

```sh
docker pull skullervo/fetch_service:latest
docker pull skullervo/analyze_service:latest
docker pull skullervo/postgres:latest
```

## 4.2 Start the Services

#### Start `fetch_service` on Worker-Node1:
```sh
sudo docker run -d --name fetch_service -p 50051:50051 skullervo/fetch_service:latest
```

#### Start `analyze_service` on Worker-Node2:
```sh
sudo docker run -d --name analyze_service -p 50052:50052 \
    -e FETCH_SERVICE_URL="worker-node1-ip:50051" \
    -e POSTGRES_HOST="master-node-ip" \
    -e POSTGRES_USER="<your_username>" \
    -e POSTGRES_PASSWORD="<your_psw>" \
    -e POSTGRES_DB="QA-results" \
    skullervo/analyze_service:latest
```

#### Start `PostgreSQL` on Master-Node:
```sh
sudo docker run -d --name postgres -p 5432:5432 \
    -e POSTGRES_USER=<your_username> \
    -e POSTGRES_PASSWORD=<your_psw> \
    -e POSTGRES_DB=QA-results \
    skullervo/postgres:latest
```


#### Start `Orthanc` on Master-Node:
```sh
sudo docker run -d --name orthanc -p 8050:8042 -p 4243:4242 \
    -v orthanc-data:/var/lib/orthanc \
    -v ~/orthanc.json:/etc/orthanc/orthanc.json \
    skullervo/orthanc:master1
```

#### Start `Prometheus`:
```sh
sudo docker run -d --name=prometheus -p 9090:9090 prom/prometheus
```

#### `Prometheus` yaml configuration:
```sh
global:
  scrape_interval: 15s  # Kuinka usein dataa kerätään

scrape_configs:
  - job_name: 'master-node'
    static_configs:
      - targets: ['ip:9090']

  - job_name: 'worker-node1'
    static_configs:
      - targets: ['ip:9090']  

  - job_name: 'worker-node2'
    static_configs:
      - targets: ['ip:9090']  

  - job_name: 'analyze_service'
    static_configs:
      - targets: ['ip:50053']  

  - job_name: 'fetch_service'
    static_configs:
      - targets: ['ip:50054']  
```

#### Start `Grafana`:
```sh
sudo docker run -d --name=grafana -p 3000:3000 grafana/grafana
```

---

5️⃣ Microservices Overview

| **Service**         | **Node**      | **Port**  | **Function**                                       |
|---------------------|---------------|-----------|----------------------------------------------------|
| **Orthanc**         | Master-node   | `8082`    | Stores DICOM images                                |
| **fetch_service**   | Worker-Node1  | `50051`   | Retrieves DICOM images from Orthanc                |
| **analyze_service** | Worker-Node2  | `50052`   | Analyzes images and stores results in the database |
| **PostgreSQL**      | Master-Node   | `5432`    | Stores analysis results                            |


---

6️⃣ Testing & Verification

### 1⃣ Test Fetch Service (`worker-node1`)
```sh
grpcurl -plaintext worker-node1-ip:50051 list
```

### 2⃣ Test Analyze Service (`worker-node2`)
```sh
grpcurl -plaintext worker-node2-ip:50052 list
```

### 3⃣ Test PostgreSQL Connection (`master-node`)
```sh
psql -h master-node-ip -U postgres -d QA-results -c "\dt"
```

### 4⃣ Test the Entire System
Run the test script:
```sh
python test_analyze_service.py
```

✅ **If the analysis runs successfully, the entire system is working in CSC!** 🎉

---

7️⃣ Kubernetes Installation & Deployment

Sure! Here’s the **Kubernetes Deployment** section in English with a structured format that fits well into your README.

---

# 7️⃣ **Kubernetes Deployment**
Kubernetes allows us to manage our microservices architecture in a distributed and scalable manner.

## 7.1 **Kubernetes Components**
Each service runs as a separate **Deployment**, and they communicate through **Service** resources.  

The required components are:
- **Deployment** (`fetch_service`, `analyze_service`, `postgres`, `orthanc`, `prometheus`, `grafana`)
- **Service** (for exposing ports)
- **ConfigMap** (for managing environment variables)
- **Persistent Volume** (for PostgreSQL and Orthanc)
- **Ingress Controller** (for external access)

---

## 7.2 **Kubernetes Deployment Files**
Below are Kubernetes YAML manifests for deploying the services.

### 7.2.1 **fetch_service Deployment**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: fetch-service
spec:
  replicas: 1
  selector:
    matchLabels:
      app: fetch-service
  template:
    metadata:
      labels:
        app: fetch-service
    spec:
      containers:
      - name: fetch-service
        image: skullervo/fetch_service:latest
        ports:
        - containerPort: 50051
        env:
        - name: ORTHANC_URL
          value: "http://orthanc-service:8042"
---
apiVersion: v1
kind: Service
metadata:
  name: fetch-service
spec:
  selector:
    app: fetch-service
  ports:
    - protocol: TCP
      port: 50051
      targetPort: 50051
```

### 7.2.2 **analyze_service Deployment**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: analyze-service
spec:
  replicas: 1
  selector:
    matchLabels:
      app: analyze-service
  template:
    metadata:
      labels:
        app: analyze-service
    spec:
      containers:
      - name: analyze-service
        image: skullervo/analyze_service:latest
        ports:
        - containerPort: 50052
        env:
        - name: FETCH_SERVICE_URL
          value: "fetch-service:50051"
        - name: POSTGRES_HOST
          value: "postgres-service"
        - name: POSTGRES_USER
          valueFrom:
            secretKeyRef:
              name: db-secret
              key: username
        - name: POSTGRES_PASSWORD
          valueFrom:
            secretKeyRef:
              name: db-secret
              key: password
        - name: POSTGRES_DB
          value: "QA-results"
---
apiVersion: v1
kind: Service
metadata:
  name: analyze-service
spec:
  selector:
    app: analyze-service
  ports:
    - protocol: TCP
      port: 50052
      targetPort: 50052
```

### 7.2.3 **PostgreSQL Deployment**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: postgres
spec:
  replicas: 1
  selector:
    matchLabels:
      app: postgres
  template:
    metadata:
      labels:
        app: postgres
    spec:
      containers:
      - name: postgres
        image: skullervo/postgres:latest
        ports:
        - containerPort: 5432
        env:
        - name: POSTGRES_USER
          valueFrom:
            secretKeyRef:
              name: db-secret
              key: username
        - name: POSTGRES_PASSWORD
          valueFrom:
            secretKeyRef:
              name: db-secret
              key: password
        - name: POSTGRES_DB
          value: "QA-results"
---
apiVersion: v1
kind: Service
metadata:
  name: postgres-service
spec:
  selector:
    app: postgres
  ports:
    - protocol: TCP
      port: 5432
      targetPort: 5432
```

### 7.2.4 **Secrets for PostgreSQL**
Use **Kubernetes Secrets** to store sensitive data instead of hardcoding them.

**db-secret.yaml**
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: db-secret
type: Opaque
data:
  username: cG9zdGdyZXM=  # Base64-encoded "postgres"
  password: cG9oZGUyNA==  # Base64-encoded "pohde24"
```

💡 **Using Kubernetes Secrets prevents exposing credentials directly in YAML files.**

---

## 7.3 **Deployment Process**
Once the YAML files are ready, apply them to the Kubernetes cluster:

1. **Create a Kubernetes Namespace**
   ```sh
   kubectl create namespace dicom-analysis
   ```
2. **Apply Secrets and ConfigMaps**
   ```sh
   kubectl apply -f db-secret.yaml --namespace=dicom-analysis
   ```
3. **Deploy PostgreSQL and Orthanc**
   ```sh
   kubectl apply -f postgres.yaml --namespace=dicom-analysis
   ```
4. **Deploy fetch_service and analyze_service**
   ```sh
   kubectl apply -f fetch_service.yaml --namespace=dicom-analysis
   kubectl apply -f analyze_service.yaml --namespace=dicom-analysis
   ```

---

## 7.4 **Verifying Deployment**
Check that all services are running:
```sh
kubectl get pods -n dicom-analysis
kubectl get services -n dicom-analysis
```

Ensure that all pods are in a `Running` state.

---

## ✅ **Next Steps**
- 🔄 **Autoscaling**: `kubectl autoscale deployment analyze-service --cpu-percent=80 --min=1 --max=5`
- 🌍 **Ingress Controller** (for external access)
- 📊 **Grafana Dashboard** (visualizing Prometheus metrics)
- 🏎 **HPA (Horizontal Pod Autoscaler)** (scaling based on load)

---

💡 **Now your README includes a well-structured Kubernetes section in English!** 🚀 You can expand this further by adding monitoring and autoscaling in future updates. Let me know if you need refinements! 😊

---

8️⃣ 🛠 Development Tools
- 🐍 **Python** (`pydicom`, `grpcio`, `grpcio-tools`)
- 🐳 **Docker**
- 🐄 **PostgreSQL**
- 🏥 **Orthanc (DICOM server)**

---

9️⃣ 📜 Future Enhancements
- 🔄 **Asynchronous communication for the analysis service** (Kafka no longer needed due to gRPC)
- 🔍 **Logging and error handling improvements**
- 📊 **Grafana monitoring for microservices**

---

## 🤝 Contact & Contributions
👤 **Skullervo**  
  


