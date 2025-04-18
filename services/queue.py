import asyncio
import contextlib
from typing import Callable, Any
from multiprocessing import Manager, current_process

class Classmate:
    _instances = {}  # 存储每个进程的单例实例
    _manager = None  # 共享状态的Manager实例

    def __new__(cls):
        # 每个进程需要独立的单例实例
        process_id = current_process().pid
        if process_id not in cls._instances:
            # 初始化Manager（仅主进程创建）
            if cls._manager is None:
                cls._manager = Manager()
            # 创建进程专用实例
            instance = super().__new__(cls)
            instance.handlers = cls._manager.dict()  # type: ignore # 共享处理器字典
            instance.queue = cls._manager.Queue()    # type: ignore # 共享队列
            instance.receiver_task = None
            instance.started = False
            cls._instances[process_id] = instance
        return cls._instances[process_id]

    async def start(self):
        """启动消息接收协程"""
        if not self.started:
            self.started = True
            # 在当前进程的事件循环中启动协程
            self.receiver_task = asyncio.create_task(self._receiver())

    async def _receiver(self):
        """消息处理协程（异步版）"""
        while True:
            try:
                data = await asyncio.to_thread(self.queue.get)  # type: ignore # 非阻塞获取
                if data is None:
                    break
                msg_type, content = data
                if handler := self.handlers.get(msg_type): # type: ignore
                    await handler(content)
                self.queue.task_done()  # type: ignore # 需要手动调用以避免阻塞
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"消息处理异常: {e}")

    async def send(self, msg_type: str, content: Any):
        """发送消息（自动启动服务）"""
        if not self.started:
            await self.start()
        await asyncio.to_thread(self.queue.put, (msg_type, content))  # type: ignore # 异步化队列操作

    def register_handler(self, msg_type: str, handler: Callable):
        """注册消息处理器"""
        self.handlers[msg_type] = handler # type: ignore

    async def stop(self):
        """停止服务"""
        await asyncio.to_thread(self.queue.put, (None, None))  # type: ignore # 发送停止信号
        if self.receiver_task:
            self.receiver_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self.receiver_task

# import multiprocessing as mp
# import asyncio

# async def handle_video(content):
#     print(f"[进程 {mp.current_process().name}] 处理视频消息: {content}")

# async def worker_process():
#     # 在子进程中初始化并使用Classmate
#     Classmate().register_handler("video", handle_video)
#     await Classmate().send("video", "子进程消息")

# if __name__ == "__main__":
#     # 主进程发送消息
#     asyncio.run(Classmate().send("video", "主进程消息"))
    
#     # 启动子进程
#     p = mp.Process(target=lambda: asyncio.run(worker_process()))
#     p.start()
#     p.join()