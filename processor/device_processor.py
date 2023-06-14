import json
import time
import threading
import processor


def device_login(device_type, msg_data, client):
    device_connect_name = msg_data['connect_name']
    device_topic = f"device/{device_type}/{device_connect_name}"
    if device_topic in processor.device_list:
        processor.device_list[device_topic].heart_sender._stop()
        processor.device_list.pop(device_topic)
    if device_type == 'smartoven':
        device = processor.SmartOven(device_topic, device_connect_name, client, time.time())
    elif device_type == 'tower':
        device = processor.ObservationTower(device_topic, device_connect_name, client, time.time())
    else:
        return

    device.heart_sender = threading.Thread(target=processor.device_processor.heart_sender, args=(device,))
    processor.device_list[device_topic] = device
    message = {
        "source": "server",
        "operation": "login",
        "connect_name": device_connect_name,
        "status": "success"
    }
    if msg_data['require_time']:
        message['time'] = time.time()
    client.publish(device_topic, json.dumps(message))
    client.subscribe(device_topic)
    device.heart_sender.start()
    print(f"{device_type} device {device_connect_name} login success!")


def smartoven_processor(device: processor.SmartOven, message):
    if message['operation'] == 'ack':
        for i in device.message_list:
            if i['seq'] == message['ack_seq']:
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


def heart_sender(device: processor.Device):
    time.sleep(5)
    while True:
        device.publish(json.dumps({
            "source": "server",
            "operation": "heart",
        }))
        time.sleep(2)
        if time.time() - device.last_seen > 30:
            processor.device_list.pop(device.topic)
            print(f"Device {device.connect_name} offline!")
            break
