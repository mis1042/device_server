import json
import random
import time

import openai

import processor


def time_to_unix(year, month, day, hour, minute, second):
    time_tuple = time.strptime(f"{year} {month} {day} {hour} {minute} {second}", '%Y %m %d %H %M %S')
    return str(time.mktime(time_tuple))


def unix_to_time(unix):
    now = time.localtime(unix)
    return json.dumps({
        "year": now.tm_year,
        "month": now.tm_mon,
        "day": now.tm_mday,
        "hour": now.tm_hour,
        "minute": now.tm_min,
        "second": now.tm_sec
    })


def get_now_unix():
    return str(int(time.time()))


class AIChat:

    def __init__(self, device: processor.SmartOven):
        self.messages = [
            {
                "role": "system",
                "content": """
    现在你有权限操作一台能够分时段控温的烘干设备，你的职责如下：
    1、按照用户的需求给出你的烘干方案，要包含每个时段的时长和对应的温度。当用户同意你的方案时，请调用函数应用你的方案
    2、当用户给出工作时长和温度时，调用函数来设置设备
    3、当用户询问设备的状态时，调用函数来获得设备状态并返回与用户
    4、当用户给出一个开始工作的时间，工作时长，温度时调用函数来添加一个工作计划
    5、当用户给出工作计划的ID时调用函数删除对应的工作计划
    注意事项：
    1、所有涉及时间的操作请全部使用函数完成
    2、无论是函数的返回还是函数的参数，时长的单位都是分钟而不是秒，温度的单位都是摄氏度并且最高为120摄氏度
    3、用户要求停止工作时，你可以直接调用设置工作参数的函数并指定工作时长为0       
    4、用户要你给出方案时，不要向用户询问时间与温度，这应该是由你给出    
    5、用户要求你给出方案的流程应该是你先将方案输出给用户，如果用户明确表示同意你的方案再调用apply_programme函数，而不是在你输出方案的时候就调用 
                    """
            }
        ]
        self.functions = [
            {
                "name": "apply_programme",
                "description": "应用模型的烘干方案，请记住这个函数一定要在用户明确同意方案后再调用而不是在你给出方案的时候调用",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "steps": {
                            "type": "string",
                            "description": """
                                模型给出的方案内容，严格按如下格式返回
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
    """
                        }
                    },
                    "required": ["steps"]
                }
            },
            {
                "name": "get_device_info",
                "description": "获得设备的状态,如果有的参数值为-1则代表设备此时正处于空闲状态，不要返回值为-1的参数",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            },
            {
                "name": "set_working",
                "description": "设置设备的工作参数",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "temp": {
                            "type": "integer",
                            "description": "设备的工作时长（分钟）"
                        },
                        "work_time": {
                            "type": "integer",
                            "description": "设备的工作温度（摄氏度）"
                        }
                    },
                    "required": ["temp", "work_time"]
                }
            },
            {
                "name": "add_work_plan",
                "description": "添加设备的工作计划",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "temp": {
                            "type": "integer",
                            "description": "设备的工作时长（分钟）"
                        },
                        "work_time": {
                            "type": "integer",
                            "description": "设备的工作温度（摄氏度）"
                        },
                        "start_time": {
                            "type": "integer",
                            "description": "工作计划的开始时间（使用UNIX时间戳）"
                        }
                    },
                    "required": ["temp", "work_time", "start_time"]
                }
            },
            {
                "name": "delete_work_plan",
                "description": "删除工作计划",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "plan_id": {
                            "type": "integer",
                            "description": "需要被删除的工作计划的ID"
                        }
                    },
                    "required": ["plan_id"]
                }
            },
            {
                "name": "get_now_unix",
                "description": "获取当前时间的UNIX时间戳格式",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            },
            {
                "name": "unix_to_time",
                "description": "将UNIX时间戳转换为年月日时分秒",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "unix": {
                            "type": "integer",
                            "description": "UNIX时间戳"
                        }
                    },
                    "required": ['unix']
                }
            },
            {
                "name": "time_to_unix",
                "description": "将年月日时分秒转换为UNIX时间戳",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "year": {
                            "type": "integer",
                            "description": "年"
                        },
                        "month": {
                            "type": "integer",
                            "description": "月"
                        },
                        "day": {
                            "type": "integer",
                            "description": "日"
                        },
                        "hour": {
                            "type": "integer",
                            "description": "时"
                        },
                        "minute": {
                            "type": "integer",
                            "description": "分"
                        },
                        "second": {
                            "type": "integer",
                            "description": "秒"
                        }
                    },
                    "required": ["year", "month", "day", "hour", "minute", "second"]
                }
            }

        ]
        self.model = "gpt-3.5-turbo-0613"
        self.function_call = "auto"
        self.temperature = 0.2
        self.device = device
        self.available_functions = {
            "apply_programme": self.apply_programme,
            "get_device_info": self.get_device_info,
            "set_working": self.set_working,
            "add_work_plan": self.add_work_plan,
            "delete_work_plan": self.delete_work_plan,
            "get_now_unix": get_now_unix,
            "time_to_unix": time_to_unix,
            "unix_to_time": unix_to_time
        }

    def apply_programme(self, steps):
        # Clear All Work_Plans
        if type(steps) is str:
            steps = json.loads(steps)
        for i in self.device.plan_list:
            self.device.delete_work_plan(i['plan_id'])

        work_start_time = time.time() + 10
        for i in steps:
            seq = self.device.add_work_plan(
                plan_id=random.randint(100000, 999999),
                start_time=work_start_time,
                work_time=i['time'],
                target_temp=i['temp']
            )
            work_start_time += int(i['time']) * 60
            start_time = time.time()

            while processor.judge(seq, self.device):
                if time.time() - start_time > 10:
                    return {"status": "failed", "reason": "device not responding"}
        return {"status": "success"}

    def get_device_info(self):
        device_info = self.device.get_status()
        device_info.pop('work_plan')
        return device_info

    def set_working(self, temp, work_time):
        seq = self.device.set_working(temp, work_time)
        start_time = time.time()
        while processor.judge(seq, self.device):
            if time.time() - start_time > 10:
                return {"status": "failed", "reason": "device not responding"}
        return {"status": "success"}

    def add_work_plan(self, temp, work_time, start_time):
        seq = self.device.add_work_plan(random.randint(100000, 999999), start_time, work_time, temp)
        start_time = time.time()
        while processor.judge(seq, self.device):
            if time.time() - start_time > 10:
                return {"status": "failed", "reason": "device not responding"}
        return {"status": "success"}

    def delete_work_plan(self, plan_id):
        seq = self.device.delete_work_plan(plan_id)
        start_time = time.time()
        while processor.judge(seq, self.device):
            if time.time() - start_time > 10:
                return {"status": "failed", "reason": "device not responding"}
        return {"status": "success"}

    def get_messages(self):
        messages = []
        for i in self.messages:
            if (i['role'] == 'assistant') and i['content'] is not None:
                messages.append(i)
        return messages

    def chat(self, content):
        self.messages.append({
            "role": "user",
            "content": content
        })
        response = openai.ChatCompletion.create(
            model=self.model,
            messages=self.messages,
            functions=self.functions,
            function_call=self.function_call,
            temperature=self.temperature
        )

        response_message = response.choices[0].message
        self.messages.append(response_message)

        # On function callback
        if response_message.get("function_call"):
            function_name = response_message["function_call"]["name"]
            function_to_call = self.available_functions[function_name]
            function_args = json.loads(response_message["function_call"]["arguments"])
            function_response = function_to_call(**function_args)
            self.messages.append({
                "role": "function",
                "name": function_name,
                "content": str(function_response)
            })
            self.chat('')

        return self.get_messages()
