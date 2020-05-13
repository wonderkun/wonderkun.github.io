---
title: 一步步理解python的异步IO
url: 710.html
id: 710
categories:
  - 代码控
date: 2018-06-25 23:47:29
tags:
  - python
  - code
---

### 前言

看到越来越多的大佬都在使用python的异步IO，协程等概念来实现高效的IO处理过程，可是我对这些概念还不太懂，就学习了一下。 因为是初学者，在理解上有很多不到位的地方，如果有错误，还希望能够有人积极帮我斧正。

下面就使用一个简单的爬虫的例子，通过一步一步的改进，最后来用异步IO的方式实现。

<!--more-->

### 0x01 阻塞的IO

我们要实现一个爬虫，去爬百度首页n次，最简单的想法就是依次下载，从建立socket连接到发送网络请求再到读取响应数据，顺序进行。

代码如下：

```python
#coding:utf-8 
import time 
import socket
import sys

def doRequest():
    sock = socket.socket()
    sock.connect(('www.baidu.com',80))
    sock.send("GET / HTTP/1.1\r\nHost: www.baidu.com\r\nConnection: Close\r\n\r\n".encode("utf-8"))
    response = sock.recv(1024)
    return response

def main():
    start = time.time()
    for i in range(int(sys.argv[1])):
        doRequest()
    print("spend time : %s" %(time.time()-start))
    
main()
```

因为socket是阻塞方式调用的，所以cpu执行到`sock.connect()`,`sock.recv()`,就会一直卡在那里直到socket的状态就绪，所以浪费了很多的CPU时间。

请求10次和20次的时间分别如下所示：

```
➜ python3 1.py  10
spend time : 0.9282660484313965
➜ python3 1.py  20
spend time : 1.732438087463379
```

可以看到，速度慢的跟蜗牛一样。

### 0x02 改进1-并发 

为了加快请求的速度，很容易想到我们可以使用并发的方式进行，那么最好的方式就是使用多线程了。修改后的代码如下：

```python
#coding:utf-8 
# 多线程

import time 
import socket
import sys
import threading 

def doRequest():
    sock = socket.socket()
    sock.connect(('www.baidu.com',80))
    sock.send("GET / HTTP/1.1\r\nHost: www.baidu.com\r\nConnection: Close\r\n\r\n".encode("utf-8"))
    response = sock.recv(1024)
    return response

def main():
    start = time.time()
    threads = []
    for i in range(int(sys.argv[1])):
        # doRequest()
        threads.append(threading.Thread(target=doRequest,args=()))
    for i in threads:
        i.start()
    for i in threads:
        i.join()
    print("spend time : %s" %(time.time()-start))
main()
```

使用线程之后，看一下请求10次和20次的时间：

```python
➜  python3 2.py  10
spend time : 0.1124269962310791
➜ python3 2.py  20
spend time : 0.15438294410705566
```

速度明显快了很多，几乎是刚才的10倍了。

但是python的线程是有问题的，因为一个python进程中，同一时刻只允许一个线程运行，正在执行的线程会获取到GPL。做阻塞的系统调用时，例如`sock.connect()`,`sock.recv()`时，当前线程会释放GIL，让别的线程有机会获取GPL，然后执行。但是这种获取GPL的调度策略是抢占式的，以保证同等优先级的线程都有均等的执行机会，那带来的问题是：并不知道下一时刻是哪个线程被运行，也不知道它正要执行的代码是什么。所以就可能存在**竞态条件**。这种竞争有可能使某些线程处于劣势，导致一直获取不到GIL

比如如下的情况，线程1执行的代码如下：

```python
flag = True
while flag:
    pass  # 啥也不干
```

比如如下的情况，线程2执行的代码如下：

```python
flag = True
while flag:
    .....  # 这里省略一些复杂的操作,会调用多次IO操作
    time.sleep(1)
```

可以看到，线程1的任务非常简单，而线程2的任务非常复杂，这就会导致CPU不停地去执行线程1，而真正做实际工作的线程2却很少被调度到，导致了浪费了大量的CPU资源。

