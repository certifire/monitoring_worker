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

with open("env.json", "r") as envfile:
    env = json.load(envfile)
auth = HTTPBasicAuth(env['certifire_uname'], env['certifire_pwd'])

def server(PORT=8000):
    Handler = partial(http.server.SimpleHTTPRequestHandler, directory='./static')

    with socketserver.TCPServer(("", PORT, ), Handler) as httpd:
        print("serving mon_bw static files at port", PORT)
        httpd.serve_forever()

if env['mon_bw']:
        T = Thread(target=server)
        T.start()
        

def new_worker(env):
    if not env['ip']:
        env['ip'] = requests.get("http://ifconfig.me/ip").text

    if not env['location']:
        from ip2geotools.databases.noncommercial import DbIpCity
        response = DbIpCity.get(env['ip'], api_key='free')
        env['location'] = response.country+'-'+response.region

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

    create_worker = requests.post(urljoin(env['certifire_url'],'api/worker'), auth=auth, data=json.dumps(payload))
    worker = json.loads(create_worker.text)
    for key in worker:
        env[key] = worker[key]

    if env['mon_self'] and not env['mon_url']:
        env['mon_url'] = 'http://' + env['host']
    
    if env['mon_bw'] and not env['bw_url']:
        env['bw_url'] = urljoin('http://' + env['host'] + ':8000', 'bwmon/10M')
    return env


if not env["id"]:
    env = new_worker(env)
    with open("env.json", "w") as envfile:
        json.dump(env, envfile, indent=4)

else:
    worker_url = urljoin(env['certifire_url'],'api/worker/')
    worker_url = urljoin(worker_url, str(env['id']))
    print(worker_url)
    worker = requests.get(worker_url, auth=auth)

    if worker.status_code == 401:
        env = new_worker(env)
        with open("env.json", "w") as envfile:
            json.dump(env, envfile, indent=4)
    else:
        worker = json.loads(worker.text)
        print(worker)


worker_tags=f"""mon_worker={env['id']},mon_host={env['host']},mon_location={env['location']}"""

while True:
    targets = json.loads(requests.get(urljoin(env['certifire_url'],'api/target'), auth=auth).text)
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

    post_mon_data = requests.post(urljoin(env['certifire_url'],'api/monitoring'), auth=auth, data=json.dumps(payload))
    print(post_mon_data.status_code)
    #print(post_mon_data.text)
    time.sleep(60)

