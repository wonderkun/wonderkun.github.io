---
title: 滥用具备RWX-S权限且有签名的dll进行无感知的shellcode注入
url: 1761.html
id: 1761
# password: LRczf@UYSRUqhO3Oz9py
categories:
  - 学习记录
date: 2022-04-16 16:16:34
tags:
  - shellcode
  - binary
  - windows
---

## 前言

常规的shellcode注入一般是通过`VirtualAllocEx`,`WriteProcessMemory` 和 `CreateRemoteThread` 来实现的，但是这种方式是被安全软件重点监控的，同时微软提供的ETW接口也是可以轻易检测出上述方式进行代码注入的痕迹。本文的核心是讲解怎么利用具备 RWX-S 权限且自身有签名的白DLL进行一种比较隐蔽的shellcode注入，
并讲解具体的代码实现以及在写代码实现的过程中遇到的坑。本方法是由文章提出的：https://billdemirkapi.me/sharing-is-caring-abusing-shared-sections-for-code-injection/ ，详情可以参考此文章。

<!-- more -->
## 基础知识回顾

PE文件的每个section都具备自己的权限，表明他被映射到虚拟内存之后的操作权限，也就是 `SECTION_CHARACTERISTICS` 这个字段，占四个字节。
通常来讲 `.text` 节区只具备 `IMAGE_SCN_MEM_READ` 和 `IMAGE_SCN_MEM_EXECUTE` 权限，`.data` 节区一般只具备 `IMAGE_SCN_MEM_READ`,`IMAGE_SCN_MEM_WRITE` 权限。 当PE文件被映射到内存后，对一个不具备 `IMAGE_SCN_MEM_WRITE` 权限的节区进行写操作或者对一个没有 `IMAGE_SCN_MEM_EXECUTE` 的节区进行执行时，都会报异常。

