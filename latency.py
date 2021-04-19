import re
import subprocess
import sys

import requests


def response_time(url):
    try:
        response = requests.get(url)
        return round(response.elapsed.total_seconds() * 1000, 3)
    except:
        return -1

def ping_latency(host):
    if sys.platform == 'linux':
        ping = subprocess.Popen(["ping "+host+" -c 4"], stdout = subprocess.PIPE, stderr = subprocess.PIPE, shell = True)
        output = ping.communicate()

        try:
            pattern = r"rtt.+"
            out = re.findall(pattern, output[0].decode())
            vals = out[0].split('=')[1].split('/')

            js = {}
            js["min"] = float(vals[0])
            js["avg"] = float(vals[1])
            js["max"] = float(vals[2])
            js["mdev"] = float(vals[3].split()[0])

            return js
        except:
            return -1
    elif sys.platform == 'win32':
        return -1                       #TODO implement for windows host
    else:
        return -1