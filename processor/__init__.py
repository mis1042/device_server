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
        self.message_list = []
        self.target_temp = -1
        self.remain_time = -1

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


def judge(seq, device: SmartOven):
    for i in device.message_list:
        if seq in i.values():
            return True
    return False