### 0x03 改进2-非阻塞方式 

在第一个例子中，我们意识到浪费了大量的时间，是因为我们用了阻塞的IO，导致CPU在卡在那里等待IO的就绪，那使用非阻塞的IO，是不是就可以解决这个问题了。

代码如下：

```python
#coding:utf-8 
import time 
import socket
import sys

def doRequest():
    sock = socket.socket()
    sock.setblocking(False)
    try:
        sock.connect(('www.baidu.com',80))
    except BlockingIOError:
        pass    

    # 因为设置为非阻塞模式了，不知道何时socket就绪，需要不停的监控socket的状态
    while True:
        try:
            sock.send("GET / HTTP/1.1\r\nHost: www.baidu.com\r\nConnection: Close\r\n\r\n".encode("utf-8"))
            # 直到send 不抛出异常，就发送成功了 
            break
        except OSError:
            pass
    while True:
        try:
            response = sock.recv(1024)
            break
        except OSError:
            pass
    return response
def main():
    start = time.time()
    for i in range(int(sys.argv[1])):
        doRequest()
    print("spend time : %s" %(time.time()-start))
    
main()
```

`sock.setblocking(False)`把socket设置为非阻塞式的，也就是说执行完`sock.connect()`和`sock.recv()`之后，CPU不再等待IO了，会继续往下执行，来看一下执行时间：

```
➜  python3 3.py  10
spend time : 1.0597507953643799
➜  python3 3.py  20
spend time : 2.0327329635620117
```

感觉被骗了，速度还是跟第一个一样啊，看来非阻塞IO并没有什么速度上的提升啊，问题出在哪里呢？看代码发现多了两个while循环：

```python
    while True:
        try:
            sock.send("GET / HTTP/1.1\r\nHost: www.baidu.com\r\nConnection: Close\r\n\r\n".encode("utf-8"))
            # 直到send 不抛出异常，就发送成功了 
            break
        except OSError:
            pass
    while True:
        try:
            response = sock.recv(1024)
            break
        except OSError:
            pass
```

因为把socket设置为非阻塞模式了，所以CPU并不知道IO什么时候就绪，所以必须在这里不停的尝试，直到IO可以使用了为止。

**虽然 connect() 和 recv() 不再阻塞主程序，空出来的时间段CPU没有空闲着，但并没有利用好这空闲去做其他有意义的事情，而是在循环尝试读写 socket （不停判断非阻塞调用的状态是否就绪）。**

有没有办法让CPU空闲出来的时间，不用来不停的询问IO，而是干别的更有意义的事情呢，等IO就绪后再通知CPU回来处理呢？当然有了，那就是回调。

### 0x04 改进3-回调

操作系统已经把IO状态的改变封装成了事件，如可读事件、可写事件。并且可以为这些事件绑定处理函数。所以我们可以使用这种方式，为socket的IO状态的变化绑定处理函数，交给系统进行调动，这样就是回调方式。python的select模块支持这样的操作。

代码如下：

```python
#!/usr/bin/env python
# encoding: utf-8

import socket
from selectors import DefaultSelector, EVENT_WRITE, EVENT_READ
import sys
selector = DefaultSelector()
stopped = False
urls_todo = []

class Crawler:
    def __init__(self, url):
        self.url = url
        self.sock = None
        self.response = b''

    def fetch(self):
        self.sock = socket.socket()
        self.sock.setblocking(False)
        try:
            self.sock.connect(('www.baidu.com', 80))
        except BlockingIOError:
            pass
        selector.register(self.sock.fileno(), EVENT_WRITE, self.connected)

    def connected(self, key, mask):
        selector.unregister(key.fd)
        get = 'GET {0} HTTP/1.0\r\nHost: www.baidu.com\r\n\r\n'.format(self.url)
        self.sock.send(get.encode('ascii'))
        selector.register(key.fd, EVENT_READ, self.read_response)

    def read_response(self, key, mask):
        global stopped
        # 如果响应大于4KB，下一次循环会继续读
        chunk = self.sock.recv(4096)
        if chunk:
            self.response += chunk
        else:
            selector.unregister(key.fd)
            urls_todo.remove(self.url)
            if not urls_todo:
                stopped = True

def loop():
    while not stopped:
        # 阻塞, 直到一个事件发生
        events = selector.select()
        for event_key, event_mask in events:
            callback = event_key.data
            callback(event_key, event_mask)
            
if __name__ == '__main__':
    import time
    start = time.time()
    for i in range(int(sys.argv[1])):
        urls_todo.append("/"+str(i))
        crawler = Crawler("/"+str(i))
        crawler.fetch()
    loop()
    print("spend time : %s" %(time.time()-start))   
```

