"""Python 端 WebSocket 广播通道。

Electron 桌宠作为客户端连 ws://127.0.0.1:8765，Python 把对话事件推过去。
A 阶段支持这些事件：
  hello   连接握手（服务端 -> 客户端）
  state   idle / thinking / speaking / listening
  chat    {role: user|assistant, text}
  notice  系统提示（网络/记忆故障等）

B 阶段会在此基础上扩展 sentence / emotion / motion / mouth 等事件。
"""

import json
import os
import queue
import threading

from websockets.sync.server import serve


class Link:
    def __init__(self, host=None, port=None):
        self.host = host or os.environ.get("ATRI_LINK_HOST", "0.0.0.0")
        try:
            self.port = int(port or os.environ.get("ATRI_LINK_PORT", "8765"))
        except ValueError:
            self.port = 8765
        self._clients = set()
        self.on_message = None
        self.input_queue = queue.Queue()
        self._lock = threading.Lock()
        self._server = None
        self._thread = None
        self._ready = threading.Event()
        self._error = None

    # ---------- 生命周期 ----------
    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._run, name="atri-link", daemon=True)
        self._thread.start()
        self._ready.wait(timeout=3)
        if self._error is not None:
            print(f"[LINK] 启动失败: {self._error}（终端对话不受影响）")
        elif not self._ready.is_set():
            print("[LINK] 启动超时（终端对话不受影响）")

    def _run(self):
        try:
            self._server = serve(self._handler, self.host, self.port)
        except Exception as exc:  # 端口被占用等
            self._error = exc
            self._ready.set()
            return

        self._ready.set()
        print(f"[LINK] 等待桌宠连接: ws://127.0.0.1:{self.port}")
        try:
            self._server.serve_forever()
        except Exception as exc:
            print(f"[LINK] 服务异常退出: {exc}")

    def stop(self):
        if self._server is not None:
            try:
                self._server.shutdown()
            except Exception:
                pass

    # ---------- 连接与收发 ----------
    def _handler(self, ws):
        with self._lock:
            self._clients.add(ws)
            count = len(self._clients)
        print(f"[LINK] 桌宠已连接（{count}）")
        try:
            self._send_to(ws, {"type": "hello", "app": "my_dear", "version": 1})
            for raw in ws:
                try:
                    event = json.loads(raw)
                except Exception:
                    continue
                callback = self.on_message
                if callback is not None:
                    try:
                        callback(event)
                    except Exception as exc:
                        print(f"[LINK] 客户端消息处理失败: {exc}")
        except Exception:
            pass
        finally:
            with self._lock:
                self._clients.discard(ws)
            print("[LINK] 桌宠已断开")

    @staticmethod
    def _send_to(ws, event):
        ws.send(json.dumps(event, ensure_ascii=False))

    def send(self, event):
        """线程安全地广播一条事件；没有客户端时静默丢弃。"""
        data = json.dumps(event, ensure_ascii=False)
        with self._lock:
            clients = list(self._clients)
        for ws in clients:
            try:
                ws.send(data)
            except Exception:
                with self._lock:
                    self._clients.discard(ws)


link = Link()


def emit_state(name):
    link.send({"type": "state", "state": name})


def emit_chat(role, text):
    link.send({"type": "chat", "role": role, "text": text})


def emit_notice(text):
    link.send({"type": "notice", "text": text})


def emit_sentence(text, duration=0.0, delay=0.0):
    link.send({"type": "sentence", "role": "assistant", "text": text, "duration": duration, "delay": delay})


def emit_mouth(value):
    link.send({"type": "mouth", "value": value})


def emit_emote(actions):
    link.send({"type": "emote", "actions": actions})