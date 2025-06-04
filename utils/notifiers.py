# 通知模块
# utils/notifiers.py
import requests
import json
import logging
from typing import Optional
from config.settings import Settings


class Notifier:
    """通知基类"""

    def send(self, title: str, content: str) -> bool:
        raise NotImplementedError


class ServerChanNotifier(Notifier):
    """
    Server酱Turbo版通知
    文档：https://sct.ftqq.com/
    """

    def __init__(self):
        self.sckey = Settings.SERVERCHAN_SCKEY
        self.base_url = f"https://sctapi.ftqq.com/{self.sckey}.send"

    def send(self, title: str, content: str) -> bool:
        try:
            payload = {
                "title": title,
                "desp": content
            }
            response = requests.post(self.base_url, data=payload)
            result = response.json()

            if result.get("code") == 0:
                logging.info(f"ServerChan通知成功: {title}")
                return True
            else:
                logging.error(f"ServerChan通知失败: {result.get('message')}")
                return False

        except Exception as e:
            logging.error(f"ServerChan连接异常: {str(e)}")
            return False


class WechatWorkNotifier(Notifier):
    """
    企业微信机器人Webhook通知
    文档：https://work.weixin.qq.com/api/doc/90000/90136/91770
    """

    def __init__(self):
        self.webhook_key = Settings.WECHATWORK_WEBHOOK_KEY
        self.webhook_url = f"https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key={self.webhook_key}"

    def send(self, title: str, content: str) -> bool:
        # 构建markdown消息，将标题和内容组合
        # 注意：markdown内容中可以使用标题格式，但整个消息内容不能超过4096字节
        markdown_content = f"## {title}\n{content}"

        payload = {
            "msgtype": "markdown",
            "markdown": {
                "content": markdown_content
            }
        }

        headers = {
            "Content-Type": "application/json"
        }

        try:
            response = requests.post(self.webhook_url, headers=headers, data=json.dumps(payload))
            result = response.json()

            if result.get("errcode") == 0:
                logging.info(f"企业微信机器人通知成功: {title}")
                return True
            else:
                logging.error(f"企业微信机器人通知失败: {result.get('errmsg')}")
                return False

        except Exception as e:
            logging.error(f"企业微信机器人连接异常: {str(e)}")
            return False


class MultiNotifier(Notifier):
    """组合通知（可同时使用多个渠道）"""

    def __init__(self):
        self.notifiers = []
        if Settings.ENABLE_SERVERCHAN:
            self.notifiers.append(ServerChanNotifier())
        if Settings.ENABLE_WECHATWORK:
            self.notifiers.append(WechatWorkNotifier())

    def send(self, title: str, content: str) -> bool:
        success = False
        for notifier in self.notifiers:
            if notifier.send(title, content):
                success = True
        return success