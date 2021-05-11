#!/home/certifire/monitoring_worker/bin/python

import http.server
import json
import os
import socketserver
import time
from functools import partial
from threading import Thread
from urllib.parse import urljoin

import requests
from requests.auth import HTTPBasicAuth

from latency import bandwidth, ping_latency, response_time

try:
    with open("env.json", "r") as envfile:
        env = json.load(envfile)
    auth = HTTPBasicAuth(env['certifire_uname'], env['certifire_pwd'])
except:
    print("env.json not foud, Quitting!")
    exit()

def server(PORT=8000):
    try:
        Handler = partial(http.server.SimpleHTTPRequestHandler, directory='./static')

        with socketserver.TCPServer(("", PORT, ), Handler) as httpd:
            print("serving mon_bw static files at port", PORT)
            httpd.serve_forever()
    except:
        print("Falied creating http server")

if env['mon_bw']:
        T = Thread(target=server)
        T.start()
        

def new_worker(env):
    if not env['ip']:
        try:
            env['ip'] = requests.get("http://ifconfig.me/ip").text
        except:
            print("Could not determine client IP, Quitting!")
            exit()

    if not env['location']:
        try:
            from ip2geotools.databases.noncommercial import DbIpCity
            response = DbIpCity.get(env['ip'], api_key='free')
            env['location'] = response.country+'-'+response.region
        except:
            print("Could not determine client location, Proceeding with Unknown!")
            env['location'] = "Unknown"

    payload = {
        'ip': env['ip'],
        'host': env['host'],
        'location': env['location'],
        'mon_self': env['mon_self'],
        'create_host': env['create_host'],
        'mon_bw': env['mon_bw'],
        'mon_url': env['mon_url'],
        'bw_url': env['bw_url']
    }

    try:
        create_worker = requests.post(urljoin(env['certifire_url'],'api/worker'), auth=auth, data=json.dumps(payload))
        worker = json.loads(create_worker.text)
        for key in worker:
            env[key] = worker[key]

        if env['mon_self'] and not env['mon_url']:
            env['mon_url'] = 'http://' + env['host']
    
        if env['mon_bw'] and not env['bw_url']:
            env['bw_url'] = urljoin('http://' + env['host'] + ':8000', 'bwmon/10M')
        return env
    except:
        print("Failed registering worker with certifire, Quitting!")
        exit()


if not env["id"]:
    env = new_worker(env)
    with open("env.json", "w") as envfile:
        json.dump(env, envfile, indent=4)

else:
    worker_url = urljoin(env['certifire_url'],'api/worker/')
    worker_url = urljoin(worker_url, str(env['id']))
    print(worker_url)

    try:
        worker = requests.get(worker_url, auth=auth)

        if worker.status_code == 401:
            env = new_worker(env)
            with open("env.json", "w") as envfile:
                json.dump(env, envfile, indent=4)
        else:
            worker = json.loads(worker.text)
            print(worker)
    except:
        print("Couldn't reach certifire server. Quitting!")
        exit()


worker_tags=f"""mon_worker={env['id']},mon_host={env['host']},mon_location={env['location']}"""

while True:
    try:
        targets = json.loads(requests.get(urljoin(env['certifire_url'],'api/target'), auth=auth).text)
    except:
        print("Couldn't reach certifire server temporarly. Continuing!")
        time.sleep(60)
        continue

    payload = {'id': env['id'], 'data':[]}

    for target in targets.values():
        print(target)
        pdata = ping_latency(target['host'])
        rtime, stcode = response_time(target['url'])
        if target['bw_url']:
            bw = bandwidth(target['bw_url'])
        strtime = str(time.time_ns())
        
        if pdata != -1:
            lpdata = f""" min={pdata["min"]},max={pdata["max"]},avg={pdata["avg"]},mdev={pdata["mdev"]} """
            linedata = f"""latency,host={target['host']},""" + worker_tags + lpdata + strtime
            print(linedata)
            payload['data'].append(linedata)
    
        if rtime != -1 or stcode != -1:
            lrdata = f""" delay={rtime},status={stcode} """
            linedata = f"""response_time,host={target['host']},""" + worker_tags + lrdata + strtime
            print(linedata)
            payload['data'].append(linedata)
        
        bwdata = f""" bps={bw} """
        linedata = f"""bandwidth,host={target['host']},""" + worker_tags + bwdata + strtime
        print(linedata)
        payload['data'].append(linedata)

    try:
        post_mon_data = requests.post(urljoin(env['certifire_url'],'api/monitoring'), auth=auth, data=json.dumps(payload))
        print(post_mon_data.status_code)
        time.sleep(60)
    except:
        print("Couldn't reach certifire server temporarly. Continuing!")
        time.sleep(60)
        try:
            post_mon_data = requests.post(urljoin(env['certifire_url'],'api/monitoring'), auth=auth, data=json.dumps(payload))
            print(post_mon_data.status_code)
        except:
            print("Couldn't reach certifire server temporarly x2. Continuing!")
            time.sleep(60)