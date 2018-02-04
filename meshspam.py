import socket
from threading import Thread
import threading
import queue
import time
import traceback
import requests
failqueue=queue.Queue()
savequeue=queue.Queue()
varlock=threading.Lock()
CURRENTPIDS=open("currentpids.txt",'r').read().strip().split(",")
CURRENTPIDS=[int(x.strip()) for x in CURRENTPIDS if x.strip()!=""]
def readsocket(sock,todo):
	result=[]
	buff=b""
	count=0
	while True:
		try:
			d=sock.recv(100000)
			buff+=d
			ll=len(buff)
			l=0
			m=0
			while l<ll:
				l=buff.find(b"HTTP/1.1",l)
				if l==-1:
					break
				l+=12
				if ll<l:
					break
				gt=todo.get()
				if buff[(l-3):l]==b"200":
					savequeue.put(gt)
				m=l
			buff=buff[m:]
			if not d:
				print("SOCKET CLOSED")
				break
		except:
			break
	while True:
		try:
			failqueue.put(todo.get_nowait())
		except:
			break
reqthreadcount=0
def checkid():
	global reqthreadcount
	with varlock:
		reqthreadcount+=1
		if reqthreadcount<32:
			Thread(target=savetofile).start()
	sock=None
	todoqueue=None
	while True:
		with varlock:
			todo=next(allvars)
		if todo==[]:
			if ((todoqueue!=None) and (len(todoqueue.queue)>0))|(len(failqueue.queue)>0):
				time.sleep(1)
				continue
			else:
				if sock!=None:
					try:
						sock.close()
					except:
						pass
				with varlock:
					reqthreadcount-=1
				print("Exiting request thread: {0}".format(threading.currentThread()._ident))
				return
		if sock==None:
			sock=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
			sock.settimeout(15)
			sock.connect(("i1.adis.ws",80))
			todoqueue=queue.Queue(200)
			Thread(target=readsocket,args=(sock,todoqueue)).start()
		try:
			for i in range(0,len(todo)):
				pack="HEAD /i/jpl/fp_{0:06d}_a HTTP/1.1\r\nHost: i1.adis.ws\r\nUser-Agent: Mozilla/5.0 (Windows; U; Windows NT 6.1; en-GB; rv:1.9.2.13) Gecko/20101203 Firefox/3.6.13\r\nAccept: */*\r\nAccept-Language: en-gb,en;q=0.5\r\nConnection: keep-alive\r\n\r\n".format(todo[i])
				sock.sendall(pack.encode())
				todoqueue.put(todo[i],timeout=20)
		except Exception as e:
			for j in range(i,len(todo)):
				failqueue.put(todo[j])
			try:
				sock.close()
			except:
				pass
			sock=None
def savetofile():
	sess=requests.session()
	while True:
		if reqthreadcount==0:
			print("Exiting saving thread {0}".format(threading.currentThread()._ident))
			return
		try:
			f=savequeue.get(timeout=5)
		except:
			continue
		if f in CURRENTPIDS:
			continue
		try:
			gh=sess.get("http://i1.adis.ws/i/jpl/fp_{0:06d}_a".format(f))
			print("Saving PID: {0}".format(f))
			lh=open(str(f)+".jpeg",'wb')
			lh.write(gh.content)
			lh.close()
		except:
			mn=open("FAILED.txt",'a')
			mn.write(str(f)+"\n")
			mn.close()
def vargen():
	global failqueue
	o=1
	while True:
		pending=[]
		while True:
			if len(pending)>=200:
				yield pending
				pending=[]
				continue
			try:
				v=failqueue.get_nowait()
				pending.append(v)
			except:
				break
		if (o<1000000)&(len(pending)<200):
			oo=o+200-len(pending)
			pending+=list(range(o,oo))
			o=oo
			print("Checked "+str(o)+" image urls")
		yield pending
		if reqthreadcount==0:
			return
allvars=vargen()
for i in range(0,100):
	Thread(target=checkid).start()