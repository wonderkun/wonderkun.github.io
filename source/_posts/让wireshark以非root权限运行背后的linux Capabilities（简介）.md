---
title: 让wireshark以非root权限运行背后的linux Capabilities（简介）
url: 571.html
id: 571
categories:
  - linux
date: 2017-03-02 12:54:45
tags:
  - linux
---

<!--more-->

## 0x1 加入linux Capabilities的背景知识  
Linux是一种安全操作系统，它给普通用户尽可能低的权限，而把全部的系统权限赋予一个单一的帐户--root。root帐户用来管理系统、安装软件、管理帐户、运行某些服务、安装/卸载文件系统、管理用户、安装软件等。另外，普通用户的很多操作也需要root权限，这通过setuid实现。

这种依赖单一帐户执行特权操作的方式加大了系统的面临风险，而需要root权限的程序可能只是为了一个单一的操作，例如：绑定到特权端口、打开一个只有root权限可以访问的文件。某些程序可能有安全漏洞，而如果程序不是以root的权限运行，其存在的漏洞就不可能对系统造成什么威胁。

从2.1版开始，内核开发人员在Linux内核中加入了能力(capability)的概念。其目标是消除需要执行某些操作的程序对root帐户的依赖。从2.2版本的内核开始，这些代基本可以使用了，虽然还存在一些问题，但是方向是正确的。

## 0x2 内核能力简介

传统UNIX的信任状模型非常简单，就是“超级用户对普通用户”模型。在这种模型中，一个进程要么什么都能做，要么几乎什么也不能做，这取决于进程的UID。如果一个进程需要执行绑定到私有端口、加载/卸载内核模块以及管理文件系统等操作时，就需要完全的root权限。很显然这样做对系统安全存在很大的威胁。

UNIX系统中的SUID问题就是由这种信任状模型造成的。例如，一个普通用户需要使用ping命令。这是一个SUID命令，会以root的权限运行。而实际上这个程序只是需要RAW套接字建立必要ICMP数据包，除此之外的其它root权限对这个程序都是没有必要的。如果程序编写不好，就可能被攻击者利用，获得系统的控制权。

使用能力(capability)可以减小这种风险。系统管理员为了系统的安全可以剥夺root用户的能力，这样即使root用户也将无法进行某些操作。而这个过程又是不可逆的，也就是说如果一种能力被删除，除非重新启动系统，否则即使root用户也无法重新添加被删除的能力。

Capabilities的主要思想在于分割root用户的特权，即将root的特权分割成不同的能力，每种能力代表一定的特权操作。例如：能力CAP_SYS_MODULE表示用户能够加载(或卸载)内核模块的特权操作，而CAP_SETUID表示用户能够修改进程用户身份的特权操作。在Capbilities中系统将根据进程拥有的能力来进行特权操作的访问控制。

在Capilities中，只有进程和可执行文件才具有能力，每个进程拥有三组能力集，分别称为cap_effective, cap_inheritable, cap_permitted(分别简记为:pE,pI,pP)：
> 1. cap_permitted表示进程所拥有的最大能力集；
> 2. cap_effective表示进程当前可用的能力集，可以看做是cap_permitted的一个子集
> 3. cap_inheitable则表示进程可以传递给其子进程的能力集。

系统根据进程的cap_effective能力集进行访问控制，cap_effective为cap_permitted的子集，进程可以通过取消cap_effective中的某些能力来放弃进程的一些特权。

可执行文件也拥有三组能力集，对应于进程的三组能力集，分别称为cap_effective, cap_allowed 和cap_forced（分别简记为fE,fI,fP）

> 1. cap_allowed表示程序运行时可从原进程的cap_inheritable中集成的能力集
> 2. cap_forced表示运行文件时必须拥有才能完成其服务的能力集
> 3. cap_effective则表示文件开始运行时可以使用的能力。

