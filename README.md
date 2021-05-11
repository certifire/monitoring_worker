Certifire Monitoring Worker (certmon)
=========

Installation
------------

Install dependencies: 

(Debian/Ubuntu and derivatives)

    $ sudo apt update && sudo apt upgrade
    $ sudo apt install git nginx 

### Select one of the following methods

<details>
<summary>Legacy Installation (Tested on Ubuntu 20.04)</summary>

### Legacy Installation
After cloning, create a virtual environment and install the requirements. For Linux and Mac users:

    $ sudo apt install python3-dev python3-pip python3-virtualenv build-essential
    $ git clone https://github.com/certifire/monitoring_worker.git
    $ virtualenv -p python3 monitoring_worker
    $ source monitoring_worker/bin/activate
    $ cd monitoring_worker
    (monitoring_worker) $ pip install -r requirements.txt

Configuring

    $ cp env_sample.json env.json

Make appropriate changes to env.json

Running

    (monitoring_worker) $ python worker.py

To run certifire as a service:

    $ sudo cp certmon.service /etc/systemd/system/
    $ sudo systemctl daemon-reload
    $ sudo systemctl enable --now certmon

</details>

<details>
<summary>Docker Installation (Tested on Ubuntu 20.04)</summary>

Install docker and docker-compose

    $ sudo apt install docker docker-compose
    $ sudo groupadd docker
    $ sudo usermod -aG docker ${USER}

Log out and Log back in so that your group membership is re-evaluated. 
More info: [Docker Docs](https://docs.docker.com/engine/install/linux-postinstall/#manage-docker-as-a-non-root-user)

You also may stop existing certmon instance if present because,
it will confilict with the postgres and certifire docker instance

    $ sudo systemctl disable --now certmon

Now we build our docker image

    $ git clone https://github.com/certifire/monitoring_worker.git certmon
    $ cd certmon
    $ docker-compose build

Run the container:

    $ docker-compose up -d

If you want to stream the logs (You can press ctrl+c to quit streaming):

    $ docker-compose logs -tf server

</details>
<br>
