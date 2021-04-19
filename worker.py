import os

import requests
from requests.auth import HTTPBasicAuth
from urllib.parse import urljoin
import json
from latency import ping_latency, response_time
import time

with open("env.json", "r") as envfile:
    env = json.load(envfile)
auth = HTTPBasicAuth(env['certifire_uname'], env['certifire_pwd'])

if not env["id"]:

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
        'create_host': env['create_host']
    }

    create_worker = requests.post(urljoin(env['certifire_url'],'api/worker'), auth=auth, data=json.dumps(payload))
    worker = json.loads(create_worker.text)
    for key in worker:
        env[key] = worker[key]
    
    with open("env.json", "w") as envfile:
        json.dump(env, envfile, indent=4)
    
worker_tags=f"""mon_worker={env['id']},mon_host={env['host']},mon_location={env['location']}"""

while True:
    targets = json.loads(requests.get(urljoin(env['certifire_url'],'api/target'), auth=auth).text)
    payload = {'id': env['id'], 'data':[]}

    for target in targets.values():
        pdata = ping_latency(target['host'])
        rtime = response_time(target['url'])
        strtime = str(time.time_ns())
        
        if pdata != -1:
            lpdata = f""" min={pdata["min"]},max={pdata["max"]},avg={pdata["avg"]},mdev={pdata["mdev"]} """
            linedata = f"""latency,host={target['host']},""" + worker_tags + lpdata + strtime
            print(linedata)
            payload['data'].append(linedata)
    
        if rtime != -1:
            lrdata = f""" delay={rtime} """
            linedata = f"""response_time,host={target['host']},""" + worker_tags + lrdata + strtime
            print(linedata)
            payload['data'].append(linedata)

    post_mon_data = requests.post(urljoin(env['certifire_url'],'api/monitoring'), auth=auth, data=json.dumps(payload))
    print(post_mon_data.status_code)
    print(post_mon_data.text)
    time.sleep(60)

