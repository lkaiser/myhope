# coding=utf-8
import redis  # redis数据库链接
import pickle


class Conn_db():
    def __init__(self):
        # 创建对本机数据库的连接对象
        self.conn = redis.StrictRedis(host='127.0.0.1', port=6379, db=0)

    # 存储
    def set(self, key_, value_):
        # 将数据pickle.dumps一下，转化为二进制bytes数据
        value_ = pickle.dumps(value_)
        # 将数据存储到数据库
        self.conn.set(key_, value_)

    # 读取
    def get(self, key_):
        # 从数据库根据键（key）获取值
        value_ = self.conn.get(key_)
        if value_ != None:
            value_ = pickle.loads(value_)  # 加载bytes数据，还原为python对象
            return value_
        else:
            return []  # 为None(值不存在)，返回空列表