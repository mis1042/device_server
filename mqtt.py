import json
import threading
import time
from json import JSONDecodeError

from paho.mqtt import client as mqtt_client

import processor.device_processor


def connect_to_server(client_id, user, password, broker, port):
    def on_connect(client, userdata, flags, code):
        if code == 0:
            print("Connected To MQTT!")
        else:
            print("Failed to connect, code %d\n", code)

    client = mqtt_client.Client(client_id)
    client.username_pw_set(user, password)
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
            if msg_topic.split('/')[1] == 'smartoven':
                # SmartOven Device Topic: device/smartoven/xxx

                # SmartOven Login
                if msg_data['operation'] == 'login' and msg_topic.split('/')[2] == 'login':
                    processor.device_processor.device_login('smartoven', msg_data, client)

                # SmartOven Process
                if msg_topic in processor.device_list:
                    device = processor.device_list[msg.topic]
                    threading.Thread(target=processor.device_processor.smartoven_processor,
                                     args=(device, msg_data)).start()

            if msg_topic.split('/')[1] == 'tower':
                # Tower Device Topic: device/tower/xxx
                pass

    client.subscribe("device/smartoven/login")
    client.on_message = on_message


def start(client_id, user, password, broker, port):
    client = connect_to_server(client_id, user, password, broker, port)
    receive(client)
    client.loop_forever()