![](https://pic.wonderkun.cc//uploads/note/202204181752550.png)

看微软的文档：[document](https://docs.microsoft.com/en-us/windows/win32/debug/pe-format#section-flags), 会发现一个权限叫做 `IMAGE_SCN_MEM_SHARED`。 那共享到底意味着什么？据测试显示：**具备此权限的section会被当前系统所有的进程共享，如果进程A和进程B都加载了具备IMAGE_SCN_MEM_SHARED权限的模块C，那么模块C的此section在系统层面上只有一份，这也就意味着A进程对C的修改（有IMAGE_SCN_MEM_WRITE权限）会影响到B进程**

那么思路就来了，如果一个模块的某个节区是具备 `RWX-S` 权限，我只需要把它加载到进程A中，然后修改它的内容为恶意代码，然后想办法让他加载到进程B中，就可以实现在B中执行恶意代码了， 那这种利用主要分为如下几个步骤：

```
1. 找到一个有签名的并且具备 RWX-S 权限的dll。(不具备RWX-S权限也可以，可以patch系统内的已签名的dll，但是这样会破坏签名，不够隐蔽)
2. 将DLL加载到进程A的内存里，修改 RWX-S 权限的section的代码进行patch
3. 调用  SetWindowsHookEx，使用DLL中的某个函数指针作为 HOOKPROC 参数，使得DLL被注入到目标进程B中。
4. 目标进程B加载DLL，并触发恶意代码执行。
```

至于怎么去找一个具备 RWX-S权限的签名dll，原文作者也提供了一个yara规则在virustotal上来筛选，不再细说:

```
import "pe"

rule RWX_S_Signed_Search
{
	meta:
		description = "Detects RWX-S signed binaries. This only verifies that the image contains a signature, not that it is valid."
		author = "Bill Demirkapi"
	condition:
		for any i in (0..pe.number_of_sections - 1): (
			(pe.sections[i].characteristics & pe.SECTION_MEM_READ) and
			(pe.sections[i].characteristics & pe.SECTION_MEM_EXECUTE) and
			(pe.sections[i].characteristics & pe.SECTION_MEM_WRITE) and
			(pe.sections[i].characteristics & pe.SECTION_MEM_SHARED) )
		and pe.number_of_signatures > 0
}
```

这里提供一个我找到的DLL: https://www.virustotal.com/gui/file/855277c0aeea89d17a07e27e9cf79c98b26e70e8e57561c4b592097e0032c4e9，
以后的代码都是基于此DLL完成的。

其实这里面最关键的是步骤二，主要涉及两个问题：

1. patch什么位置可以保证此DLL被进程B加载之后，恶意代码一定会被执行
2. patch成什么样的代码才能保证进程B不会因为运行异常而崩溃

先回答问题1：当前DLL被进程B加载后一定会被执行的有两个函数，分别是 `DllMain` 和 设置给 `SetWindowsHookEx` 的消息hook函数, 我觉得这两个函数中`DllMain`更合适被patch为恶意代码，理由是 `hook procedure` 在每次有对应消息需要处理的时候都会被调用，这会导致我们的恶意代码被执行很多次，这显然不是我们想要的。同时 `DllMain` 在被进程加载的那一刻就会执行，能够保证我们的shellcode在第一时间被执行。

## patch DllMain为恶意代码

此时就有人说了，patch DllMain很简单啊，加载这个dll之后，获取 imagebase，然后解析PE头找到entrypoint，将 msfvenom 生成的shellcode直接复制 imagebase + entrypoint 的位置就可以了。 开始我也是这么认为的，但是事实证明，这样不行。

我们来看 DllMain的函数声明：

```c++
BOOL WINAPI DllMain(
    HINSTANCE hinstDLL,  // handle to DLL module
    DWORD fdwReason,     // reason for calling function
    LPVOID lpReserved )  // reserved
{
    // Perform actions based on the reason for calling.
    switch( fdwReason ) 
    { 
        case DLL_PROCESS_ATTACH:
         // Initialize once for each new process.
         // Return FALSE to fail DLL load.
            break;

        case DLL_THREAD_ATTACH:
         // Do thread-specific initialization.
            break;

        case DLL_THREAD_DETACH:
         // Do thread-specific cleanup.
            break;

        case DLL_PROCESS_DETACH:
         // Perform any necessary cleanup.
            break;
    }
    return TRUE;  // Successful DLL_PROCESS_ATTACH.
}
```

此函是有返回值的，当对应的 `fdwReason` 操作成功后，必须返回 TRUE/FALSE。 此函数直接被替换为 meterpreter 的 shellcode，就会导致此函数无法返回。这种情况下的DLL加载是在系统新开的一个线程中完成的，如果 `DllMain` 回调函数不返回，系统就会kill掉这个线程，以至于我们自己的恶意代码无法持续的执行，那解决办法就是要在 `DllMain` 中新开一个线程，在线程里执行恶意代码，然后此函数返回。

**由于这一段代码需要在B进程的进程空间中执行，此时没有任何地址相关的信息，所以这一段代码必须要写成shellcode才能正常执行**
由于要自己写一段shellcode，那我们就没有必要再去使用 `meterpreter` 的shellcode了，也就是说这一段代码要完成 `meterpreter` 第一阶段的功能，直接下载stage2 的代码，然后使用 `CreateThread`进行执行，所以基本的代码框架：

```c++
BOOL WINAPI DllMain(
    HINSTANCE hinstDLL,  // handle to DLL module
    DWORD fdwReason,     // reason for calling function
    LPVOID lpReserved )  // reserved
{
    switch( fdwReason ) 
    { 
        case DLL_PROCESS_ATTACH:{
            // 1. 加载 ws2_32.dll 
            // 2. 获取与socket相关的函数的地址
            // 3. 连接socket, 如果连接失败，返回FALSE 
            // 4. 申请内存空间,下载payload
            // 5. 调用 CreateThread 执行payload ，然后返回 TRUE
            break;
        }
        case DLL_THREAD_ATTACH:
            break;
        case DLL_THREAD_DETACH:
            break;
        case DLL_PROCESS_DETACH:
            break;
    }
    return TRUE;  // Successful DLL_PROCESS_ATTACH.
}
```

要完成这样一段shellcode，我们是需要再创建一个项目，然后编写相关的c或者汇编代码，编译完成之后把相对于的16进制copy到当前的项目中来，这样做一方面比较麻烦，容易出错；另一方面不太灵活，不便于替换c2地址等操作。

**我想要就在当前项目中完成，编译完之后，运行时patch进去，要怎么做呢？**

仔细想一下，当 `DllMain`回调函数被执行的时候，难道真的任何地址信息都没有提供吗？其实不然。
看 `DllMain` 的第一个参数 `hinstDLL` 的值其实就是当前被加载模块的基址，有了这个基址，理论上我们就可以访问到当前模块任何地址空间数据。

那思路有了: 我们可以让进程A向 DLL 相对于 `imageBase` 固定偏移的地方写入一些必要的函数指针和数据，例如`LoadLibraryA`，`GetProcAddress`的函数的地址，以及 c2 的ip 和端口信息，然后 `DllMain` 被调用的时候会到指定偏移的地方读取这些数据，完成自己的功能，示意图如下：

![](https://pic.wonderkun.cc//uploads/note/202204182132688.png)

下面实现就比较简单了，首先需要定义一下要向DLL中写入的数据的结构：

![](https://pic.wonderkun.cc//uploads/note/202204182137405.png)

其中 `fn` 开头的存储的是对应函数的指针，`char`数组保存的是一些字符串信息，便于利用这些字符串获取到socket相关的函数的地址。最后 host 和 port 存储的c2的信息，flag是`meterpreter`第一阶段向第二阶段的传参约定数据。不了解的可以去读一下 `meterpreter`的源码，这里不再细说他的相关细节。

接下来将这个结构体初始化，然后放到固定偏移 `OFFSET_TO_SHELLCODE` 上去：

![](https://pic.wonderkun.cc//uploads/note/202204182144848.png)

然后开始编写伪造的DllMain，也就是shellcode的主体代码，如下:

首先读取指定偏移获取之前存储的数据：

![](https://pic.wonderkun.cc//uploads/note/202204182158887.png)

然后当 `DLL_PROCESS_ATTACH` 发生时，调用执行相关的操作加载远程的恶意代码：

![](https://pic.wonderkun.cc//uploads/note/202204182200356.png)

然后将这段代码patch到DllMain的位置：

![](https://pic.wonderkun.cc//uploads/note/202204182203333.png)

`ShellCodeEnd` 是我定义的一个空的函数，他紧跟在`myDllMain`后面，主要是为了帮助我们定位出函数`myDllMain`在文件中的大小。

## patch hook procedure 函数防止程序崩溃

只经过上述patch的DLL是可以满足执行恶意代码的功能，但是会引起被注入程序的异常或者崩溃，因为我们是调用 `SetWindowsHookEx` 设置的消息钩子，我们传入的 `hook procedure` 也并非一个钩子处理函数，它并不会调用 `CallNextHookEx` ，就导致被注入的进程无法响应相关的消息，甚至运行异常代码而崩溃，这样会导致获取的session挂掉， 因此这里也需要对 `hook procedure` 进行代码patch。

![](https://pic.wonderkun.cc//uploads/note/202204182211988.png)

这里就是使用传统的shellcode的写法，就是获取 PEB ，遍历dll，然后加载 `CallNextHookEx` 并调用，这里使用了 `lazy_import` 的宏 `LI_FN`,他是可以自动展开为shellcode的，不需要自己再写了。

## 主程序

加载相关 RWX-S的模块，解析PE结构，获取相关的地址：

![](https://pic.wonderkun.cc//uploads/note/202204182220207.png)

设置消息钩子，进行dll注入。

![](https://pic.wonderkun.cc//uploads/note/202204182214469.png)

我这里sleep了200秒，然后卸载掉钩子，这个时间长度足够 `explorer.exe` 触发 `WH_GETMESSAGE` 消息，并上线了。

![](https://pic.wonderkun.cc//uploads/note/202204182217607.png)

当钩子被卸载之后，`KbdEditDllPremium.dll` 也会从内存中卸载，此时主程序其实可以直接删掉 `KbdEditDllPremium.dll`进行彻底的毁尸灭迹。

![](https://pic.wonderkun.cc//uploads/note/202204182222967.png)

内存里虽然已经没有了 `KbdEditDllPremium.dll` 模块，但是却依然不影响我们的session交互，因为此时的恶意代码运行在 `explorer.exe` 申请的堆空间上。

![](https://pic.wonderkun.cc//uploads/note/202204182224697.png)

这对于入侵痕迹的隐藏是非常有用的一个技巧。

## 补充说明

最后还需要再补充一下，因为要在此项目中要编译生成shellcode，所以要对一些编译选项就行一些调整，防止生成的代码无法在其他进程空间中运行。

![](https://pic.wonderkun.cc//uploads/note/202204190847820.png)

运行库选择MT，然后禁用GS保护。

![](https://pic.wonderkun.cc//uploads/note/202204190848574.png)

代码优化也需要调整一下。

**最后扩展一句：如果无法找到一个已经签名的RWX-S权限的dll，我们甚至可以修改系统的dll添加S权限，然后保存到临时目录，注入完成之后删除掉。**

为了避免安全风险，代码以及有RWX-S权限的签名DLL就不发源文件了，如果感兴趣，可以联系我获取。