import json
import time
import threading
import processor


def smartoven_login(msg_data, client):
    device_connect_name = msg_data['connect_name']
    device_topic = f"device/smartoven/{device_connect_name}"
    message = {
        "source": "server",
        "operation": "login",
        "connect_name": device_connect_name,
        "status": "success"
    }
    if msg_data['require_time']:
        message['time'] = time.time()

    if device_topic in processor.device_list:
        client.publish(json.dumps(message))
        device = processor.device_list[device_topic]
        time.sleep(1)
        device.sync_work_plan()
        print(f"SmartOven Device {device_connect_name} login success!")
        return

    device = processor.SmartOven(device_topic, device_connect_name, client, time.time())
    device.heart_sender = threading.Thread(target=processor.device_processor.heart_sender, args=(device,))
    processor.device_list[device_topic] = device
    client.publish(device_topic, json.dumps(message))
    client.subscribe(device_topic)
    device.heart_sender.start()
    print(f"SmartOven Device {device_connect_name} login success!")


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


def tower_login(msg_data, client):
    device_connect_name = msg_data.split(',')[1]
    device_topic = f"device/tower/{device_connect_name}"
    device = processor.ObservationTower(device_topic, device_connect_name, client, time.time())
    processor.device_list[device_topic] = device
    client.subscribe(device_topic)
    print(f"Tower Device {device_connect_name} login success!")


def tower_processor(device: processor.ObservationTower, message):
    device.last_seen = time.time()
    if message[0] == '1':
        message = message[1::]
        device.temp = message
    if message[0] == '2':
        message = message[1::]
        device.hum = message
    if message[0] == '3':
        message = message[1::]
        device.dirty_hum = message
    if message[0] == '4':
        message = message[1::]
        device.earthquake = message
    if message[0] == '5':
        message = message[1::]
        device.db = message


def heart_sender(device: processor.SmartOven):
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

