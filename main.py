import threading
import time
import openai
import json
import os
import flask
from flask_cors import CORS
import mqtt
import processor
from processor import device_list

app = flask.Flask(__name__)
CORS(app, resources=r'/*')
with open('config.json', 'r') as f:
    config = json.load(f)
    broker = config['broker']
    port = config['port']
    client_id = config['client_id']
    user = config['user']
    password = config['password']
    openai_key = config['openai_key']
    os.environ["HTTP_PROXY"] = config['openai_proxy']
    os.environ["HTTPS_PROXY"] = config['openai_proxy']
threading.Thread(target=mqtt.start, args=(client_id, user, password, broker, port)).start()


@app.route('/device/<device_type>/<connect_name>/get_info', methods=['GET'])
def get_device_info(device_type, connect_name):
    if device_type == 'smartoven':
        topic = f"device/{device_type}/{connect_name}"
        if topic not in device_list:
            return flask.jsonify({"status": "failed", "reason": "device not online"})
        device = device_list[topic]
        return flask.jsonify({
            "status": "success",
            "internal_temp": device.internal_temp,
            "ambient_temp": device.ambient_temp,
            "ambient_hum": device.ambient_hum,
            "target_temp": device.target_temp,
            "remain_time": device.remain_time,
            "device_status": device.status,
            "work_plan": device.plan_list
        })


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


@app.route('/chat', methods=['POST'])
def chat():
    if flask.request.json is None:
        return flask.jsonify({"status": "failed", "reason": "invalid request"})
    content = flask.request.json['content']
    request_content = """
        以下列的格式回复烘干content的每一步的时间与温度，只返回下面的内容不需要其他的
    {
            "steps":[
            {
            "temp":20,
            // 使用摄氏度
            "time":20
            //使用分钟
            },
            ...
        ]
    }
    """.replace('content', content)
    rsp = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "user", "content": request_content}
        ]
    )
    return json.dumps(json.loads(rsp.get("choices")[0]["message"]["content"]))
