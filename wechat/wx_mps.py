import re
import time
import json
import requests
import wx_mps_sql
from utils import pgs
from datetime import datetime


class WxMps:
    host = 'localhost'
    port = '12432'
    db_name = 'wxmps'
    user = db_name
    pwd = db_name

    def __init__(self):
        self.biz = 'MzU4NjA4NjMwNw=='  # 公众号标志
        self.pass_ticket = 'syyvrYpIR5DlT5goq3tcdr1sw%25252BUhH%25252FByS6GimOsAWTbnh3eR94OSz9Xb665LkGfV'  # 通用票据(非固定)
        self.headers = {
            # 通用cookie(非固定)
            'Cookie': 'pgv_pvi=6708115456; pgv_si=s4773475328; ptisp=cm; RK=XopsBML0RK; ptcz=73aac9f580839d2b9c7f634ca28f3e19c8bd037390a7f639e5332831aa13b8c4; uin=o1394223902; skey=@KWMdUovjK; pt2gguin=o1394223902; rewardsn=; wxuin=2089823341; devicetype=android-26; version=26060739; lang=zh_HK; pass_ticket=syyvrYpIR5DlT5goq3tcdr1sw+UhH/ByS6GimOsAWTbnh3eR94OSz9Xb665LkGfV; wap_sid2=CO3YwOQHEogBWFJhV2l3ajhMc0ZtZGFreFF0dGx1MGNaWi1XVE5Ubzk4QXFOMDRVclRCNkhLb1JSdjJqUXR2d1p4aTJheWZ3OWhFSVlvdmlaME1wSzhFMHRzUVBxT0tocFVna2t6QUVwQkoyQUNtUzdrZ1FLUHNGR1VwNEl0N1ZRUnlhT3V5MHV5QU1BQUF+fjDzpaXbBTgNQAE=; wxtokenkey=777',
            'User-Agent': 'Mozilla/5.0 (Linux; Android 8.0; WAS-AL00 Build/HUAWEIWAS-AL00; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/57.0.2987.132 MQQBrowser/6.2 TBS/044203 Mobile Safari/537.36 MicroMessenger/6.6.7.1321(0x26060739) NetType/WIFI Language/zh_HK'
        }
        self.postgres = pgs.Pgs(host=WxMps.host, port=WxMps.port, db_name=WxMps.db_name,
                                user=WxMps.user, password=WxMps.pwd)

    def spider_articles(self, msg_token):
        """抓取公众号的文章
        
        :return: 
        """

        offset = 0
        while True:
            api = 'https://mp.weixin.qq.com/mp/profile_ext?action=getmsg&__biz={0}&f=json&offset={1}' \
                  '&count=10&is_ok=1&scene=124&uin=777&key=777&pass_ticket={2}&wxtoken=&appmsg_token' \
                  '={3}&x5=1&f=json'.format(self.biz, offset, self.pass_ticket, msg_token)

            resp = requests.get(api, headers=self.headers).json()
            status = resp['errmsg']  # 状态码
            if status == 'ok':
                offset = resp['next_offset']  # 偏移量
                msg_list = json.loads(resp['general_msg_list'])['list']
                for msg in msg_list:
                    comm_msg_info = msg['comm_msg_info']
                    msg_id = comm_msg_info['id']  # 文章标志位
                    date_time = datetime.fromtimestamp(comm_msg_info['datetime'])  # 发布时间
                    msg_type = comm_msg_info['type']  # 文章类型
                    msg_data = json.dumps(comm_msg_info, ensure_ascii=False)  # msg原数据

                    app_msg_ext_info = msg.get('app_msg_ext_info')  # article原数据
                    if app_msg_ext_info:
                        # 某推送的首条文章
                        self.__parse_articles(app_msg_ext_info, msg_id, date_time, msg_type, msg_data)
                        # 该推送的其余文章
                        multi_app_msg_item_list = app_msg_ext_info.get('multi_app_msg_item_list')
                        if multi_app_msg_item_list:
                            for item in multi_app_msg_item_list:
                                msg_id = item['fileid']  # 文章标志位
                                if msg_id == 0:
                                    msg_id = int(time.time() * 1000)  # 部分历史文章有都为0的问题
                                msg_data = '{}'  # 首条文章有该数据即可
                                self.__parse_articles(item, msg_id, date_time, msg_type, msg_data)
                if not msg_list:
                    break
                time.sleep(30)  # 必要的休眠
                print('next offset is %d' % offset)
            else:
                print('Current end offset is %d' % offset)
                break

    def __parse_articles(self, info, msg_id, date_time, msg_type, msg_data):
        """解析文章列表接口数据并保存

        :param info:
        :param msg_id:
        :param date_time:
        :param msg_type:
        :param msg_data:
        :return:
        """

        title = info['title']  # 标题
        author = info['author']  # 作者
        cover = info['cover']  # 封面图
        del_flag = info.get('del_flag')  # 标志位
        digest = info['digest']  # 关键字
        source_url = info['source_url']  # 原文地址
        ext_data = json.dumps(info, ensure_ascii=False)  # 原始数据
        content_url = info['content_url']  # 微信地址

        self.__handle_data(wx_mps_sql.add_article(), (msg_id, date_time, msg_type, msg_data, title,
                                                      author, cover, digest, content_url, source_url,
                                                      del_flag, ext_data, datetime.now()))

    def __parse_article_detail(self, content_url):
        """从文章详情提取数据用于获取评论

        :param content_url: 微信地址
        :return:
        """

        try:
            api = content_url.replace('amp;', '')
            html = requests.get(api, headers=self.headers).text
        except requests.exceptions.MissingSchema:
            print('requests.exceptions.MissingSchema = ' + content_url)
        else:
            # group(0) is current line
            comment_str = re.search(r'var comment_id = "(.*)" \|\| "(.*)" \* 1;', html)
            comment_id = comment_str.group(1)
            app_msg_id_str = re.search(r"var appmsgid = '' \|\| '(.*)'\|\|", html)
            app_msg_id = app_msg_id_str.group(1)
            token_str = re.search(r'window.appmsg_token = "(.*)";', html)
            token = token_str.group(1)

            # 两个条件缺一不可
            if app_msg_id and token:
                print('__parse_article_detail: ' + api)
                self.__spider_comments(app_msg_id, comment_id, token)  # 爬取评论

    def __spider_comments(self, app_msg_id, comment_id, msg_token):
        """抓取文章的评论
        
        :param app_msg_id: 标志
        :param comment_id: 标志
        :param msg_token: 评论票据(非固定)
        :return: 
        """

        api = 'https://mp.weixin.qq.com/mp/appmsg_comment?action=getcomment&scene=0&__biz={0}' \
              '&appmsgid={4}&idx=1&comment_id={1}&offset=0&limit=100&uin=777&key=777' \
              '&pass_ticket={2}&wxtoken=777&devicetype=android-26&clientversion=26060739' \
              '&appmsg_token={3}&x5=1&f=json'.format(self.biz, comment_id, self.pass_ticket,
                                                     msg_token, app_msg_id)
        resp = requests.get(api, headers=self.headers).json()
        status = resp['base_resp']['errmsg']
        if status == 'ok':
            elected_comment = resp['elected_comment']
            for comment in elected_comment:
                nick_name = comment['nick_name']  # 昵称
                logo_url = comment['logo_url']  # 评论人头像
                create_time = datetime.fromtimestamp(comment['create_time'])  # 评论时间
                content = comment['content']  # 评论内容
                content_id = comment['content_id']  # id
                like_num = comment['like_num']  # 点赞数
                reply_list = comment['reply']['reply_list']  # 原数据

                reply_like_num = 0
                reply_content = None
                reply_create_time = None
                reply_data = json.dumps(reply_list)  # 原数据
                if reply_list:
                    reply = reply_list[0]  # 第1条回复评论
                    reply_content = reply['content']  # 回复评论内容
                    reply_create_time = datetime.fromtimestamp(reply['create_time'])  # 回复评论手时间
                    reply_like_num = reply.get('reply_like_num')  # 回复评论点赞数

                self.__handle_data(wx_mps_sql.add_article_comment(), (comment_id, nick_name, logo_url,
                                                                      content_id, content, like_num, create_time,
                                                                      reply_content, reply_create_time, reply_like_num,
                                                                      reply_data, datetime.now()))

    def __handle_data(self, sql, params):
        """保存数据

        :param sql: SQL
        :param params: Params
        :return:
        """

        self.postgres.handler(sql, params)

    def get_content_url(self, title=''):
        """从数据库获取帅选文章的微信地址

        :param title: 过滤条件
        :return:
        """

        rows = self.postgres.fetch_all(wx_mps_sql.find_article(), ('%' + title + '%',))
        for row in rows:
            content_url = row[0]
            self.__parse_article_detail(content_url)


if __name__ == '__main__':
    wxMps = WxMps()
    # 爬取文章
    # msg_token = '968_xDms46Qr4aDyyGztsd2KrCTBkhFG7CYkhQ4Nuw~~'  # 文章列表票据(非固定)
    # wxMps.spider_articles(msg_token)
    # 爬取评论
    wxMps.get_content_url()
