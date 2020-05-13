---
title: linux (ubuntu)  清理系统日志
url: 428.html
id: 428
categories:
  - linux
date: 2016-05-17 14:38:47
tags:
  - linux
  - ubuntu
---

<!--more-->

我正在安安静静的写(xia)代(dian)码(ying)呢,突然系统报了一个错,说磁盘已经没有可用空间了,然后系统就卡死了..........

吓得我一阵紧张,赶紧把我存的电影全部删除了,然后查了一下磁盘占有量.

<img class="alignnone size-full wp-image-430" src="/uploads/2016/05/深度截图20160517143928.png" alt="深度截图20160517143928" width="731" height="293" />

删除我的视频之后我的硬盘才仅有9.4G的空间,我的空间都哪里去了???

然后在系统中搜索大文件,最后定位到我的/var/log目录

<img class="alignnone size-full wp-image-432" src="/uploads/2016/05/深度截图20160517144153.png" alt="深度截图20160517144153" width="619" height="398" />

我可爱的42G,就这么没了,呵呵呵呵呵呵.........

不得不说,日志是个好东西,但是像这样磁盘1/3都用来存储日志了,真是有点过了,所以定时做一些清理,是很必要的.

首先说一下错误的清理日志的方法

[bash]

rm -f logfile &nbsp;#这样做是错误的,因为应用已经打开文件句柄,这样操作会造成

#1.应用无法正确释放日志文件和写入

#2.显示磁盘空间未释放

[/bash]

百度了一下别人的方法:


[bash]

echo "" > /var/log/logfile  #第一种方法

cat  /dev/null >  /var/log/logfile  #第二种方法

[/bash]


但是这两种方法我执行之后是这样的结果:

<img class="alignnone size-full wp-image-433" src="/uploads/2016/05/深度截图20160517145243.png" alt="深度截图20160517145243" width="915" height="162" />

想想也对,我的sudo仅仅是对cat和echo 起作用,并没有对重定向起作用,所以就说没有权限.

我最后用的是下面这种办法


[bash]

echo -n  "" | sudo  tee /var/log/bootstrap.log   #这样就不会报错了

[/bash]


好了,写一个清理的脚本吧,其实可以把脚本加入到计划任务中去,定时清理.


[bash]

#!/bin/sh

sudo apt-get auto-clean
sudo apt-get clean
sudo apt-get autoremove

echo -n "" | sudo tee /var/log/messages
echo -n "" | sudo tee /var/log/user.log
echo -n "" | sudo tee /var/log/auth.log
echo -n "" | sudo tee /var/log/syslog
echo -n "" | sudo tee /var/log/apache2/access.log
echo -n "" | sudo tee /usr/local/nginx/logs/access.log
echo -n "" | sudo tee /usr/local/nginx/logs/error.log

exit

[/bash]


ok,运行一下,看一下磁盘,这下干净多了

<img class="alignnone size-full wp-image-434" src="/uploads/2016/05/深度截图20160517145958.png" alt="深度截图20160517145958" width="672" height="253" />

好了,继续看电影....,奥不对,写代码了.