# coding=utf-8
import datetime
import threading

import sys
import os
parentpath = os.path.dirname(sys.path[0])
sys.path.append(parentpath)

from bit.db import db



class DataStore(object):
    def __init__(self):
        self.last1minUpdate = datetime.datetime.utcnow()-datetime.timedelta(minutes=1)
        self.min1list = []
        self.last5minUpdate = datetime.datetime.utcnow()-datetime.timedelta(minutes=5)
        self.min5list = []
        self.last15minUpdate = datetime.datetime.utcnow()-datetime.timedelta(minutes=15)
        self.min15list = []
        self.last30minUpdate = datetime.datetime.utcnow()-datetime.timedelta(minutes=30)
        self.min30list = []
        self.lock = threading.Lock()

        conn = db.getconn()
        cursor = conn.cursor()
        cursor.execute("select * from bit_1min_margin order by trading_time desc")
        row1 = cursor.fetchone()
        if row1:
            self.last1minUpdate = row1[1]
        cursor.execute("select * from bit_5min_margin order by trading_time desc")
        row1 = cursor.fetchone()
        if row1:
            self.last5minUpdate = row1[1]
        cursor.execute("select * from bit_15min_margin order by trading_time desc")
        row1 = cursor.fetchone()
        if row1:
            self.last15minUpdate = row1[1]
        cursor.execute("select * from bit_30min_margin order by trading_time desc")
        row1 = cursor.fetchone()
        if row1:
            self.last30minUpdate = row1[1]
        conn.commit()
        cursor.close()
        conn.close()




    def _binarySearch(self,a,target):
        low = 0
        high = len(a) - 1
        #print 'target = ',target
        while low < high:
            #print "low = ",low," high= ",high,'low =',a[low][0],'high =',a[high][0]
            mid = (low + high) / 2
            midVal = a[mid][0]

            if (midVal == target):
                return mid

            if(high-low == 1):
                return low

            if midVal < target:
                low = mid
            elif midVal > target:
                high = mid
        return 0

    def extra(self,secondsdata):
        if secondsdata:
            #print '_binarySearch start'
            min = self._binarySearch(secondsdata, self.last1minUpdate)
            #print '_binarySearch min = ', min,'val =',secondsdata[min][0],'last1minUpdate=',self.last1minUpdate
            size = len(secondsdata)

            if(min+6<size):
                i = min
                if(secondsdata[min][0]<=self.last1minUpdate):
                    i = min+6
                if self.lock.acquire():
                    while(i<size):
                        #print "i=",i,"secondsdata i-6 =",secondsdata[i-6][0],"secondsdata i-5 =",secondsdata[i-5][0],"secondsdata i-4 =",secondsdata[i-4][0],"secondsdata i-3 =",secondsdata[i-3][0],"secondsdata i-2 =",secondsdata[i-2][0],"secondsdata i-1 =",secondsdata[i-1][0],"secondsdata i =",secondsdata[i][0]
                        #print "i=", i, "seconds[i] =", secondsdata[i][0],'last1minUpdate=',self.last1minUpdate,'last5minUpdate=',self.last5minUpdate,'last15minUpdate=',self.last15minUpdate,'last30minUpdate=',self.last30minUpdate
                        sec = secondsdata[i][0]
                        self.min1list.append((round(secondsdata[i][2]-secondsdata[i][1],2),secondsdata[i][0]))
                        self.last1minUpdate = sec
                        if (sec > self.last5minUpdate+datetime.timedelta(minutes=5)):
                            self.min5list.append((round(secondsdata[i][2]-secondsdata[i][1],2),secondsdata[i][0]))
                            self.last5minUpdate = sec
                        if (sec > self.last15minUpdate+datetime.timedelta(minutes=15)):
                            self.min15list.append((round(secondsdata[i][2]-secondsdata[i][1],2),secondsdata[i][0]))
                            self.last15minUpdate = sec
                        if (sec > self.last30minUpdate+datetime.timedelta(minutes=30)):
                            self.min30list.append((round(secondsdata[i][2]-secondsdata[i][1],2),secondsdata[i][0]))
                            self.last30minUpdate = sec
                        i += 6
                    self.lock.release()

    def commit(self):
        if self.min1list and self.lock.acquire():
            try:
                conn = db.getconn()
                cursor = conn.cursor()
                cursor.executemany("insert into bit_1min_margin values(%s,%s,current_timestamp)",self.min1list)
                if(self.min5list):
                    cursor.executemany("insert into bit_5min_margin values(%s,%s,current_timestamp)", self.min5list)
                if (self.min15list):
                    cursor.executemany("insert into bit_15min_margin values(%s,%s,current_timestamp)", self.min15list)
                if (self.min30list):
                    cursor.executemany("insert into bit_30min_margin values(%s,%s,current_timestamp)", self.min30list)
            except Exception as e:
                conn.rollback()  # 事务回滚
                print('事务处理失败', e)
            else:
                conn.commit()  # 事务提交
                self.min1list = []
                self.min5list = []
                self.min15list = []
                self.min30list = []
            cursor.close()
            conn.close()
            self.lock.release()