# coding=utf-8
import pymysql.cursors
import datetime
import pymysql
from pymysql import connect

DB_URL = 'mysql+pymysql://finace:finace@127.0.0.1/finace?charset=utf8'

def getconn():
    connect = pymysql.Connect(
        host='localhost',
        port=3306,
        user='bit',
        passwd='bit',
        db='bit',
        charset='utf8'
    )
    return connect

def update(sql):
    connect = getconn()
    cursor = connect.cursor()
    try:
        cursor.execute(sql)  # 执行更新
    except Exception as e:
        connect.rollback()  # 事务回滚
        print('事务处理失败', e)
    else:
        connect.commit()  # 事务提交
        print('事务处理成功', cursor.rowcount)
    cursor.close()
    connect.close()
    return

def querycount(sql):
    print(sql)
    connect = getconn()
    row = False
    cursor = connect.cursor()
    try:
        cursor.execute(sql)  # 执行更新
        row = cursor.fetchone()
       # print(row)
    except Exception as e:
        connect.rollback()  # 事务回滚
        print('事务处理失败', e)
    else:
        connect.commit()  # 事务提交
        print('事务处理成功')
    cursor.close()
    connect.close()
    return row[0]

if __name__ == '__main__':
    conn = getconn()
    cursor = conn.cursor()
    cursor.execute("select * from bit_1min_margin order by trading_time desc")
    row_1 = cursor.fetchone()
    print row_1[1]
    print datetime.datetime.utcnow()
    cursor.close()
    connect.close()


