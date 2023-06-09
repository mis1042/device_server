import json
import threading
import time
from json import JSONDecodeError

from paho.mqtt import client as mqtt_client

import processor.device_processor

broker = '127.0.0.1'
port = 1883
client_id = f'Python-Server'


def connect_to_server():
    def on_connect(client, userdata, flags, code):
        if code == 0:
            print("Connected To MQTT!")
        else:
            print("Failed to connect, code %d\n", code)

    client = mqtt_client.Client(client_id)
    client.on_connect = on_connect
    client.connect(broker, port)
    return client


def receive(client: mqtt_client):
    def on_message(client, userdata, msg):

        msg_data = msg.payload.decode()
        msg_topic = msg.topic
        try:
            msg_data = json.loads(msg_data)
        except JSONDecodeError:
            pass

        if msg_data['source'] == 'device':

            if msg_data['operation'] == 'login' and msg_topic == 'device/smartoven/login':
                device_connect_name = msg_data['connect_name']
                device_topic = f"device/smartoven/{device_connect_name}"
                if device_topic in processor.device_list:
                    processor.device_list.pop(device_topic)
                device = processor.SmartOven(device_topic, device_connect_name, client, time.time())
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
                print(f"Device {device_connect_name} login success!")

            if msg_topic in processor.device_list:
                device = processor.device_list[msg.topic]
                threading.Thread(target=processor.device_processor.smartoven_processor,
                                 args=(device, msg_data)).start()

    client.subscribe("device/smartoven/login")
    client.on_message = on_message


def start():
    client = connect_to_server()
    receive(client)
    client.loop_forever()


if __name__ == '__main__':
    start()
