import wx_mps_sql
from utils import pgs


def show_data(data_list):
    with open('mps.md', 'a', encoding='utf-8-sig') as f:
        for data in data_list:
            #  nick_name,content,logo_url,comment_time
            comment_time = data[3].strftime('%Y-%m-%d %H:%M:%S')
            f.write('#### ' + data[0] + '  ' + comment_time + '\n')
            f.write('&emsp;&emsp;' + data[1] + '\n')
            f.write('![' + data[0] + '](' + data[2] + ')' + '\n\n')


def get_data():
    content = '%广州%'
    rows = pgs.fetch_all(wx_mps_sql.find_article_comment(), (content,), db_name='wxmps')
    show_data(rows)


if __name__ == '__main__':
    get_data()
