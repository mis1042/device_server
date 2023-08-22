import json
import os
import threading
import time

import flask
import openai
from flask_cors import CORS

import mqtt
import processor
from processor import device_list, gpt_processor

app = flask.Flask(__name__)
CORS(app, resources=r'/*')
with open('config.json', 'r') as f:
    config = json.load(f)
    broker = config['broker']
    port = config['port']
    client_id = config['client_id']
    user = config['user']
    password = config['password']
    openai.api_key = config['openai_key']
    os.environ["HTTP_PROXY"] = config['openai_proxy']
    os.environ["HTTPS_PROXY"] = config['openai_proxy']
threading.Thread(target=mqtt.start, args=(client_id, user, password, broker, port)).start()
threading.Thread(target=processor.show_server_qrcode).start()


@app.route('/device/<device_type>/<connect_name>/get_info', methods=['GET'])
def get_device_info(device_type, connect_name):
    topic = f"device/{device_type}/{connect_name}"
    if topic not in device_list:
        return flask.jsonify({"status": "failed", "reason": "device not online"})
    device = device_list[topic]
    return flask.jsonify(device.get_status())


# SmartOven Device: Set Working
@app.route('/device/<device_type>/<connect_name>/set_working', methods=['POST'])
def set_working(device_type, connect_name):
    if device_type == 'smartoven':
        topic = f"device/{device_type}/{connect_name}"
        if topic not in device_list:
            return flask.jsonify({"status": "failed", "reason": "device not online"})
        device = device_list[topic]
        if flask.request.json is None:
            return flask.jsonify({"status": "failed", "reason": "invalid request"})
        temp = flask.request.json['target_temp']
        worktime = flask.request.json['work_time']
        seq = device.set_working(temp, worktime)
        start_time = time.time()
        while processor.judge(seq, device):
            if time.time() - start_time > 10:
                return flask.jsonify({"status": "failed", "reason": "device not responding"})
        return flask.jsonify({"status": "success"})


# SmartOven Device: Add Work Plan
@app.route('/device/<device_type>/<connect_name>/add_work_plan', methods=['POST'])
def add_work_plan(device_type, connect_name):
    if device_type == 'smartoven':
        topic = f"device/{device_type}/{connect_name}"
        if topic not in device_list:
            return flask.jsonify({"status": "failed", "reason": "device not online"})
        device = device_list[topic]
        if flask.request.json is None:
            return flask.jsonify({"status": "failed", "reason": "invalid request"})
        plan_id = flask.request.json['plan_id']
        start_time = flask.request.json['start_time']
        work_time = flask.request.json['work_time']
        target_temp = flask.request.json['target_temp']
        seq = device.add_work_plan(plan_id, start_time, work_time, target_temp)
        start_time = time.time()
        while processor.judge(seq, device):
            if time.time() - start_time > 10:
                return flask.jsonify({"status": "failed", "reason": "device not responding"})
        return flask.jsonify({"status": "success"})


# SmartOven Device: Delete Work Plan
@app.route('/device/<device_type>/<connect_name>/delete_work_plan', methods=['POST'])
def delete_work_plan(device_type, connect_name):
    if device_type == 'smartoven':
        topic = f"device/{device_type}/{connect_name}"
        if topic not in device_list:
            return flask.jsonify({"status": "failed", "reason": "device not online"})
        device = device_list[topic]
        if flask.request.json is None:
            return flask.jsonify({"status": "failed", "reason": "invalid request"})
        plan_id = flask.request.json['plan_id']
        seq = device.delete_work_plan(plan_id)
        start_time = time.time()
        while processor.judge(seq, device):
            if time.time() - start_time > 10:
                return flask.jsonify({"status": "failed", "reason": "device not responding"})
        return flask.jsonify({"status": "success"})


@app.route('/device/<device_type>/<connect_name>/create_chat')
def create_chat(device_type, connect_name):
    if device_type == 'smartoven':
        topic = f"device/{device_type}/{connect_name}"
        if topic not in device_list:
            return flask.jsonify({"status": "failed", "reason": "device not online"})
        device = device_list[topic]
        device.chat = processor.gpt_processor.AIChat(device)
        return flask.jsonify({"status": "success"})


@app.route('/device/<device_type>/<connect_name>/chat', methods=['POST'])
def chat(device_type, connect_name):
    if device_type == 'smartoven':
        topic = f"device/{device_type}/{connect_name}"
        if topic not in device_list:
            return flask.jsonify({"status": "failed", "reason": "device not online"})
        if flask.request.json is None:
            return flask.jsonify({"status": "failed", "reason": "invalid request"})
        device = device_list[topic]
        if device.chat is None:
            device.chat = processor.gpt_processor.AIChat(device)
        try:
            return flask.jsonify({
                "messages": device.chat.chat(flask.request.json['content'])
            })
        except openai.error.RateLimitError:
            return "", 500
