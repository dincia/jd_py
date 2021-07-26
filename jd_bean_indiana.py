#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2021/6/26 8:55
# @File    : jd_bean_indiana.py
# @Project : jd_scripts
# @Desc    ： 京豆APP->摇金豆->金豆夺宝
import asyncio
import aiohttp
import json

from urllib.parse import unquote

from utils.console import println
from utils.notify import notify
from utils.process import process_start
from config import USER_AGENT, JD_BEAN_INDIANA_OPEN


class JdBeanIndiana:
    """
    金豆夺宝,
    https://jdjoy.jd.com获取token和lkEPin,lkToken, 然后https://pf.moxigame.cn/jddb/duobao/login获取真正需要使用的token。
    夺宝功能都是在https://pf.moxigame.cn/这个域名里面操作的。
    """

    def __init__(self, pt_pin, pt_key):
        """
        :param pt_pin:
        :param pt_key:
        """
        self._token = None
        self._encrypt = None
        self._cookies = {
            'pt_pin': pt_pin,
            'pt_key': pt_key
        }
        self._pt_pin = unquote(pt_pin)
        self._nickname = None
        self._real_token = None  # 夺宝任务需要使用的token
        self._id = None  # 夺宝任务需要使用的用户ID
        self._joined_num = 0  # 当前已参与的夺宝数量
        self._use_bean_num = 0  # 夺宝消耗的京豆
        self._award_list = []  # 奖品列表
        self._message = None

    @property
    def message(self):
        """
        :return:
        """
        return self._message

    async def get_token(self, session):
        try:
            url = 'https://jdjoy.jd.com/saas/framework/user/token?appId=dafbe42d5bff9d82298e5230eb8c3f79&client=m&url' \
                  '=pengyougou.m.jd.com'
            response = await session.post(url)
            text = await response.text()
            data = json.loads(text)
            token = data['data']
            println('{}, 获取token成功!'.format(self._pt_pin))
            return token
        except Exception as e:
            println('{}, 获取token失败, 原因:{}'.format(self._pt_pin, e.args))
            return None

    async def verify(self, session):
        """
        验证
        :param session:
        :return:
        """
        try:
            url = 'https://jdjoy.jd.com/saas/verify/domain?domain=game-cdn.moxigame.cn&appId' \
                  '=dafbe42d5bff9d82298e5230eb8c3f79'
            response = await session.post(url=url)
            text = await response.text()
            data = json.loads(text)
            return data['success']
        except Exception as e:
            println('{}, verify fail, {}'.format(self._pt_pin, e.args))
            return False

    async def get_encrypt_params(self, session):
        """
        获取加密参数
        :param session:
        :return:
        """
        try:
            url = 'https://jdjoy.jd.com/saas/framework/encrypt/pin?appId=dafbe42d5bff9d82298e5230eb8c3f79'
            response = await session.post(url)
            text = await response.text()
            data = json.loads(text)
            encrypt = data['data']
            println('{}, 获取加密参数成功!'.format(self._pt_pin))
            return encrypt
        except Exception as e:
            println('{}, 获取加密参数失败, 原因:{}'.format(self._pt_pin, e.args))
            return []

    async def login(self, session):
        """
        夺宝活动登录获取token
        :return:
        """
        try:
            url = 'https://pf.moxigame.cn/jddb/duobao/login'
            body = {
                "refid": "zjd",
                "lkEPin": self._encrypt['lkEPin'],
                "lkToken": self._encrypt['lkToken'],
                "token": self._token,
                "returnurl": "https://prodev.m.jd.com/mall/active/xiPStZsNkPxpQFXqVRuTv1QGr3x/index.html?"
                             "tttparams=Z2p2neyJnTGF0IjoiMjMuMDE1NDExIiwiZ0xuZyI6IjExMy4zODgwOTIifQ5%3D%3D"
            }
            response = await session.post(url=url, data=json.dumps(body))
            data = await response.json()
            self._nickname = data['userInfo']['nickname']
            self._id = data['id']
            token = data['token']
            println('{}, 登陆成功, 昵称:{}'.format(self._pt_pin, self._nickname))
            return token
        except Exception as e:
            println('{}, login fail, reason:{}'.format(self._pt_pin, e.args))

    async def get_award_list(self, session, page=1, page_size=10):
        try:
            url = 'https://pf.moxigame.cn/jddb/duobao/list'
            params = {
                "id": self._id,
                "token": self._real_token,
                "pageSize": page_size,
                "page": page,
                "status": "progress"
            }
            response = await session.post(url=url, data=json.dumps(params))
            data = await response.json()
            return data['result']['list']
        except Exception as e:
            println('{}, 获取列表失败, {}'.format(self._pt_pin, e.args))
            return []

    async def join(self, session, params):
        """
        加入夺宝
        :param session:
        :param params:
        :return:
        """
        url = 'https://pf.moxigame.cn/jddb/duobao/join'
        try:
            response = await session.post(url=url, data=json.dumps(params))
            data = await response.json()
            if data['code'] == 2002:
                println('{}, 京豆余额不足, 无法参与!'.format(self._pt_pin))
            return data['code'] == 0
        except Exception as e:
            println('{}, 加入夺宝失败! {}'.format(self._pt_pin, e.args))
            return False

    async def share(self, session, params):
        """
        完成分享任务
        :param session:
        :param params:
        :return:
        """
        url = 'https://pf.moxigame.cn/jddb/duobao/finishTask'
        try:
            response = await session.post(url=url, data=json.dumps(params))
            data = await response.json()
            return data['code'] == 0
        except Exception as e:
            println('{}, 分享任务完成失败! {}'.format(self._pt_pin, e.args))
            return False

    async def do_lottery(self, session):
        """
        夺宝
        :param session:
        :return:
        """
        try:
            page = 1
            while True:
                data = await self.get_award_list(session, page)
                if not data:
                    break
                for item in data:
                    if 'duoBaoRoleInfo' in item:
                        self._joined_num += 1
                        println('{}, 夺宝:{}, 已参与过, 无需再次参与!'.format(self._pt_pin, item['actTitle']))
                        continue
                    params = {
                        'id': self._id,
                        'token': self._real_token,
                        'activeid': item['_id']
                    }
                    join_success = await self.join(session, params)
                    if join_success:
                        self._joined_num += 1
                        self._use_bean_num += 1
                        println('{}, 夺宝:{}, 参与成功!'.format(self._pt_pin, item['actTitle']))
                    else:
                        println('{}, 夺宝:{}, 参与失败!'.format(self._pt_pin, item['actTitle']))
                        continue
                    await asyncio.sleep(0.5)
                    params = {
                        'id': self._id,
                        'token': self._real_token,
                        'activeid': item['_id'],
                        'type': 'share'
                    }
                    share_success = await self.share(session, params)
                    if share_success:
                        println('{}, 夺宝:{}, 分享任务成功!'.format(self._pt_pin, item['actTitle']))
                    else:
                        println('{}, 夺宝:{}, 分享任务失败!'.format(self._pt_pin, item['actTitle']))
                    await asyncio.sleep(0.5)
                page += 1
        except Exception as e:
            println('{}, 参与京豆夺宝失败, {}'.format(self._pt_pin, e.args))

    async def query_award(self, session, params):
        """
        判断是否中奖
        :param session:
        :param params:
        :return:
        """
        try:
            url = 'https://pf.moxigame.cn/jddb/duobao/joinProgressList'
            response = await session.post(url=url, data=json.dumps(params))
            data = await response.json()
            if data['code'] != 0:
                return False
            # 暂时不知状态码，无法判断是否中奖
            if data['result']['status'] == 'noJoined':
                return False
            return True
        except Exception as e:
            println('{}, 查询奖品信息失败!{}'.format(self._pt_pin, e.args))
            return 0

    async def query_awards(self, session):
        """
        查询已中奖奖品列表
        :param session:
        :return:
        """
        url = 'https://pf.moxigame.cn/jddb/duobao/joinProgressList'
        params = {
            "id": self._id,
            "token": self._real_token,
            "pageSize": 10,
            "page": 1
        }
        try:
            response = await session.post(url=url, data=json.dumps(params))
            data = await response.json()
            for item in data['result']['list']:
                params = {
                    "id": self._id,
                    "token": self._token,
                    "activeid": item['_id']
                }
                await asyncio.sleep(0.5)
                status = await self.query_award(session, params)
                if not status:
                    continue
                self._award_list.append(item['actTitle'])

        except Exception as e:
            println('{}, 查询中奖信息失败, {}'.format(self._pt_pin, e.args))

    async def notify(self):
        """
        通知
        :return:
        """
        if len(self._award_list) > 0:
            award = ','.join(self._award_list)
        else:
            award = '无'
        message = '\n【活动名称】{}\n【用户ID】{}\n【用户昵称】{}\n' \
                  '【消耗京豆】{}\n【参与数量】{}\n【获得奖励】{}\n【提示信息】{}\n'\
            .format('京豆夺宝', self._pt_pin, self._nickname, self._use_bean_num, self._joined_num, award,
                    '京豆奖励自动发放, 实物需要手动领取, 活动入口:京东APP->我的->签到领京豆->摇京豆->左上角京豆夺宝!')
        self._message = message

    async def run(self):
        """
        入口
        :return:
        """
        headers = {
            'referer': 'https://prodev.m.jd.com/mall/active/xiPStZsNkPxpQFXqVRuTv1QGr3x/index.html',
            'user-agent': USER_AGENT,
        }
        async with aiohttp.ClientSession(headers=headers, cookies=self._cookies) as session:
            self._token = await self.get_token(session)
            self._encrypt = await self.get_encrypt_params(session)
            await self.verify(session)

        if not self._token or not self._encrypt:
            println('{}, 获取Token或加密参数失败, 无法进行夺宝!'.format(self._pt_pin))
            return

        headers = {
            'referer': 'https://prodev.m.jd.com/mall/active/xiPStZsNkPxpQFXqVRuTv1QGr3x/index.html',
            'user-agent': USER_AGENT,
            'origin': 'https://game-cdn.moxigame.cn',
            'Content-type': 'application/json',
        }

        async with aiohttp.ClientSession(headers=headers) as session:
            self._real_token = await self.login(session)
            if not self._real_token:
                println('{}, 无法获取夺宝token, 退出程序...'.format(self._pt_pin))
                return
            await self.do_lottery(session)
            await self.query_awards(session)
        await self.notify()


def start(pt_pin, pt_key):
    """
    :param pt_pin:
    :param pt_key:
    :return:
    """
    app = JdBeanIndiana(pt_pin, pt_key)
    asyncio.run(app.run())
    return app.message


if __name__ == '__main__':
    if not JD_BEAN_INDIANA_OPEN:
        println('配置未开启京豆夺宝功能不运行!')
    else:
        process_start(start, '京豆夺宝')
