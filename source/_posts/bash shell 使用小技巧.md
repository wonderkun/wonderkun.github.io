---
title: bash shell 使用小技巧
url: 383.html
id: 383
categories:
  - linux
date: 2016-05-05 21:47:42
tags:
  - linux
  - shell
---

近来一直在写一个python的分布式爬虫,写了很多的文件和目录,于是就想统计一下我到底这几天写了多少行代码,这么一个小功能如果也用python来实现,就有点杀鸡用牛刀的感觉了,所以第一想法就是用shell来写了,所以就有了下面这个文章.

<!--more-->

0x1.在其他语言中,如果想实现两个整数的相加求和,直接加就好了,但是bash中可不是你想的那样,例如:

```shell
#!/bin/bash
a=1
b=2

a=${a}+${b}
echo ${a}
```

运行这个,结果会让你目瞪口呆:

```
1+2   #结果是这样的,是不是想说......caocao
```

so,问题来了,我们到底该怎么加呢????

0x2.度娘了一下,我搜集了五种方法,(啥??竟然有五种,我一种都不知道!!!!!!!!)
概括起来如下:

```shell
# #!/bin/bash

a=1
b=2

# let a=${a}+${b} #第一种方法

# a=$((${a}+${b})) #第二种方法

# a=$[${a}+${b}] #第三种方法 

#a=`echo -e "${a} ${b}" | awk '{print $1+$2}'` #第四种方法 

a=`expr ${a} + ${b}`  #注意加号的左右都是有空格的.否则....... 你自己试试看
echo ${a}

```

不信你可以试一试,得到可爱的3还真有点不太容易啊

0x3.在写shell脚本的时候难免会遇到循环,但是怎是实现变量的自增呢???

其实跟上面的方法很类似,如下


```

i=0
while [ $i -lt 4 ];
do
echo $i;
# i=`expr $i + 1`;  #第一种
# let i+=1;             #二
# ((i++));               #三
# i=$[$i+1];          #四
i=$(( $i + 1 ))       #五
done

```

对于固定次数的循环，可以通过seq命令来实现，就不需要变量的自增了

代码如下,

```
#!/bin/bash
for j in $(seq 1 5)
do
  echo $j
done
```

<pre>0x4.好了,终于学会了加法,下面就看我怎么统计了</pre>

```
#!/bin/bash

# 递归搜索目录,获取路径

names=`find | grep 'py$'`   #只找py文件

line=0

for name in  ${names}
do

linetmp=`cat ${name} | wc -l`   #统计每个文件的行数
echo ${name} : ${linetmp}
line=$((line+linetmp))

done

echo "总行数:" ${line}

```

&nbsp;

好了,搞定.....