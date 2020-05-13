---
title: php pwn学习入门一 (基础环境搭建)
url: 1680.html
id: 1680
categories:
  - 学习记录
date: 2020-5-12 19:57:14
tags:
  - php
  - pwn
  - web
  - 学习记录
---

## php pwn学习入门一 (基础环境搭建)

本文是学习php二进制漏洞利用的第一篇文章，本文主要简单说一下基础的环境搭建问题以及一个简单的栈溢出的利用过程。

<!-- more -->

### php不同的运行模式

SAPI(Server Application Programming Interface)是服务器端应用编程端口，它是应用层(比如 Apache，Nginx，CLI等)和 PHP 进行数据交互的入口。利用SAPI，php能够和其上的具体应用层进行解耦合，使得同一套php内核就可以和多种不同的应用层进行交互。在php的源代码sapi目录下有多种sapi的具体实现，比如cgi、cli、apache2handler、fpm等。

根据不同的上层应用，php使用的SAPI也不同，常见的搭配有`apache2+apache2handler`，`nginx+fpm`，当然也存在 `apache2 + cgi`的模式，不过由于性能问题，现在已经基本见不到了。(defcon曾经出过一个赛题叫shellql，就是 `apache2 + cgi` 模式下写shellcode，此模式相对于其他两种会简单一些，此处就不讲了)。

一般调试php，最好是能够自己重新编译一下php，这样的二进制有符号表，可以大大的提高了调试时的效率。

`nginx+fpm`的这种运行方式的调试我在复现CVE-2019-11043漏洞的那篇文章中说过，但是注意编译php时的参数选择，最主要的是`--enable-fpm --with-fpm-user=www-data --with-fpm-group=www-data`，其他的编译参数的含义可以直接使用`./configure --help`查看，偷懒的办法就是直接 pull php 官方提供的docker环境` php:version-fpm`，然后运行`php-config --configure-options`参考一下。

`apache2+apache2handler`运行模式下需要编译mod_php，就是俗称的 `libphp.so`，将它作为模块加载到apache2中执行，需要使用`--with-apxs2`来指定apache2的`apxs2`路径。在编译安装完成libphp.so之后，还无法启动apache2，因为php不支持apche2默认采用的`mpm_event`多线程管理技术，所以需要执行`a2dismod mpm_event && a2enmod  mpm_prefork`来启用php支持的`mpm_prefork`，具体的详情可以参考php官方文档[https://www.php.net/manual/en/install.unix.apache2.php](https://www.php.net/manual/en/install.unix.apache2.php)。我也在这里提供了一个Dockerfile例子[https://github.com/wonderkun/CTFENV/tree/master/libphp-extension-debug](https://github.com/wonderkun/CTFENV/tree/master/libphp-extension-debug)。

### De1CTF mixture 题解

这个题目按道理是比较简单的，但是当时做出来的人也不多，可能是被 `apache2+apache2handler` 这种运行模式吓到了，很有幸朋友 @lfy 在赛后给我提供了题目环境[https://github.com/wonderkun/CTF_web/tree/master/PHP_PWN_LEARN/stack_overflow](https://github.com/wonderkun/CTF_web/tree/master/PHP_PWN_LEARN/stack_overflow)。

为了调试的方便，以debug模式启动apache2: 

```bash
apachectl -X &
gdb -q -p `pidof apache2`
```

此题目是一个基础的栈溢出利用，由于可以直接写栈，所以可以直接构造 ROP chian来实现任意命令执行。但是由于溢出点的函数栈帧偏移无法被泄露出来，而且是64位的非交互环境，也无法直接跳到one_gadget，所以任意命令执行的参数构造还是有点麻烦，但是pwn师傅找的 gadget `mov QWORD PTR [rdx],rdi ; ret`，来进行参数构造的方法真是香(我完全想不到)，主要代码如下：

```python
for i in range(len(s)//8+1):
    payload+=p64(pop_rdx)
    payload+=p64(shell_addr+i*8)
    payload+=p64(pop_rdi)
    payload+= bytes(s[i*8:i*8+8].ljust(8,"\x00"),encoding="latin-1")
    payload+=p64(mov_rdx_rdi)
```

除此之外，在php扩展中，返回信息是通过结构体指针传出的，所以下图中的代码会修改栈上的数据，影响最后栈上的rop的执行，所以这里需要放一些无用的数据来防止破坏rop chain，在真实利用过程中此处使用4个pop操作进行绕过。

![http://pic.wonderkun.cc/uploads/2020/05/2020-05-13-12-26-17.png](http://pic.wonderkun.cc/uploads/2020/05/2020-05-13-12-26-17.png)

```python
pop4_ret=libc_addr+0x000000000002219e  # 0x7ffff711519e ;pop    r13 ; pop    r14 ;pop    r15;pop    rbp; ret
payload=p64(pop_rdx)*10+p64(pop4_ret)+p64(0)*4 + p64(pop4_ret)+p64(0)*4
```

最后一个问题是system函数中有指令 `movaps xmmword ptr [rsp+0x40], xmm0 `可能会导致崩溃，查了一些资料才知道 [http://blog.binpang.me/2019/07/12/stack-alignment/](http://blog.binpang.me/2019/07/12/stack-alignment/)，[http://homura.cc/blog/archives/168](http://homura.cc/blog/archives/168)，这条指令要求 rsp必须是16字节对齐的，所以需要修改一下栈布局，让调用system函数的时候rsp是16字节对齐的即可。

