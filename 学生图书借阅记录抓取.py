# -*- encoding=utf8 -*-
#! /usr/bin/env python3

'''此程序可抓取指定学号范围的大学四年图书馆借书记录并保存到mysql数据库'''

import requests
import re
import chardet
import urllib
from bs4 import BeautifulSoup
import pandas as pd
from sqlalchemy import create_engine
import pymysql
pymysql.install_as_MySQLdb()
def login(students_num):
    login_data = {
        'barcode' : students_num,
        'password' : '888888',
        'login_type' : ''
    }
    headers = {
        'Host': '121.33.188.47:22995',
        'Connection': 'keep-alive',
        'Content-Length': '48',
        'Origin': 'http://121.33.188.47:22995',
        'X-Requested-With': 'XMLHttpRequest',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML,like Gecko) Chrome/62.0.3202.94 Safari/537.36',
        'X-Prototype-Version': '1.4.0',
        'Content-type': 'application/x-www-form-urlencoded',
        'Accept': '*/*',
        'Referer': 'http://121.33.188.47:22995/opac_two/reader/infoList.jsp',
        'Accept-Encoding': 'gzip, deflate',
        'Accept-Language': 'zh-CN,zh;q=0.9',
    }
    session = requests.session()
    login_url = 'http://121.33.188.47:22995/opac_two/include/login_app.jsp'

    content = session.post(login_url, headers = headers, data=login_data)
    if  re.findall(r'查无此读者',content.text) != [] :
        # print('%s 账号或密码不匹配,正在尝试下一个'%students_num)
        return
    else:
        print('%s 登入成功'%students_num,end='')

    cookie_header={
        'Host': '121.33.188.47:22995',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:57.0) Gecko/20100101 Firefox/57.0',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2',
        'Accept-Encoding': 'gzip, deflate',
        'Referer': 'http://121.33.188.47:22995/opac_two/reader/infoList.jsp',
        'Cookie': 'JSESSIONID=' + content.cookies['JSESSIONID'] + '; __lnkrntdmcvrd=-1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Cache-Control': 'max-age=0',
    }

    #若要查询所有图书馆4年内借阅的图书
    borrow_param={
        'library_id': '%C3%8B%C3%B9%C3%93%C3%90%C2%B7%C3%96%C2%B9%C3%9D',
        'fromdate': '2014-8-1',
        'todate': '2017-11-30',
        'b1': '%BC%EC%CB%F7',
    }

    borrow_cookie={
        '__lnkrntdmcvrd':'-1',
        'content':content.cookies['JSESSIONID']

    }

    borrow_history_url='http://121.33.188.47:22995/opac_two/reader/jieshulishi.jsp?' + urllib.parse.urlencode(borrow_param)
    srudents_msg_url ='http://121.33.188.47:22995/opac_two/reader/reader_set.jsp'
    borrow_history_content = session.get(borrow_history_url,headers=cookie_header,cookies=borrow_cookie,data=borrow_param)
    students_msg_content = session.get(srudents_msg_url,headers=cookie_header)

    encode_msg = chardet.detect(borrow_history_content.content)
    # print(encode_msg) GB2312
    borrow_history_text = str(borrow_history_content.content,'GB2312')
    students_msg_text = str(students_msg_content.content,'GB2312')
    # borrow_history_text = borrow_history_content.text.encode('latin-1').decode('GBK')
    # print(borrow_history_text)
    # o = borrow_history_text.encode('GB2312').decode('utf-8',errors='ignore')
    # root = etree.HTML(borrow_history_text)
    # print(etree.tostring(root))
    # print(root.xpath('/html/body/table/tbody/tr[1]/td/table/tbody/tr[9]/td[2]'))


    b_soup = BeautifulSoup(borrow_history_text, 'lxml', from_encoding=encode_msg['encoding'])


    # print(b_soup.prettify)

    isBorrow1 = b_soup.select("tr.td_color_1 > td:nth-of-type(4)")
    isBorrow2 = b_soup.select("tr.td_color_2 > td:nth-of-type(4)")
    isBorrow3 = isBorrow1 + isBorrow2

    bookscount = 0
    for i in range(len(isBorrow3)):
        if getmsg(isBorrow3[i]) == '借书':
            bookscount += 1
    if bookscount == 0:
        # print(' !此同学竟然没有向图书馆借过书')
        return



    student_class = re.findall(re.compile('name="str_reader_addr" type="text"  value="(.*?)"'), students_msg_text)[0]
    student_department = re.findall(re.compile('读者单位:</TD>[\t\r\n\s]{12}<TD>[\t\r\n\s]{12}(.{3,10})\r[\t\r\n\s]*?',re.M),students_msg_text)[0].lstrip()
    student_name = re.findall(r'名:</TD>[\t\r\n\s]{12}<TD>[\t\r\n\s]{12}(.{3})[\t\r\n\s]*?',students_msg_text)[0]
    student_gender = re.findall(r'性别:</TD>[\t\r\n\s]{12}<TD>[\t\r\n\s]{12}(.{1})[\t\r\n\s]*?',students_msg_text)[0]

    books=[]
    book1 = b_soup.select("tr.td_color_1 > td:nth-of-type(2)")
    book2 = b_soup.select("tr.td_color_2 > td:nth-of-type(2)")
    book3 = book1 + book2

    date=[]
    date1 = b_soup.select("tr.td_color_1 > td:nth-of-type(5)")
    date2 = b_soup.select("tr.td_color_2 > td:nth-of-type(5)")
    date3 = date1 + date2

   # print(bookscount)
   # print(date3.__len__())

    for k in range(bookscount):
        books.append(getmsg(book3[k]))
        date.append(getmsg(date3[k]))

    print(' 并成功读取借书历史 借阅数为:' + str( bookscount))
    df = pd.DataFrame({
        '系别' : student_department,
        '学号' : students_num,
        '姓名' : student_name,
        '性别' : student_gender,
        '班级' : student_class,
        '借书时间' : pd.Categorical(date),
        '书名' : pd.Categorical(books),
    })
    df.to_sql('14dd',engine,if_exists='append')

def getmsg(tag):
    r = re.compile('>(.*?)\s<')
    return re.findall(r,str(tag))[0]

engine = create_engine('mysql+mysqldb://root:@localhost:3306/schoollib?charset=utf8')
ObjectStudents = range(11111111,11111111)
for s in ObjectStudents:
    login(s)
