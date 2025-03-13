from pkg.plugin.context import register, handler, BasePlugin, APIHost, EventContext
from pkg.plugin.events import GroupMessageReceived, PersonMessageReceived
import subprocess
import os
import re
import asyncio
import time
import json
from datetime import datetime, timedelta, timezone
from pkg.platform.types import *

APPLIANCE_ID = "VERSA"

# 创建UTC+8时区对象
china_tz = timezone(timedelta(hours=8))

@register(name="AutoTaskPlugin", 
          description="增加定时功能的小插件（支持±1分钟触发范围）", 
          version="0.5", 
          author="sheetung")
class AutoTaskPlugin(BasePlugin):

    def __init__(self, host: APIHost):
        self.host = host
        # 初始化任务列表
        self.tasks = []
        self.load_tasks()
        self.lock = asyncio.Lock()
        self.last_check_time = -1.0


        # 启动定时检查器
        self.check_timer_task = asyncio.create_task(self.check_timer())

    lock = asyncio.Lock()  # 创建一个锁以确保线程安全
    command_queue = asyncio.Queue()  # 创建一个队列以存储待处理的命令

    async def register(self) -> None:
        super().register()
        print("AutoTaskPlugin 已加载，使用 🕒 命令来管理定时任务")

    async def on_unregister(self) -> None:
        # 停止定时检查器
        self.check_timer_task.cancel()
        self.check_timer_task = None

    async def check_timer(self):
        while True:
            try:
                await asyncio.sleep(60)
                # print('60秒检查')
                await self.check_timer_handler()
            except Exception as e:
                print(f"定时检查出错: {str(e)}")

    async def check_timer_handler(self):
        try:
            # current_time_str = datetime.now().strftime("%H:%M")  # 修正 datetime 使用
            current_time_str = datetime.now(china_tz).strftime('%H:%M') 
            print(f'当前时间: {current_time_str}，检查定时任务')
            hours_current, minutes_current = current_time_str.split(":")
            current_minutes = int(hours_current) * 60 + int(minutes_current)

            now = datetime.now(china_tz)

            for task in self.tasks:
                task_time = task["time"]
                try:
                    hours_task, minutes_task = map(int, task_time.split(':'))
                    task_minutes = hours_task * 60 + minutes_task
                    time_diff = abs(current_minutes - task_minutes)
                except ValueError:
                    print(f"任务时间格式错误: {task_time}")
                    continue

                if time_diff == 0:  # 移除 or True
                    last_triggered = task.get("last_triggered_at")
                    if last_triggered is None or (now - last_triggered).total_seconds() >= 60:
                        print(f'触发任务: {task["name"]}')
                        task["last_triggered_at"] = now
                        self.save_tasks()  # 保存任务列表到文件
                        await self.execute_task(task)
        except Exception as e:
            print(f"检查定时任务时出错: {str(e)}")
                    
    async def execute_task(self, task):
        try:
            script_name = task["script"]
            target_id = task["target"]
            target_type = task["type"]
            task_name = task["name"]

            script_path = os.path.join(os.path.dirname(__file__), 'data', f"{script_name}.py")
            print(f"执行脚本: {script_path}")
            if os.path.exists(script_path):
                try:
                    result = subprocess.check_output(['python', script_path], text=True, timeout=60)  # 设置超时为60秒
                    print(f"脚本执行结果: {result}")
                    messages = self.convert_message(result, target_id)
                    # print(f'messages1={messages}')
                    await self.send_reply(target_id, target_type, messages)
                except subprocess.CalledProcessError as e:
                    error_msg = f"定时任务 {task_name} 执行失败: {e.output}"
                    print(error_msg)
                    await self.send_reply(target_id, target_type, [Plain(error_msg)])
                except Exception as e:
                    error_msg = f"定时任务 {task_name} 发生错误: {str(e)}"
                    print(error_msg)
                    await self.send_reply(target_id, target_type, [Plain(error_msg)])
            else:
                error_msg = f"定时任务 {task_name} 对应的脚本 {script_name}.py 不存在"
                print(error_msg)
                await self.send_reply(target_id, target_type, [Plain(error_msg)])
        except Exception as e:
            print(f"执行任务时出错: {str(e)}")

    def convert_message(self, message, sender_id):
        parts = []
        last_end = 0
        image_pattern = re.compile(r'!\[.*?\]\((https?://\S+)\)')  # 定义图像链接的正则表达式

        # 检查消息中是否包含at指令
        if "atper_on" in message:
            parts.append(At(target=sender_id))  # 在消息开头加上At(sender_id)
            message = message.replace("atper_on", "")  # 从消息中移除"send_on"

        for match in image_pattern.finditer(message):  # 查找所有匹配的图像链接
            start, end = match.span()  # 获取匹配的起止位置
            if start > last_end:  # 如果有文本在图像之前
                parts.append(Plain(message[last_end:start]))  # 添加纯文本部分
            image_url = match.group(1)  # 提取图像 URL
            parts.append(Image(url=image_url))  # 添加图像消息
            last_end = end  # 更新最后结束位置
        if last_end +1 < len(message):  # 如果还有剩余文本
            parts.append(Plain(message[last_end:]))  # 添加剩余的纯文本

        return parts if parts else [Plain(message)]  # 返回构建好的消息列表，如果没有部分则返回纯文本消息

    async def send_reply(self, target_id, target_type, messages):
        try:
            # print("1111111111111111")
            adapters = self.host.get_platform_adapters()  # 获取所有适配器对象
            
            # 如果没有适配器，直接返回
            if not adapters:
                print("Error: No adapters found.")
                return
                
            # 尝试使用第一个可用的适配器
            adapter_to_use = adapters[0]
            
            # 尝试查找名为 'aiocqhttp' 的适配器对象
            for adapter in adapters:
                try:
                    if hasattr(adapter, 'name') and adapter.name == "aiocqhttp":
                        adapter_to_use = adapter
                        break
                except Exception as e:
                    print(f"检查适配器时出错: {str(e)}")
                    continue
            
            print(f'使用适配器: {adapter_to_use}')
            
            if target_type == 'person':
                print(f'发送个人消息: target_id={target_id}')
                
                await self.host.send_active_message(adapter=adapter_to_use,
                                                    target_type=target_type,
                                                    target_id=str(target_id),
                                                    message=MessageChain(messages))
            elif target_type == 'group':
                print(f'发送群组消息: target_id={target_id}')
                # print(f"self.host 的类型: {type(self.host)}")
                # print(f"self.host 的值: {self.host}")
                await self.host.send_active_message(adapter=adapter_to_use,
                                                    target_type=target_type,
                                                    target_id=str(target_id),
                                                    message=MessageChain(messages),
                                                )
        except Exception as e:
            print(f"发送消息时出错: {str(e)}")

    def load_tasks(self):
        """
        加载任务列表，从 tasks.json 文件中读取
        """
        try:
            with open(os.path.join(os.path.dirname(__file__), 'tasks.json'), 'r', encoding='utf-8') as file:
                tasks_data = json.load(file)
                if not isinstance(tasks_data, list):
                    self.tasks = []
                    return
                self.tasks = []
                for task_data in tasks_data:
                    task = {
                        "time": task_data.get("time", ""),
                        "script": task_data.get("script", ""),
                        "target": task_data.get("target", 0),
                        "type": task_data.get("type", ""),
                        "name": task_data.get("name", ""),
                        "created_at": task_data.get("created_at", ""),
                        "last_triggered_at": datetime.fromisoformat(task_data.get("last_triggered_at", "")) if task_data.get("last_triggered_at") else None
                    }
                    self.tasks.append(task)
        except FileNotFoundError:
            self.tasks = []
        except json.JSONDecodeError:
            self.tasks = []
        except Exception as e:
            print(f"加载定时任务失败: {str(e)}")
            self.tasks = []

    def save_tasks(self):
        """
        保存任务列表，写入到 tasks.json 文件中
        """
        try:
            tasks_data = []
            for task in self.tasks:
                task_data = {
                    "time": task.get("time", ""),
                    "script": task.get("script", ""),
                    "target": task.get("target", 0),
                    "type": task.get("type", ""),
                    "name": task.get("name", ""),
                    "created_at": task.get("created_at", ""),
                    "last_triggered_at": task.get("last_triggered_at").isoformat() if task.get("last_triggered_at") else None
                }
                tasks_data.append(task_data)
            with open(os.path.join(os.path.dirname(__file__), 'tasks.json'), 'w', encoding='utf-8') as file:
                json.dump(tasks_data, file, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"保存定时任务失败: {str(e)}")

    @handler(GroupMessageReceived)
    async def group_normal_message_received(self, ctx: EventContext):
        try:
            msg = str(ctx.event.message_chain).strip()
            if msg.startswith("🕒") or msg.startswith("@AutoTaskPlugin"):
                print(f"收到群组定时任务命令: {msg}")
                await self.command_queue.put(ctx)  # 将命令上下文放入队列
                await self.process_commands()  # 处理命令
                return True  # 返回True表示消息已被处理，阻止其他插件或大模型处理
            return False  # 返回False表示消息未被处理，允许其他插件或大模型处理
        except Exception as e:
            print(f"处理群组消息时出错: {str(e)}")
            return False

    @handler(PersonMessageReceived)
    async def person_normal_message_received(self, ctx: EventContext):
        try:
            msg = str(ctx.event.message_chain).strip()
            if msg.startswith("🕒") or msg.startswith("@AutoTaskPlugin"):
                print(f"收到个人定时任务命令: {msg}")
                await self.command_queue.put(ctx)  # 将命令上下文放入队列
                await self.process_commands()  # 处理命令
                return True  # 返回True表示消息已被处理，阻止其他插件或大模型处理
            return False  # 返回False表示消息未被处理，允许其他插件或大模型处理
        except Exception as e:
            print(f"处理个人消息时出错: {str(e)}")
            return False

    async def process_commands(self):
        try:
            while not self.command_queue.empty():  # 当队列不为空时
                ctx = await self.command_queue.get()  # 从队列中获取命令上下文
                target_type = 'group' if isinstance(ctx.event, GroupMessageReceived) else 'person'
                await self.handle_command(ctx, target_type)  # 执行命令
                await asyncio.sleep(2)  # 等待 2 秒再处理下一个命令
        except Exception as e:
            print(f"处理命令队列时出错: {str(e)}")

    async def handle_command(self, ctx: EventContext, target_type):
        try:
            msg = str(ctx.event.message_chain).strip()
            print(f"处理命令: {msg}, 类型: {target_type}")

            # 处理 cmd，如果包含 / 则删除 /
            if '/' in msg:
                msg = msg.replace('/', '')  # 删除所有 /，只保留文字部分

            # 处理消息前缀
            original_msg = msg  # 保存原始消息
            if msg.startswith("🕒"):
                msg = msg[1:].strip()
            elif msg.startswith("@AutoTaskPlugin"):
                msg = msg[len("@AutoTaskPlugin"):].strip()
            
            # 如果用户只发送了前缀而没有命令，显示帮助信息
            if not msg and (original_msg == "🕒" or original_msg == "@AutoTaskPlugin"):
                await self.show_help(ctx)
                return
                
            command = msg.split(' ', 2)  # 拆分命令为最多三个部分

            # 命令结构：[子命令] [任务名] [时间]
            # 例如：添加 早报 6:00
            #       删除 早报
            #       列出

            subcmd = command[0].strip() if len(command) > 0 else ""
            task_name = command[1].strip() if len(command) > 1 else ""
            task_time = command[2].strip() if len(command) > 2 else ""
            sender_id = ctx.event.sender_id
            group_id = ctx.event.launcher_id if target_type == 'group' else sender_id

            print(f"解析命令: 子命令={subcmd}, 任务名={task_name}, 时间={task_time}")

            if subcmd == "添加":
                await self.add_task(ctx, target_type, group_id, task_name, task_time)
            elif subcmd == "删除":
                await self.delete_task(ctx, target_type, group_id, task_name)
            elif subcmd == "列出":
                await self.list_tasks(ctx, target_type, group_id)
            else:
                await self.show_help(ctx)
        except Exception as e:
            print(f"处理命令时出错: {str(e)}")
            try:
                await ctx.reply(MessageChain([Plain(f"处理命令时出错: {str(e)}")]))
            except:
                pass

    async def add_task(self, ctx: EventContext, target_type, group_id, task_name, task_time):
        try:
            # 检查任务名和时间是否为空
            if not task_name:
                await ctx.reply(MessageChain([Plain("任务名不能为空!")]))
                return
                
            if not task_time:
                await ctx.reply(MessageChain([Plain("时间不能为空!")]))
                return

            # 检查任务名称是否已存在
            for task in self.tasks:
                if task["name"] == task_name and task["target"] == group_id and task["type"] == target_type:
                    await ctx.reply(MessageChain([Plain(f"定时任务 {task_name} 已存在，请使用其他名称!")]))
                    return

            # 验证时间格式是否正确
            if re.match(r"^\d{1,2}:\d{2}$", task_time) is None:
                await ctx.reply(MessageChain([Plain("时间格式不正确，请使用 HH:MM 格式!")]))
                return

            # 检查脚本是否存在
            script_path = os.path.join(os.path.dirname(__file__), 'data', f"{task_name}.py")
            if not os.path.exists(script_path):
                await ctx.reply(MessageChain([Plain(f"任务脚本 {task_name}.py 不存在于 data 目录中!")]))
                return

            # 保存任务信息
            new_task = {
                "time": task_time,
                "script": f"{task_name}",  # 脚本名称与任务名一致，需要存放在 data/目录下
                "target": group_id,
                "type": target_type,
                "name": task_name,
                "created_at": datetime.now(china_tz).strftime("%Y-%m-%d %H:%M:%S"),
                "last_triggered_at": None  # 添加一个新字段，用于记录任务的最后触发时间
            }

            self.tasks.append(new_task)
            self.save_tasks()

            await ctx.reply(MessageChain([Plain(f"定时任务 {task_name} 已添加，时间：{task_time}")]))
        except Exception as e:
            print(f"添加任务时出错: {str(e)}")
            await ctx.reply(MessageChain([Plain(f"添加任务时出错: {str(e)}")]))

    async def delete_task(self, ctx: EventContext, target_type, target_id, task_name):
        try:
            # 查找并删除任务
            for task in self.tasks:
                if task["name"] == task_name and task["target"] == target_id and task["type"] == target_type:
                    self.tasks.remove(task)
                    self.save_tasks()
                    await ctx.reply(MessageChain([Plain(f"定时任务 {task_name} 已删除!")]))
                    return

            await ctx.reply(MessageChain([Plain(f"定时任务 {task_name} 不存在!")]))
        except Exception as e:
            print(f"删除任务时出错: {str(e)}")
            await ctx.reply(MessageChain([Plain(f"删除任务时出错: {str(e)}")]))

    async def list_tasks(self, ctx: EventContext, target_type, target_id):
        try:
            tasks_info = []
            for task in self.tasks:
                if task["target"] == target_id and task["type"] == target_type:
                    last_triggered = task.get('last_triggered_at', '从未触发')
                    if isinstance(last_triggered, datetime):
                        last_triggered = last_triggered.strftime("%Y-%m-%d %H:%M:%S")
                    tasks_info.append(f"{task['name']} - {task['time']} - {task['created_at']} (最后触发时间: {last_triggered})")

            if tasks_info:
                message = "\n".join(tasks_info)
            else:
                message = "没有找到任何定时任务!"

            await ctx.reply(MessageChain([Plain(message)]))
        except Exception as e:
            print(f"列出任务时出错: {str(e)}")
            await ctx.reply(MessageChain([Plain(f"列出任务时出错: {str(e)}")]))

    async def show_help(self, ctx: EventContext):
        """显示帮助信息"""
        # 获取data目录下的所有Python脚本
        data_dir = os.path.join(os.path.dirname(__file__), 'data')
        available_scripts = []
        
        try:
            if os.path.exists(data_dir) and os.path.isdir(data_dir):
                for file in os.listdir(data_dir):
                    if file.endswith('.py'):
                        available_scripts.append(file[:-3])  # 去掉.py后缀
        except Exception as e:
            print(f"获取可用脚本列表时出错: {str(e)}")
        
        # 构建可用脚本列表文本
        available_scripts_text = "\n".join(available_scripts) if available_scripts else "暂无可用脚本"
        
        help_text = f"请使用以下格式：\n🕒 添加 <任务名> <时间>\n🕒 删除 <任务名>\n🕒 列出\n\
或\n@AutoTaskPlugin 添加 <任务名> <时间>\n@AutoTaskPlugin 删除 <任务名>\n@AutoTaskPlugin 列出\n\
例如：🕒 添加 早报 8:10\n\
\n任务名仅能触发/data目录下脚本\n\
目前可用任务名：\n{available_scripts_text}"
        
        await ctx.reply(MessageChain([Plain(help_text)]))

    def __del__(self):
        # 清理定时检查器
        if self.check_timer_task:
            self.check_timer_task.cancel()