## 0x3 Linux内核中Capabilities的实现机制
Linux内核从2.2版本开始，就加进的Capabilities的概念与机制，并随着版本升高逐步得到改进。在linux中，root权限被分割成一下29中能力：
```
CAP_CHOWN:修改文件属主的权限
CAP_DAC_OVERRIDE:忽略文件的DAC访问限制
CAP_DAC_READ_SEARCH:忽略文件读及目录搜索的DAC访问限制
CAP_FOWNER：忽略文件属主ID必须和进程用户ID相匹配的限制
CAP_FSETID:允许设置文件的setuid位
CAP_KILL:允许对不属于自己的进程发送信号
CAP_SETGID:允许改变进程的组ID
CAP_SETUID:允许改变进程的用户ID
CAP_SETPCAP:允许向其他进程转移能力以及删除其他进程的能力
CAP_LINUX_IMMUTABLE:允许修改文件的IMMUTABLE和APPEND属性标志
CAP_NET_BIND_SERVICE:允许绑定到小于1024的端口
CAP_NET_BROADCAST:允许网络广播和多播访问
CAP_NET_ADMIN:允许执行网络管理任务
CAP_NET_RAW:允许使用原始套接字
CAP_IPC_LOCK:允许锁定共享内存片段
CAP_IPC_OWNER:忽略IPC所有权检查
CAP_SYS_MODULE:允许插入和删除内核模块
CAP_SYS_RAWIO:允许直接访问/devport,/dev/mem,/dev/kmem及原始块设备
CAP_SYS_CHROOT:允许使用chroot()系统调用
CAP_SYS_PTRACE:允许跟踪任何进程
CAP_SYS_PACCT:允许执行进程的BSD式审计
CAP_SYS_ADMIN:允许执行系统管理任务，如加载或卸载文件系统、设置磁盘配额等
CAP_SYS_BOOT:允许重新启动系统
CAP_SYS_NICE:允许提升优先级及设置其他进程的优先级
CAP_SYS_RESOURCE:忽略资源限制
CAP_SYS_TIME:允许改变系统时钟
CAP_SYS_TTY_CONFIG:允许配置TTY设备
CAP_MKNOD:允许使用mknod()系统调用
CAP_LEASE:允许修改文件锁的FL_LEASE标志
```
这些能力可以单独作为选项添加到进程的三个能力集合中去，为程序的权限控制提供更大的灵活性。

## 0x4 wireshark 的非root权限启动问题 
从Linux中第一次启动Wireshark的时候，可能会觉得奇怪，为什么看不到任何一个网卡，比如eth0之类的。这是因为，直接访问这些设备需要 root权限。然后，我就用root权限去用了。当然，这是一个不好的做法。比如Gentoo中就会提示：WIRESHARK CONTAINS OVER ONE POINT FIVE MILLION LINES OF SOURCE CODE. DO NOT RUN THEM AS ROOT.

那怎么办呢？Wireshark的leader Gerald Combs指出，现在多数Linux发行版都开始实现对raw网络设备使用文件系统权限（能力） ，可以用这个途径从普通用户启动Wireshark。
 
具体方法如下：
```bash
#1.安装setcap,setcap 是libcap2-bin包的一部分，一般来说，这个包默认会已经装好。
sudo apt-get install libcap2-bin
#2.创建Wireshark组。这一步在安装Wireshark的时候，也会完成。
#groupadd -g wireshark
#usermod -a -G wireshark <自己的用户名>
#chgrp wireshark /usr/bin/dumpcap
#chmod 4750 /usr/bin/dumpcap
#3.赋予权限。
sudo setcap cap_net_raw,cap_net_admin=eip /usr/bin/dumpcap
#可以使用 getcap /usr/bin/dumpcap验证，输出应当是：/usr/bin/dumpcap = cap_net_admin,cap_net_raw+eip
#现在wireshark 就可以用普通用户身份启动了

```

但是下面这个命令中的 eip后缀代表什么？ 

```bash
setcap cap_net_raw,cap_net_admin=eip /usr/bin/dumpcap
```
其实上面已经说过了，代表进程的三个能力集合

```
e  ->  cap_effective
i   ->  cap_inheritable  
p  ->  cap_permitted
```



#### Reference
[http://www.andy-pearce.com/blog/posts/2013/Mar/file-capabilities-in-linux/](http://www.andy-pearce.com/blog/posts/2013/Mar/file-capabilities-in-linux/)