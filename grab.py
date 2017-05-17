#!/usr/bin/python
# coding: utf-8
#
# @file: grab.py
# @date: 2017-05-16
# @brief:
# @detail:
#
#################################################################


from bs4 import BeautifulSoup, element
import os, sys, requests, logging
from urllib.parse import urlparse
from db import DB
import time

logger = logging.getLogger(__name__)

''' 请求 www.wenzigao.com/data-YYYY-M-D.html 格式url，获取里面“主要内容、简要内容摘抄摘要”
	的链接内容 .....
'''
class Grab:
	def __init__(self, url):
		self.url = url

	def load(self, url=None):
		# 支持本地缓冲 ...
		if not url:
			url = self.url
		o = urlparse(url)
		fname = '.cache/' + o.path
		if os.path.isfile(fname):
			with open(fname, 'rb') as f:
				return f.read()
		else:
			req = requests.get(url)
			if req.status_code == 200:
				if not os.path.isdir('.cache'):
					os.mkdir('.cache')
				print('fname:{}'.format(fname))
				with open(fname, 'wb') as f:
					f.write(req.content)
				return req.content
			else:
				logger.warn('load: GET {} return {}'.format(self.url, req.status_code))
				return None
	
	def get_content(self):
		''' 返回简要内容的文字 ...'''
		content = self.load()	# 第一层
		soup = BeautifulSoup(content, 'lxml')
		cata3 = soup.find_all(class_='post cate3 auth1')	# 对应着 “XXXX年X月X日新闻联播主要内容、简要内容稿件摘抄摘要”
		if len(cata3) > 0:
			return self.get_cata3(cata3[0])
		else:	# 第一层，没有简要内容 ..
			# 这种情况下，有 class='post cate4 auth1', 对应着“焦点访谈”
			# 			   class='post cate1 auth1'，对应着“逐条新闻”
			#			   class='post cate2 auth1', 对应着“完整的新闻，但没有文字 ...
			# 这里尝试提取 cate1 的
			cate1 = soup.find_all(class_='post cate1 auth1')
			return self.get_cate1(cate1)

	def get_cate1(self, cate1s):
		# cate1 为列表，对应每一条新闻..
		all_contents = []
		for cate1 in cate1s:
			title, content = self.get_cate1_content(cate1)
			if title:
				all_contents.append(title)
		return all_contents

	def get_cate1_content(self, cate1):
		# cate1 对应一条新闻，需要首先提取链接，加载链接内容，然后提取里面的标题，内容 ...
		post_body = cate1.find_all(class_='post_body')[0]	# 必定存在
		link = post_body.find_all('a')[0]	# 对应到具体内容的链接 ...
		content_url = link.attrs['href']
		title = str(link.string)					# 这个就是 title 了

		content_page = self.load(content_url)	# 第二层
		soup = BeautifulSoup(content_page, 'lxml')
		post_content = soup.find_all(class_='post_content')[0]	# 里面往往包含一个 video，<p> 为文字 ...
		content = ''
		for p in post_content:
			if p.name != 'p':
				continue
			content += self.get_content_string(p)
		return title, content

	def get_cata3(self, cata3):
		post_body = cata3.find_all(class_='post_body')[0]
		link = post_body.find_all('a')[0]	# 对应着摘要的详细链接 ..
		content_url = link.attrs['href']	# 详细链接 ...

		content = self.load(content_url)	# 第二层
		soup = BeautifulSoup(content, 'lxml')
		cata3 = soup.find_all(class_='post cate3 auth1') # 对应着详细内容
		if len(cata3) > 0:
			return self.get_cata3_detail(cata3[0])
		else: # 第二层，内容格式不确定，
			# TODO: 需要进一步解析
			print("\tNOT support ???")
			return []

	def get_cata3_detail(self, cata3):
		post_body = cata3.find_all(class_='post_body')[0] #
		post_content = post_body.find_all(class_='post_content')[0]	# 发布的内容
		
		main_content = []	# [['标题', '内容'], ...]
		curr_title = None
		curr_content = ''
		for p in post_content:	# 每段内容使用 <p> 分割, <strong> 包裹的是标题，里面可能还有 <a> ...
			if p.name != 'p':
				continue
			t = self.get_title(p)
			if t: # 出现新的 title
				if curr_title:
					main_content.append([str(curr_title), str(curr_content)])
				curr_title = t
				curr_content = ''
			else:
				curr_content += self.get_content_string(p)
		if curr_title and curr_content:
			main_content.append([str(curr_title), curr_content])

		if len(main_content) == 0:
			# 此时内容可能在 <div id="main"> 里面 ...
			main_class = post_content.find_all(id='main')
			if len(main_class) > 0:
				main_class = main_class[0]
				curr_title = None
				curr_content = ''
				for p in main_class:
					if p.name != 'p':
						continue
					t = self.get_title(p)
					if t: # 出现新的 title
						if curr_title:
							main_content.append([str(curr_title), str(curr_content)])
						curr_title = t
						curr_content = ''
					else:
						curr_content += self.get_content_string(p)
				if curr_title:
					main_content.append([str(curr_title), str(curr_content)])

		title_with_empty = None
		for t in list(main_content): # 如果某个 content 为 ''，则检查后面的 title，如果是“央视网消息”，则合并
			if t[0].find('新闻联播文字稿') == 0 and title_with_empty:
				t[0] = title_with_empty
			if len(t[1]) < 3:
				title_with_empty = t[0]
				main_content.remove(t)

		if len(main_content) == 0:
			# 此时可能是因为没有 title 的情况，这时候，可以标题使用“title”，所有都是 content
			post_content = post_body.find_all(class_='post_content')[0]	# 发布的内容
			title = 'title'
			content = ''
			for p in post_content:	# 每段内容使用 <p> 分割, <strong> 包裹的是标题，里面可能还有 <a> ...
				if p.name != 'p':
					continue
				content += self.get_content_string(p)
			if content:
				main_content.append([title, content])
			
		return main_content

	def get_title(self, p):
		# 如 p 中包含 <strong> 则是 title，如果 <strong><a> 则返回 a 的内容
		a = p.find_all('a')
		if len(a) > 0:
			return a[0].string
		s = p.find_all('strong')
		if len(s) > 0:
			return s[0].string
		return None

	def get_content_string(self, p):
		# p 中可能包含 <br>，仅仅保留 <class 'bs4.element.NavigableString' 类型的，并且合并成字符串返回
		content = ''
		for s in p.contents:
			if isinstance(s, element.NavigableString):
				content += str(s)
		return content

def save(url):
	logger.info('Grab: url: "{}"'.format(url))
	grab = Grab(url)
	content = grab.get_content()
	logger.info('==> there are {} iterms'.format(len(content)))
	db = DB()
	o = urlparse(url)
	fname = o.path+'.pkl'
	db.save(name=fname, content=content)
	logger.info('==> {} saved'.format(fname))

if __name__ == '__main__':
	logging.basicConfig(level=logging.DEBUG)
	baseurl = 'http://www.wenzigao.com/'
	now = time.time()
	db = DB()
	while True:
		now -= 24*3600	# 减去一天的时间 ...
		lt = time.localtime(now)
		if lt[0] == 2014 and lt[1] == 6:	# 这个网站上，到此为止 ...
			print('==NO more')
			break
		name = 'date-{}-{}-{}.html.pkl'.format(lt[0], lt[1], lt[2])
		saved_content = db.load(name)
		if saved_content and len(saved_content) > 0:
			continue
		fdate = 'date-{}-{}-{}'.format(lt[0], lt[1], lt[2])
		url = baseurl+fdate+'.html'
		if lt[0] == 2017 and lt[1] == 3 and lt[2] == 8:
			a=1
		save(url)



# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4

