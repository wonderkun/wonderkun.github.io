---
title: visual studio 2015上写x64位汇编
url: 780.html
id: 780
categories:
  - 代码控
date: 2019-03-11 17:25:59
tags:
	- binary
	- vs2015
	- asm
---

最近在做一个东西，有少部分的代码需要用汇编写，大部分都是c语言实现，而且还是x64的程序。配置单独的masm开发环境，独立编译然后链接过来，真实太费劲了，所以就想直接用visual studio吧。
vs上64位的编译器不支持内敛汇编了，只能写成单独的asm文件，然后独立编译。下面就介绍怎么让让vs2015上让项目支持对asm文件进行编译。

<!--more-->

### x01 配置项目

在项目上右键->生成依赖项->生成自定义

![http://pic.wonderkun.cc/uploads/2019/03/1552291498048.png](http://pic.wonderkun.cc/uploads/2019/03/1552291498048.png)

然后勾选，masm选项：

![http://pic.wonderkun.cc/uploads/2019/03/1552291644812.png](http://pic.wonderkun.cc/uploads/2019/03/1552291644812.png)

然后接下来就可以在项目的源文件中添加asm文件。

右键源代码->添加->添加新建项->文件后缀修改为asm。

### x02 在汇编中调用C函数和变量

比如我们的`main.c`中定义了一个函数，

```c
void myprint(void)
{
	printf("this is my function\n");
}
```

想要在汇编中调用，首先需要在项目头文件`stdafx.h`头文件中写如下的声明:

```c
extern "C"//防止函数被name mangling
{
	void myprint(void);
	__int64 g_iValue = 100; // 定义一个全局变量，注意用extern语法的时候声明和定义的区别。
}
```

这里用C的方式导出，防止函数名字被粉碎。

接下来，就需要在汇编中写代码来调用c中定义的函数和c中全局变量了。在`proc.asm`写如下代码

```
EXTERN  myprint:PROC  ;引用外部函数
EXTERN  g_iValue:DQ   ;引用外部变量，dq是QWORD，8字节的变量

.DATA
val1 DQ ?;自己定义变量

.CODE

func2 PROC
    sub rsp,28h  ; 这个地方可能是为了栈空间对齐，不这样做有可能会崩掉，原因未知。反正反汇编一x64的代码都有这个东西
	call myprint
	mov r10,g_iValue ; 此处使用中的stdafx.h全局变量。
    mov val1,r10  ; 使用自定义的变量
    mov rax,val1 ; 写入返回值
	add rsp,28h
	ret
FUNC2 ENDP
END

```

这样就可以实现在汇编中调用C的函数了。

### 0x3 在C语言中调用汇编的函数

上面代码写完之后，编译可以通过，但是我们并看不到执行的结果，因为汇编中的`func2`还并没有被我们调用，想要调用汇编中的`func2`，首先需要在头文件`stdafx.h`中做如下声明：

```c
extern "C" __int64 __stdcall func2();
```

然后在main函数中调用：

```c
int main()
{   
    __int64 ret = func2();
	printf("%ld",ret);
	return 0;
}

```

就可以看到输出：

```
this is my function
100
```

### 0x4 在汇编中调用win64 api

有时候需要在汇编中调用windows的64位的API，在调用API之前首先要明白函数调用约定。

在32位系统中我们调用的用户态API一般都遵循`WINAPI(__stdcall)`的调用约定,主要规则有两条: 1.  函数参数由右向左入栈;2. 函数调用结束后由被调用函数清除栈内数据（其实是被调者参数的清除）。所以在调用一个遵循`WINAPI`的函数之后，不需要自己来做被调函数栈空间的清除，因为被调函数已经恢复过了。而在x64汇编中，两方面都发生了变化。一是前四个参数分析通过四个寄存器传递：RCX、RDX、R8、R9，如果还有更多的参数，才通过椎栈传递。二是调用者负责椎栈空间的分配与回收。

下面写一个调用`MeesageBoxA`的实例代码：

```
INCLUDELIB kernel32.lib ; 告诉连接器链接这个动态库
EXTERN MessageBoxA:PROC  ; 引用 MessageBoxA函数

.DATA
; 定义局部变量
szCaption   db  '恭喜',0  
szText      db  '当您看到这个信息的时候，您已经可以编译Win32汇编程序了!',0  

.CODE
func2 PROC
    sub rsp,28h
    mov rcx, 0
    mov rdx, offset szText;
	mov r8, offset szCaption
    mov r9, 0
    call MessageBoxA 
	add rsp,28h  
	ret
FUNC2 ENDP
END
```

看雪上的大佬说`sub rsp,28h`是为了给被调用函数的参数和返回地址预留栈空间，这个说法应该是对的，不留会报错的。


至于语法高亮，可以使用`AsmDude`这个插件，还有代码提示功能，用起来很舒服。

### 推荐阅读

[https://www.cs.uaf.edu/2017/fall/cs301/reference/x86_64.html](https://www.cs.uaf.edu/2017/fall/cs301/reference/x86_64.html)

[https://bbs.pediy.com/thread-43967.htm](https://bbs.pediy.com/thread-43967.htm)