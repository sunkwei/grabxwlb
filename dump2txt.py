#coding: utf-8
import db

out_fname = 'wxlb_sentences.txt'

db = db.DB()
data = db.all_data()

# data={'2016-10-6':[["...", "...", ...], ...], ...}
# 将句子使用全角句号分割
with open(out_fname, "w") as f:
    for k in data.keys():
        sss = data[k]
        for ss in sss:
            for s in ss:
                ss0 = s.split('。')
                for s0 in ss0:
                    if len(s0)>1:
                        f.write(s0)
                        f.write('\n')

