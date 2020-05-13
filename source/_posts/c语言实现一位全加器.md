---
title: c语言实现一位全加器
url: 566.html
id: 566
categories:
  - 代码控
date: 2017-03-01 21:15:23
tags:
  - code
  - c
---

暑假的时候来信工所参加夏令营,当时面试的时候出了个题目说让我们不用加号实现两个数相加.
用c语言实现.当时不知道是紧张还是怎么了,改了好几次都没写对.

<!--more-->

现在马上要复试了,心里还是有些压力的,今晚没什么事情干,就敲两行代码.把这个实现一下.证明自己是会写的 
希望这次复试中的机试要做好点.

其实不用加号来实现加法,其实就是写一个全加器,知道了运算规则,就相当简单.
如果想写的复杂点,可以实现一下3位全加器或者4位全加器.

由于我逻辑运算忘记的差不多了,不太会写多位全加器的逻辑表达式了,这里就先写个一位的全加器吧. 

* 用 S(i)代表i位的最终结果,C(i)为第i位的进位,A(i)和B(i)分别代表两个加数
这逻辑关系可以表示为:
```
S(i) = A(i)^B(i)^C(i-1)
C(i) = (A(i)&B(i))|((A(i)^B(i))&C(i-1))
```
下面就是代码实现,比较简单,不再解释:

```c
#include <iostream>
#include <math.h>
using namespace  std; 

int add(int a,int b){
    bool a_array[32];  //存储a的二进制位
    bool b_array[32];  //存储b的二进制位 
    bool result[32]; //保存结果
    bool c=0; //用来保存进位 
    int res=0;

    int i;
    for(i=0;i<32;i++){
       a_array[i] = a & (1<<i);
       b_array[i] = b & (1<<i);  
       result[i] = a_array[i]^b_array[i]^c;
       c = (a_array[i]&b_array[i])|((a_array[i]^b_array[i])&c);
       res = res + (unsigned int)(result[i])*pow(2,i);   
    }
   
   return res;
}
int main(int argc ,char** argv){
      int a;
      int b;  
      cin>>a;
      cin>>b;
      cout<<add(a,b)<<endl;
      return 0;

}
```


