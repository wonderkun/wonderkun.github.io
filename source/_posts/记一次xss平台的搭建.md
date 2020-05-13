---
title: 记一次xss平台的搭建
url: 352.html
id: 352
categories:
  - linux
date: 2016-04-20 15:02:14
tags:
  - xss
---

一直都在学xss，不过苦于没有xss平台啊，又不愿意去用别人的免费的xss平台（善于装x的人都这样！！！），所以就一直没有盲打实战的机会。近来这几天就寻思着在我vps上搭建一个，在搭建的过程中遇见了各种各样的问题啊，最后在我的好友yichin的帮助下，终于搞好啦，所以发篇博客记录一下，让想自己搭建xss平台的小伙伴们有个参考。

<!--more-->

好啦，直接来干货：

首先你得有个虚拟主机，或者服务器什么的，这写基础设备就不在说啦。
然后去网上找一套xss源码，我用的是这一个,<a href="http://www.1937cn.net/?p=203">点击下载</a>
下载完了之后上传到我的vps，因为是本地是windows，服务器是ubuntu，所以用pscp传到服务器上。
然后需要给我的vps安装php5和mysql，安装过程就是一直按回车……命令如下

[shell]
sudo apt-get install php5       #安装php5 
sudo apt-get install mysql-server      #安装mysql,注意设置密码，不要忘记了
sudo apt-get install phpmyadmin       #安装phpmyadmin
[/shell]

安装完成之后，需要看一下是否安装成功
具体操作如下

[shell]
sudo service apache2 start   #开启apache服务
cd  /var/www/html 
echo "&lt;?php phpinfo();  ?&gt;" &gt;index.php 
[/shell]

然后访问你的服务器：http://你的ip/index.php
如果出现一下界面，就说名你的php安装成功啦
<a href="/uploads/2015/07/搜狗截图15年07月03日0101_1.png"><img class="alignnone size-full wp-image-204" src="/uploads/2015/07/搜狗截图15年07月03日0101_1.png" alt="搜狗截图15年07月03日0101_1" width="638" height="587" /></a>
然后接下来就是在的/var/www/html文件夹下新建一个xss文件夹，然后修改xss文件的权限为755，把你的xss源码拷贝到这个文件夹下,然后解压一下

[shell]
cd  /var/www/html  
mkdir  xss           #新建一个xss文件夹
sudo chomd  755  xss    #把文件夹权限改为755
cp  ~/xss.zip  .     #把上传到服务器的xss源码拷贝到xss目录下，具体的路径和文件名，以你的为准
unzip  xss.zip       #解压   
[/shell]

然后大概有下面这些文件
<a href="/uploads/2015/07/搜狗截图15年07月03日0124_2.png"><img class="alignnone size-full wp-image-206" src="/uploads/2015/07/搜狗截图15年07月03日0124_2.png" alt="搜狗截图15年07月03日0124_2" width="772" height="293" /></a>
接下来看操作：
修改一下你的配置文件,按照下面的说明改

[shell]
sudo vim  config.php 
[/shell]

<a href="/uploads/2015/07/搜狗截图15年07月03日0139_4.png"><img class="alignnone size-full wp-image-209" src="/uploads/2015/07/搜狗截图15年07月03日0139_4.png" alt="搜狗截图15年07月03日0139_4" width="1212" height="349" /></a>
然后就是数据库的配置啦，

[shell]
service mysql start    #开启mysql服务
mysql  -u root    -p    #连接一下数据库  
[/shell]

<a href="/uploads/2015/07/搜狗截图15年07月03日0157_6.png"><img class="alignnone size-full wp-image-213" src="/uploads/2015/07/搜狗截图15年07月03日0157_6.png" alt="搜狗截图15年07月03日0157_6" width="827" height="263" /></a>
在我打箭头的地方数输入之前安装mysql数据库的时候设置的密码
接下来创建一个数据库

[shell]
creat database xssplatform  #创建一个名字为xssplatform的数据库，注意名字要和之前在配置文件中设置的一样
exit                        #退出mysql
mysql -u root  -p  xssplatform  &lt; /var/www/html/xss/xssplatform.sql   #导入sql文件到xssplatform数据库 
use xssplatform    #用xssplatform 数据库 
update  oc_module  SET code=REPLACE(code,'http://xsser.me','http://你的ip/xss')  #更新一下code的值 
exit 
[/shell]

