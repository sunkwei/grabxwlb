#!/usr/bin/python
#coding: utf-8

import pickle, os

''' 根据名字保存到文件 '''

class DB:
    def __init__(self, path='.store/'):
        if not os.path.isdir(path):
            os.mkdir(path)
        self.path = path

    def save(self, name, content):
        fname = os.path.sep.join((self.path, name))
        with open(fname, 'wb') as f:
            pickle.dump(content, f)

    def load(self, name):
        fname = os.path.sep.join((self.path, name))
        if not os.path.isfile(fname):
            return None
        with open(fname, 'rb') as f:
            return pickle.load(f)

    def all_data(self):
        data = {}
        for n in os.listdir(self.path):
            fname = os.path.sep.join((self.path, n))
            with open(fname, 'rb') as f:
                o = pickle.load(f)
                if len(o) > 0:
                    pos = n[5:].find('.')
                    name = n[5:pos+5]
                    data[name] = o
                else:
                    print('{} has no data'.format(fname))
        return data

if __name__ == '__main__':
    db = DB()
    data = db.all_data()
    cnt = 0
    for d in data:
        cnt += len(d)
    print('{}/{}'.format(len(data), cnt))
