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
    企业微信应用通知
    文档：https://work.weixin.qq.com/api/doc/90000/90136/91770
    """

    def __init__(self):
        self.corpid = Settings.WECHATWORK_CORPID
        self.corpsecret = Settings.WECHATWORK_SECRET
        self.agentid = Settings.WECHATWORK_AGENTID
        self.access_token = self._get_access_token()

    def _get_access_token(self) -> Optional[str]:
        """获取企业微信access_token"""
        url = f"https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid={self.corpid}&corpsecret={self.corpsecret}"
        try:
            response = requests.get(url)
            result = response.json()
            if result.get("errcode") == 0:
                return result["access_token"]
            logging.error(f"获取企业微信token失败: {result.get('errmsg')}")
            return None
        except Exception as e:
            logging.error(f"连接企业微信失败: {str(e)}")
            return None

    def send(self, title: str, content: str) -> bool:
        if not self.access_token:
            logging.warning("企业微信access_token未获取")
            return False

        url = f"https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={self.access_token}"
        payload = {
            "touser": "@all",
            "msgtype": "textcard",
            "agentid": self.agentid,
            "textcard": {
                "title": title,
                "description": content,
                "url": "URL",  # 可配置跳转链接
                "btntxt": "详情"
            },
            "safe": 0
        }

        try:
            response = requests.post(url, json=payload)
            result = response.json()

            if result.get("errcode") == 0:
                logging.info(f"企业微信通知成功: {title}")
                return True

            # token过期时自动刷新重试
            if result.get("errcode") == 42001:
                self.access_token = self._get_access_token()
                return self.send(title, content)

            logging.error(f"企业微信通知失败: {result.get('errmsg')}")
            return False

        except Exception as e:
            logging.error(f"企业微信连接异常: {str(e)}")
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