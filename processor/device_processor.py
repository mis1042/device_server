import json
import time

import processor
from processor import SmartOven


def smartoven_processor(device: SmartOven, message):
    if message['operation'] == 'ack':
        for i in device.message_list:
            device.message_list.remove(i)
            break

    if message['operation'] == 'heart':
        device.last_seen = time.time()
        device.status = message['status']
        plan_list = message['work_plan']

        for i in plan_list:
            i['start_time'] += 946656000
        device.plan_list = plan_list

        if device.status == 'working':
            device.internal_temp = message['internal_temp']
            device.ambient_temp = message['ambient_temp']
            device.ambient_hum = message['ambient_hum']
            device.target_temp = message['target_temp']
            device.remain_time = message['remain_time']
        else:
            device.internal_temp = -1
            device.ambient_temp = -1
            device.ambient_hum = -1
            device.target_temp = -1
            device.remain_time = -1


def heart_sender(device: SmartOven):
    time.sleep(5)
    while True:
        device.publish(json.dumps({
            "source": "server",
            "operation": "heart",
        }))
        time.sleep(5)
        if time.time() - device.last_seen > 30:
            processor.device_list.pop(device.topic)
            print(f"Device {device.connect_name} offline!")
            break
