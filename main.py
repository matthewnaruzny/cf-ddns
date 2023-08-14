import json
import sched
import time

import requests

api_base = "https://api.cloudflare.com/client/v4/"

f = open('config.json')
config = json.load(f)
f.close()

cf_auth_headers = {'X-Auth-Email': config['api_email'], 'Authorization': config['api_token'],
                   'Content-Type': 'application/json'}


def cf_get_zones():
    zones_raw = requests.get(api_base + 'zones', headers=cf_auth_headers)
    zones = json.loads(zones_raw.text)
    return zones['result']


def cf_get_zone(name):
    zone_raw = requests.get(api_base + 'zones', headers=cf_auth_headers, params={
        "name": name
    })
    zone = json.loads(zone_raw.text)
    return zone['result']


def cf_get_record(zone_id, name):
    record_raw = requests.get(api_base + 'zones/' + zone_id + '/dns_records', headers=cf_auth_headers, params={
        "name": name
    })
    record = json.loads(record_raw.text)
    return record['result']


def cf_update_record(zone_id, name, content, record_type, proxied, ttl, tags=None, comment=None):
    if tags is None:
        tags = []
    payload = {
        "content": content,
        "name": name,
        "proxied": proxied,
        "type": record_type,
        "comment": comment,
        "tags": tags,
        "ttl": ttl
    }

    # Check if record exists
    record = cf_get_record(zone_id, name)
    if len(record) == 0:  # If New Record
        response = requests.post(api_base + "zones/" + zone_id + "/dns_records", headers=cf_auth_headers, json=payload)
        if response.status_code == 200:
            print("Successfully Created: " + name)
        else:
            print("Error Creating: " + name)
    else:  # Update Existing Record
        response = requests.patch(api_base + "zones/" + zone_id + "/dns_records/" + record[0]['id'],
                                 headers=cf_auth_headers, json=payload)
        if response.status_code == 200:
            print("Successfully Updated: " + name)
        else:
            print("Error Updating: " + name)


def update(scheduler, prev_external_ip):
    external_ip = requests.get("https://api.ipify.org").text
    if external_ip != prev_external_ip:
        zones = cf_get_zones()
        for r in config['records']:
            zone_found = False
            for zone in zones:
                if zone['name'] == r['zone']:
                    cf_update_record(zone['id'], r['name'], external_ip, r['type'], r['proxy'], r['ttl'])
                    zone_found = True
                    break

            if not zone_found:
                print("Zone: " + r['zone'] + " not found")
    else:
        print("No Change")

    scheduler.enter(config['update_delay'], 1, update, (scheduler, external_ip))


if __name__ == '__main__':
    main_scheduler = sched.scheduler(time.time, time.sleep)
    main_scheduler.enter(0, 1, update, (main_scheduler, '0'))
    main_scheduler.run()