然后，访问一下：
<a href="/uploads/2015/07/搜狗截图15年07月03日0217_7.png"><img class="alignnone size-full wp-image-215" src="/uploads/2015/07/搜狗截图15年07月03日0217_7.png" alt="搜狗截图15年07月03日0217_7" width="805" height="729" /></a>
让人欣喜若狂的页面终于出现了，但是却发现高兴的太早了，因为无法注册……
需要你修改点东西

[shell]
vim   /var/www/html/xss/config.php   
[/shell]

<a href="/uploads/2015/07/搜狗截图15年07月03日0222_8.png"><img class="alignnone size-full wp-image-217" src="/uploads/2015/07/搜狗截图15年07月03日0222_8.png" alt="搜狗截图15年07月03日0222_8" width="1015" height="247" /></a>

这样修改之后，就可以注册了，如果想让别人有邀请码才可以注册，需要把这个再改过来
<a href="/uploads/2015/07/搜狗截图15年07月03日0227_9.png"><img class="alignnone size-full wp-image-220" src="/uploads/2015/07/搜狗截图15年07月03日0227_9.png" alt="搜狗截图15年07月03日0227_9" width="779" height="523" /></a>

<a href="/uploads/2015/07/搜狗截图15年07月03日0228_10.png"><img class="alignnone size-full wp-image-221" src="/uploads/2015/07/搜狗截图15年07月03日0228_10.png" alt="搜狗截图15年07月03日0228_10" width="789" height="587" /></a>

<a href="/uploads/2015/07/搜狗截图15年07月03日0229_11.png"><img class="alignnone size-full wp-image-222" src="/uploads/2015/07/搜狗截图15年07月03日0229_11.png" alt="搜狗截图15年07月03日0229_11" width="919" height="539" /></a>

访问了一下 http://107.170.200.129/xss/PTmW5y?1435861703 发现404了，看了一下发现是地址重写的问题
操作如下：

[shell]
cd  /etc/apache2/mods-enabled     #进入apache2的配置项目录 
ln -s  ../mods-available/rewrite.load  rewrite.load  #创建一个名字为rewrite.load 的文件，连接到../mods-available/rewrit.load 文件 
ls  -al   #看一下是否创建成功   
[/shell]

如果有红框里面的文件，就说明创建成功啦
<a href="/uploads/2015/07/搜狗截图15年07月09日1631_1.png"><img class="alignnone size-full wp-image-225" src="/uploads/2015/07/搜狗截图15年07月09日1631_1.png" alt="搜狗截图15年07月09日1631_1" width="992" height="123" /></a>
接下来在你的xss目录下新建一个.htaccess的文件，文件内容如下
<a href="/uploads/2015/07/搜狗截图15年07月09日1634_2.png"><img class="alignnone size-full wp-image-226" src="/uploads/2015/07/搜狗截图15年07月09日1634_2.png" alt="搜狗截图15年07月09日1634_2" width="808" height="167" /></a>
文件内容贴出来，大家直接复制吧

[shell]
&lt;IfModule mod_rewrite.c&gt;
RewriteEngine on
RewriteRule ^([0-9a-zA-Z]{6})$ index.php?do=code&amp;urlKey=$1
RewriteRule ^do/auth/(w+?)(/domain/([w.]+?))?$ index.php?do=do&amp;auth=$1&amp;domain=$3
RewriteRule ^register/(.*?)$ index.php?do=register&amp;key=$1
RewriteRule ^register-validate/(.*?)$ index.php?do=register&amp;act=validate&amp;key=$1
RewriteRule ^login$   xss/index.php?do=login
&lt;/IfModule&gt;
[/shell]

接下来连入数据库，把自己的这个用户的adminlevel的值设置为1，接下来你就是超级管理员啦，可以给好朋友发要邀请码了
如果你发现有没有发邀请码的功能，或者说不能用，拿应该是文件权限的问题
官方的解决办法是，将xss这个文件夹的拥有者设置为apache2的内置账号，然后给这个问价夹一个744的权限
但是遗憾来了，我的vps没有apache2的内建账号，我是这样干的

[shell]
chmod  -R  777   xss   #先把文件权限设置为777，设置为755是不行的，因为在第一次用某些功能的时候，会创建一些文件
####权限给的太大，这样是不太安全的，所以等到你把所有的功能都用一下，发现没有问题之后，再把权限改过来
chmod   -R 755  xss  #修改文件权限完成，
[/shell]

xss平台搭建就基本完成啦，可以去盲打了
我的xss平台的地址是： <a href="http://107.170.200.129/xss">http://107.170.200.129/xss</a>
欢迎大家在我这里注册使用，在下面给我留言就可以啦，我会把邀请码发给大家。