监控socket的状态，如果变为可写的，就往里面写数据

```
selector.register(self.sock.fileno(), EVENT_WRITE, self.connected)
```

监控socket的状态，如果变为可读的，就外读数据

```
selector.register(key.fd, EVENT_READ, self.read_response)
```

测试一下速度：

```
➜  python3 4.py 10
spend time : 0.03910994529724121
➜  python3 4.py 20
spend time : 0.04195284843444824
```

 我们看到速度已经有个一个质的飞跃了，但是回调用一些严重的问题，会破坏代码的本来的逻辑结构，造成代码可读性很差。

比如我们有函数 funcA,funcB,funcC三个函数，如果funcC处理的结果依赖于funcB的处理结果，funcB的处理结果依赖于funcA的处理结果，而funcA又是回调的方式调用的，所以就不知道funcA什么时候返回，所以只能将后续的处理都作为callback的方式传入funcA中，让funcA执行完了可以执行funcB，funcB执行完了可以执行funcC，看起来像下面这样：

```
funcA(funcB(funcC()))
```

这就形成了一个链式的回调，跟最初的代码逻辑完全相反，本来的逻辑应该是这样的。

```
funcC(funcB(funcA()))
```

因为这样的链式回调的出现，导致了理解代码逻辑困难，并且错误处理困难。

有没有方法避免这种地狱式的链式回调的呢？

### 0x05 改进4-利用生成器 

可以利用python的生成器，把发请求的函数写成一个生成器，然后只监控IO的状态，当IO状态发生改变之后，就给生成器传送值，驱动生成器进行下一步操作，这样就可以避免回调了，具体实现如下：

```python
import select
import socket
import time
import sys

num = int(sys.argv[1])

def coroutine():
    sock = socket.socket()
    sock.setblocking(0)
    address = yield sock
    try:
        sock.connect(address)
    except BlockingIOError:
        pass
    data = yield
    size = yield sock.send(data)
    yield sock.recv(size)

def main():
    inputs = []
    outputs = []
    coros = []
    coro_dict = dict()
    for i in range(num):
        coros.append(coroutine())
        sock = coros[-1].send(None)   # 发送一个None值来启动生成器
        outputs.append(sock.fileno()) # 
        # print(outputs)
        coro_dict[sock.fileno()] = coros[-1]
        coros[-1].send(('www.baidu.com', 80))
    while True:
        r_list,w_list,e_list = select.select(inputs,outputs, ())
        for i in w_list:
            # print(type(i))
            coro_dict[i].send(b'GET / HTTP/1.1\r\nHost: www.baidu.com\r\nConnection: Close\r\n\r\n')
            outputs.remove(i)
            inputs.append(i)
        for i in r_list:
            coro_dict[i].send(1024)
            inputs.remove(i)
        if len(inputs) == len(outputs) == 0:
            break   
    # time.sleep(2)
    # coro.send(b'GET / HTTP/1.1\r\nHost: www.baidu.com\r\nConnection: Close\r\n\r\n')
    # select.select(wait_list, (), ())
    # print(coro.send(1024))

start  = time.time()
main()
print("spend time : %s" %(time.time()-start))
```

可以看到把发起请求的函数写成了一个生成器：

```python
def coroutine():
    sock = socket.socket()
    sock.setblocking(0)
    address = yield sock
    try:
        sock.connect(address)
    except BlockingIOError:
        pass
    data = yield
    size = yield sock.send(data)
    yield sock.recv(size)
```

