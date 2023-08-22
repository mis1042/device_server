import json
import random

device_list = {}


class Device:
    def __init__(self, topic, connect_name, server, last_seen):
        self.topic = topic
        self.connect_name = connect_name
        self.server = server
        self.last_seen = last_seen
        self.heart_sender = None
        self.message_list = []

    def publish(self, message):
        self.server.publish(self.topic, message)


class SmartOven(Device):
    def __init__(self, topic, connect_name, server, last_seen):
        Device.__init__(self, topic, connect_name, server, last_seen)
        self.status = 'free'
        self.internal_temp = -1
        self.ambient_temp = -1
        self.ambient_hum = -1
        self.plan_list = []
        self.target_temp = -1
        self.remain_time = -1

        self.chat = None

    def publish_ack(self, message):
        seq = random.randint(0, 9999999)
        self.message_list.append({"seq": seq, "message": message})
        message['seq'] = seq
        self.publish(json.dumps(message))
        return seq

    def set_working(self, temp, worktime):
        message = {
            "source": "server",
            "operation": "set_work_config",
            "work_time": worktime,
            "target_temp": temp
        }
        return self.publish_ack(message)

    def add_work_plan(self, plan_id, start_time, work_time, target_temp):
        return self.publish_ack({
            "source": "server",
            "operation": "add_work_plan",
            "plan_id": plan_id,
            "start_time": start_time - 946656000,
            "work_time": work_time,
            "target_temp": target_temp
        })

    def delete_work_plan(self, plan_id):
        return self.publish_ack({
            "source": "server",
            "operation": "delete_work_plan",
            "plan_id": plan_id
        })

    def get_status(self):
        return {
            "status": "success",
            "internal_temp": self.internal_temp,
            "ambient_temp": self.ambient_temp,
            "ambient_hum": self.ambient_hum,
            "target_temp": self.target_temp,
            "remain_time": self.remain_time,
            "device_status": self.status,
            "work_plan": self.plan_list
        }

    def sync_work_plan(self):
        for i in self.plan_list:
            self.add_work_plan(i['plan_id'], i['start_time'] - 946656000, i['work_time'], i['target_temp'])


def judge(seq, device: Device):
    for i in device.message_list:
        if seq in i.values():
            return True
    return False


def show_server_qrcode():
    import qrcode
    import socket
    from PIL import Image
    s = socket.socket()
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    finally:
        s.close()
    img = qrcode.make(f"{ip}:{1042}/")
    img.save('qr.png')
    img = Image.open('qr.png')
    img.show()
