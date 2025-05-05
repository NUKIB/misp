# How to use MISP in air-gap environment

MISP by default does not require access to the Internet. So it is possible to use MISP in an air-gapped environment or
an environment with blocked outgoing connections. Easies way how to do that is to export container images to compressed tar
and transfer them to an air-gapped system.

Both machines can be any system that is supported by Docker, so Windows, macOS, or Linux are supported.

## Installation

### On machine connected to the internet

* [Install Docker](https://docs.docker.com/get-docker/)
* Create a new working directory like `misp`
* Download [docker-compose.yml](docker-compose.yml) file to the working directory:

  `curl --proto '=https' --tlsv1.2 -O https://raw.githubusercontent.com/NUKIB/misp/main/docker-compose.yml`

* In a working directory, pull all images defined in `docker-compose.yml`:

  `docker compose pull`

* Export all images to `misp.tar` file:
  
  `docker save -o misp.tar mariadb:11.5 redis:7.4 ghcr.io/nukib/misp-modules:latest ghcr.io/nukib/misp:latest`

* Transfer whole directory (`misp.tar` and `docker-compose.yml` files) to air gapped system

### On a machine without internet connection

* [Install Docker](https://docs.docker.com/get-docker/)
* In a working directory transferred from previous machine, import images:
    
  `docker load -i misp.tar`
* Start all containers:

  `docker compose up -d`
* MISP should be ready and accessible from `http://localhost:8080`.

## Updating

### On machine connected to the internet

* In a working directory, pull new images defined in `docker-compose.yml`:

  `docker compose pull`

* Export new images to files:
    * `docker save -o misp-modules.tar ghcr.io/nukib/misp-modules:latest`
    * `docker save -o misp.tar ghcr.io/nukib/misp:latest`
* Transfer these files to air gapped system

### On a machine without internet connection

* In a working directory transferred from the previous machine, import images
    * `docker load -i misp-modules.tar`
    * `docker load -i misp.tar`
* Recreate changed containers:

  `docker compose up -d`
* New MISP should be ready and accessible from `http://localhost:8080`.
