import logging
import requests
from utils import pgs
from utils import rds
from logger import log


class Planet(object):
    log.Logger()
    # Postgres配置
    host = 'localhost'
    pgs_port = 12432
    pgs_db_name = 'planet'
    pgs_user = pgs_db_name
    pgs_pwd = pgs_db_name
    postgres = pgs.Pgs(host=host, port=pgs_port, db_name=pgs_db_name, user=pgs_user, password=pgs_pwd)
    # Redis配置
    rds_port = 12379
    rds_pwd = 'redis6379'
    redis = rds.Rds(host=host, port=rds_port, password=rds_pwd).redis_cli
    my_hash = None
    my_user_id = None
    token = 'djM6kGdI04LxK4zk9C2reI50szrReqT90NSVbjxv3WkvxXYkQqXRGyngiR2zX0EASm1GswTTk7RQepcmx6YtLCNqAyFcRC67z9O' \
            'YGmxLrEE-Hl4ayz9p21TYKQVNWZXHQZBZVY4D5OEVnWORTtBV7lkuOy-2_bQyJCEkDBLO3ksR8o10'
    headers = {
        'Authorization': 'token {0}'.format(token)
    }

    def __init__(self):
        self.redis = Planet.redis
        self.postgres = Planet.postgres
        Planet.my_hash = self.__get_my_hash()
        Planet.my_user_id = self.__get_my_user_id()
        logging.info('Init my hash : %s and my user id : %s', Planet.my_hash, Planet.my_user_id)

    def handler(self, sql, params):
        """ 处理数据

        :param sql:
        :param params:
        :return:
        """

        return self.postgres.handler(sql, params)

    def __get_my_user_id(self):
        """return my_user_id directly or request to return it (直接返回my_user_id或请求获得并返回)

        :return: my_user_id
        """

        if not Planet.my_user_id:
            key = 'planet:my:uid'
            Planet.my_user_id = self.redis.get(key)
            if not Planet.my_user_id:
                api = 'https://www.quanquanyuanyuan.cn/huodong/dog/api/my-status'
                resp = requests.post(api, json={}, headers=Planet.headers).json()
                Planet.my_user_id = resp['notification_settings'][0]['user_id']
                self.redis.set(key, Planet.my_user_id)
        return Planet.my_user_id

    def __get_my_hash(self):
        """return my_hash directly or request to return it (直接返回my_hash或请求获得并返回)

        :return: my_hash
        """

        if not Planet.my_hash:
            key = 'planet:my:hash'
            Planet.my_hash = self.redis.get(key)
            if not Planet.my_hash:
                api = 'https://www.quanquanyuanyuan.cn/huodong/dog/api/my-dog-hash'
                resp = requests.post(api, json={}, headers=Planet.headers).json()
                Planet.my_hash = resp['uid_hash']
                self.redis.set(key, Planet.my_hash)
        return Planet.my_hash