然后监控IO状态，当IO状态发生改变之后，驱动生成器继续运行。

```python
while True:
        r_list,w_list,e_list = select.select(inputs,outputs, ())
        for i in w_list:
            # print(type(i))
            coro_dict[i].send(b'GET / HTTP/1.1\r\nHost: www.baidu.com\r\nConnection: Close\r\n\r\n')
            outputs.remove(i)
            inputs.append(i)
        for i in r_list:
            coro_dict[i].send(1024)
            inputs.remove(i)
```

看一下程序执行时间：

```
➜  python3 5.py 10
spend time : 0.058114051818847656
➜  python3 5.py 20
spend time : 0.0949699878692627
```

效果貌似非常的棒啊，执行的太快了，但是当我执行300次请求的时候，我就发现问题了，返回的非常慢，。估计原因可能是select是顺序遍历每一个IO描述符的去做状态检查，当IO描述符过多的时候，会导致遍历的速度比较慢，所以造成时间花费很大。

上面的代码看起来太复杂了，能不能简单点呢? 答案是可以。

### 0x06 改进5-利用python的异步IO库asyncio和aiohttp

要想看懂asyncio的代码的话，还需要先学习一些基础知识。

#### yield from 

yield我们都用过，用来产生一个生成器，但是yield from是用来干什么的？ 

简单的说，就是让生成器进行嵌套，在一个生成器里面可以使用另外一个生成器，允许一个`generator`生成器将其部分操作委派给另一个生成器。

对于简单的迭代器，`yield from iterable`本质上等于`for item in iterable: yield item`的缩写版，如下所示：

```python
>>> def g(x):
...     yield from range(x, 0, -1)
...     yield from range(x)
...
>>> list(g(5))
[5, 4, 3, 2, 1, 0, 1, 2, 3, 4]
```

然而，不同于普通的循环，`yield from`允许子生成器直接从调用者接收其发送的信息或者抛出调用时遇到的异常，并且返回给委派生产器一个值，如下所示：

```python
>>> def accumulate():    # 子生成器，将传进的非None值累加，传进的值若为None，则返回累加结果
...     tally = 0
...     while 1:
...         next = yield
...         if next is None:
...             return tally
...         tally += next
...
>>> def gather_tallies(tallies):    # 外部生成器，将累加操作任务委托给子生成器
...     while 1:
...         tally = yield from accumulate()
...         tallies.append(tally)
...
>>> tallies = []
>>> acc = gather_tallies(tallies)
>>> next(acc)    # 使累加生成器准备好接收传入值
>>> for i in range(4):
...     acc.send(i)
...
>>> acc.send(None)    # 结束第一次累加
>>> for i in range(5):
...     acc.send(i)
...
>>> acc.send(None)    # 结束第二次累加
>>> tallies    # 输出最终结果
[6, 10]
```

#### await 和 async的使用

在Python3.5中引入的async和await，可以将他们理解成asyncio.coroutine/yield from的完美替身。当然，从Python设计的角度来说，async/await让协程表面上独立于生成器而存在。

async可以使一个函数变成为一个生成器，如下代码：

```
In [40]: async def func2():
    ...:     pass
In [41]: def func1():
    ...:     pass
In [42]: c = func1()
In [43]: d = func2()
In [44]: c
In [45]: d
Out[45]: <async_generator object func2 at 0x110de1b40>
```

await可以看做是yield from的替身。

#### 异步IO实现代码如下

代码如下：

```python
#!/usr/bin/env python
# encoding: utf-8

import asyncio
import aiohttp
import sys

host = 'http://www.baidu.com'
loop = asyncio.get_event_loop()
async def fetch(url):
    async with aiohttp.ClientSession(loop=loop) as session:
        async with session.get(url) as response:
            response = await response.read()
            # print(response)
            return response
if __name__ == '__main__':
    import time
    start = time.time()
    tasks = [fetch(host) for i  in  range(int(sys.argv[1]))]
    loop.run_until_complete(asyncio.gather(*tasks))
    print("spend time : %s" %(time.time()-start))
```