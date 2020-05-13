---
title: 用模拟执行实现Objective-C代码自动化分析
url: 819.html
id: 819
categories:
  - 学习记录
date: 2020-03-2 12:01:27
tags:
  - binary
  - 学习记录
---



## 火眼高级逆向工程实验室脚本系列：用模拟执行实现Objective-C代码自动化分析


### 写在前面的话

<!-- 京东安全开源的 [qiling](https://github.com/qilingframework/qiling) 是一个很不错的想法，但是唯一的问题在于它实现的东西太多，比较笨重。有的时候我仅仅想模拟几个函数的执行,操作比较麻烦，并且不太直观。所以我在github上一顿搜索，最终发现了这个 [flare-emu](https://github.com/fireeye/flare-emu) 完全满足我直观，简单的需求。 -->
但是使用的时候发现它不支持python3，同时代码中 bytes 和 str 对象傻傻的分不清楚，所以不得不进行了一下修改，修改后的版本在[这里](https://github.com/wonderkun/flare-emu)(可能有些地方并没有修改完善，以后使用过程中发现问题再做修改吧)。下面就对官方的介绍文档进行了一个翻译。

<!-- more -->

原文链接: [ https://www.fireeye.com/blog/threat-research/2018/12/automating-objective-c-code-analysis-with-emulation.html]( https://www.fireeye.com/blog/threat-research/2018/12/automating-objective-c-code-analysis-with-emulation.html )


这是 FireEye 高级逆向工程团队公开的脚本系列的另一篇博文。今天我们分享一个新的  IDApython  库 - [flare-emu]( https://github.com/fireeye/flare-emu ),它依赖于 IDA pro和 Unicorn 仿真模拟框架，为 x86、x86_64、ARM和ARM64体系结构提供可脚本化的仿真功能，供逆向工程师使用。  除了这个库之外，我们还共享了一个使用它分析 Objective-C 代码的 IDAPython 脚本。请继续阅读以了解使用模拟器的一些创新的方法，这些方法可以帮你解决代码分析中遇到的问题，以及如何使用我们新的 IDAPython 库来节省您在此过程中的大量时间。


### 为什么要模拟执行？

如果你还没有使用模拟执行来解决代码分析中的问题，那你就已经跟不上潮流了。我将重点介绍它的一些优点和一些用例，以使您了解它的强大功能。仿真模拟是非常灵活的，并且当今可用的许多仿真框架（包括 Unicorn ）都是跨平台的。通过模拟执行，您可以选择要模拟执行的代码，并控制代码执行时的上下文信息。因为被模拟执行的代码无法访问运行它的操作系统的系统服务，所以几乎没有造成任何损坏的风险。所有这些优点使仿真成为临时实验，解决问题或自动化的绝佳选择。

### 使用场景

- 解码/解密/解混淆/解压缩 - 在进行恶意代码分析时，你经常会遇到用于解码、解压缩、解密或者解混淆一些有用数据(如字符串或者其他的payload)的函数。如果是常用的算法，你可以通过人工分析或者使用 [signsrch]( https://github.com/nihilus/IDA_Signsrch )之类的插件来解决，但是不幸的是，很多时候并不是这样的。然后，你要么打开调试器对样本进行插桩分析来解密数据，要么手动将函数转换为适合您当时需求的任何其他编程语言。这些选择可能很耗时且有一定的问题，具体取决于代码本身和要分析的样本的复杂性。此时，模拟执行通常可以为你提供更好的第三种选择。编写一个可以为您模拟执行功能的脚本将类似的功能提供给你，就好像您编写了该功能或正在从库中调用它一样。这样你就可以在不打开调试器的情况下，通过不同的输入重复使用相同的函数。这也适用于可以自解密的shellcode，你可以使用模拟器功能让代码自我解密。
- 数据跟踪 - 使用模拟器，您可以随时使用指令挂钩来停止和检查仿真上下文。将反汇编器和模拟器搭配，可以使你在关键指令上停止模拟并检查寄存器和内存的值。这样，您就可以在您感兴趣数据流过某个函数时对其进行标记。这里还有其他的几个有用的程序，正如以前在FLARE脚本系列的其他博客中介绍的那样，[自动函数参数提取]( https://www.fireeye.com/blog/threat-research/2015/11/flare_ida_pro_script.html )和[自动混淆字符串解码]( https://www.fireeye.com/blog/threat-research/2015/12/flare_script_series.html ),该技术可用于跟踪在整个程序中传递给给定函数的参数。函数参数跟踪是本文稍后介绍的Objective-C代码分析工具采用的技术之一。数据跟踪技术也可以用来跟踪C ++代码中的this指针，以便标记对象成员引用，或者标记从GetProcAddress / dlsym的调用返回的值，以便适当地重命名存储它们的变量。带来了很多可能性。

### flare-emu 简介

 FLARE (FireEye 高级逆向工程团队)团队正在介绍一个IDApython的库 [flare-emu](https://github.com/fireeye/flare-emu) ,该库将IDA Pro的二进制分析功能与Unicorn的仿真框架相结合，为用户提供了易用且灵活的脚本编写仿真模拟接口。flare-emu旨在处理所有内务处理，为其支持的体系结构设置灵活而强大的仿真器，以便您专注于解决代码分析问题。 当前，它提供了三种不同的接口来满足您的仿真需求，以及一系列相关的帮助程序和实用功能。

1.  emulateRange  - 该API用于在用户指定的上下文中模拟一系列指令或函数。它为各个指令以及遇到“call”指令时提供用户自定义的挂钩选项。用户可以决定模拟器是跳过还是调用函数中的代码。图1显示了 emulateRange 与指令和调用hook一起使用，以跟踪GetProcAddress调用的返回值，并将全局变量重命名为它们将指向的Windows API的名称。在此示例中，仅将其设置为从 0x401514 到 0x40153D 进行仿真。 该接口为用户提供了一种简单的方法来给寄存器和堆栈参数指定值。 如果指定了字节串，则将其写入仿真器的内存，并将指针写入寄存器或堆栈变量。 仿真后，用户可以使用 flare-emu 的其他的实用函数从仿真的内存或寄存器中读取数据，或者在flare-emu无法提供您所需的某些功能的情况下，使用返回的Unicorn仿真对象直接进行获取。

   emulateSelection是对emulateRange函数的简单封装，可用于模拟IDA Pro中当前高亮显示的指令范围。

   ![http://pic.wonderkun.cc/uploads/2020/03/Picture1.png](http://pic.wonderkun.cc/uploads/2020/03/Picture1.png)

​                         图1： emulateRange用于跟踪GetProcAddress的返回值

2. iterate - 此API用于强制向下模拟执行函数中的特定分支，以达到给定目标。用户可以指定目标地址列表，也可以指定函数的地址（从中使用对该函数的交叉引用的列表）作为目标，并指定达到目标时的回调。无论仿真期间可能导致采用不同分支的条件如何，都将达到目标。图2展示了为了达到目标而不得不进行迭代的一组代码分支。 cmp指令设置的标志无关紧要。 像emulateRange API一样，可以提供了用户定义的挂钩的选项，既可以用于单独的指令，也可以用于遇到“call”指令时。iterate API的一个示例用法是用于本文前面提到的函数参数跟踪技术。

   ![http://pic.wonderkun.cc/uploads/2020/03/Picture2.png](http://pic.wonderkun.cc/uploads/2020/03/Picture2.png)

​                                                                 图2：由 iterate  API确定的仿真路径，以便到达目标地址

3.  emulateBytes  - 该API提供了一种简单地模拟独立的shellcode的方法。 所提供的字节不会添加到IDB数据库中，而是直接照原样进行仿真。这对于准备仿真环境很有用,例如，flare-emu本身使用此API来操作Unicorn未公开的ARM64 CPU Model Specific Register（MSR）寄存器，以便启用 Vector Floating Point（VFP）指令和寄存器访问。 图3展示了为实现此目的的代码片段。 与emulateRange一样，如果flare-emu没有暴露用户所需的某些功能，则返回Unicorn仿真对象以供用户进一步探测。

   ![http://pic.wonderkun.cc/uploads/2020/03/Picture3.png](http://pic.wonderkun.cc/uploads/2020/03/Picture3.png)

   ​                                              图3：flare-emu使用emulateBytes为ARM64启用VFP

### API-Hooking

 如前所述，flare-emu 旨在让您轻松使用仿真来解决代码分析中的需求。模拟执行的一大痛点时对库函数调用的处理。flare-emu允许您选择需要跳过的call指令的同时，也支持你定义自己的hook函数来实现hook的函数被调用之后的特定功能。它自带有预定义的挂钩函数共80多个。这些函数包括许多常见的c运行时函数，这些函数将对你遇到的字符串和内存进行操作，以及与之对应的某些windows API。

#### example

图4显示了一些代码块，这些代码块调用一个函数，该函数需要一个时间戳值并将其转换为字符串。 图5显示了一个简单的脚本，该脚本使用flare-emu的迭代API在每个被调用的位置打印传递给该函数的参数。 该脚本还模拟了一个简单的XOR解码功能，并输出结果解码后的字符串。 图6显示了脚本的结果输出。

![http://pic.wonderkun.cc/uploads/2020/03/Picture4.png](http://pic.wonderkun.cc/uploads/2020/03/Picture4.png)

​                                                                              图4： 调用时间戳转换函数

![http://pic.wonderkun.cc/uploads/2020/03/Picture5.png](http://pic.wonderkun.cc/uploads/2020/03/Picture5.png)

​                                                                           图5： Simple example of flare-emu usage 

![http://pic.wonderkun.cc/uploads/2020/03/Picture6.png](http://pic.wonderkun.cc/uploads/2020/03/Picture6.png)

​                                                                        图6： Output of script shown in Figure 5 

这是一个[示例脚本]( https://github.com/fireeye/flare-emu/blob/master/rename_dynamic_imports.py )，该脚本使用flare-emu跟踪GetProcAddress的返回值并重命名它们相应存储的变量。 查看我们的自述文件以获取更多示例，并获得关于flare-emu的帮助。

```python
############################################
# Copyright (C) 2018 FireEye, Inc.
#
# Licensed under the Apache License, Version 2.0, <LICENSE-APACHE or
# http://apache.org/licenses/LICENSE-2.0> or the MIT license <LICENSE-BSD-3-CLAUSE or
# https://opensource.org/licenses/BSD-3-Clause>, at your option. This file may not be
# copied, modified, or distributed except according to those terms.
#
# Author: James T. Bennett
#
# IDApython script that names global variables after their import names when dynamically resolved using GetProcAddress
# Point it to a target function (or somewhere within the function) to begin emulation from
#
# Dependencies:
# https://github.com/fireeye/flare-emu
############################################

import flare_emu
import struct
import idc
import idautils
import logging


def makeName(addr, name):
    names = list(map(lambda x: x[1], list(idautils.Names())))
    i = 0
    myname = name
    while myname in names:
        myname = name + "_%d" % i
        i += 1

    idc.set_name(addr, myname, idc.SN_CHECK)


def instructionHook(uc, address, size, userData):
    try:
        eh = userData["EmuHelper"]
        if (idc.print_insn_mnem(address) == "mov" and
                idc.get_operand_type(address, 0) == 2 and
                idc.get_name(idc.get_operand_value(address, 0))[:6] == "dword_"):
            if "imp" in userData:
                makeName(idc.get_operand_value(address, 0), userData["imp"])
                del(userData["imp"])

    except Exception as err:
        print "Error in instructionHook: %s" % str(err)
        eh.stopEmulation(userData)


def callHook(address, argv, funcName, userData):
    try:
        eh = userData["EmuHelper"]
        # save last import string passed to a call to GetProcAddress
        if funcName == "GetProcAddress":
            arg = eh.getEmuString(argv[1])
            if len(arg) > 2:
                userData["imp"] = arg
            # for code that checks for a return value
            eh.uc.reg_write(eh.regs["ret"], 1)

    except Exception as err:
        print "Error in callHook: %s" % str(err)
        eh.stopEmulation(userData)


if __name__ == '__main__':
    eh = flare_emu.EmuHelper()
    sVa = idc.ida_kernwin.ask_str("0", 0, "Enter the start address (hex)")
    sVa = int(sVa, 16)
    eVa = idc.ida_kernwin.ask_str("0", 0, "Enter the end address (hex), specify 0 to emulate to end of function")
    eVa = int(eVa, 16)
    if (sVa >= idc.get_inf_attr(idc.INF_MIN_EA) and sVa <= idc.get_inf_attr(idc.INF_MAX_EA) and
            (eVa == 0 or (eVa >= idc.get_inf_attr(idc.INF_MIN_EA) and eVa <= idc.get_inf_attr(idc.INF_MAX_EA)))):
        if eVa == 0:
            eVa = None
        mu = eh.emulateRange(sVa, eVa, instructionHook=instructionHook, callHook=callHook)
    else:
        print "Error: supplied addresses not within IDB address range"
```

### 介绍 objc2_analyzer

(对object-c不太懂，不知道有没有说错的地方)

去年，我写了一篇博客文章向您介绍逆向macOS平台的Cocoa应用程序,文章地址在[这里]( https://www.fireeye.com/blog/threat-research/2017/03/introduction_to_reve.html ),该帖子包括一个简短的入门文章，介绍如何在后台调用Objective-C方法，以及这如何对IDA Pro和其他反汇编工具中的交叉引用产生的不利影响。帖子中还介绍了一个名为objc2_xrefs_helper的IDAPython脚本，以帮助解决这些交叉引用问题。 如果您尚未阅读该博文，建议您在继续阅读本博文之前先阅读该博文，因为它提供了使用objc2_analyzer特别有用的上下文。objc2_xrefs_helper的主要缺点是，如果选择器名称含糊不清，则意味着两个或多个类实现了具有相同名称的方法，脚本无法确定引用的选择器在二进制文件中任何给定位置所属的类，所以修复交叉引用时不得不忽略这种情况。现在，有了仿真支持，情况就不再如此。 objc2_analyzer使用flare-emu中的iterate API以及执行Objective-C反汇编分析的指令和调用挂钩，以确定为二进制形式的 objc_msgSend 变量的每次调用传递的id和selector。脚本功能的示例如图7和图8所示。

![http://pic.wonderkun.cc/uploads/2020/03/Picture7.png](http://pic.wonderkun.cc/uploads/2020/03/Picture7.png)

​                                                   图7：运行objc2_analyzer之前的Objective-C IDB代码段

![http://pic.wonderkun.cc/uploads/2020/03/Picture8.png](http://pic.wonderkun.cc/uploads/2020/03/Picture8.png)

​                                                  Figure 8: Objective-C IDB snippet after running objc2_analyzer 

请注意已对引用选择器的指令进行了修补，以改为引用实现功能本身，以便于转换。 添加到每个call中的注释使分析更加容易。 还创建了来自实现功能的交叉引用，以指向指向引用它们的objc_msgSend调用，如图9所示。

![http://pic.wonderkun.cc/uploads/2020/03/Picture9.png](http://pic.wonderkun.cc/uploads/2020/03/Picture9.png)

​                                                         图9：为函数实现添加到IDB的交叉引用

应当注意，从7.0开始的每个IDA Pro版本都对Objective-C代码分析和处理进行了改进。 但是，在撰写本文时，IDA Pro的最新版本为7.2，使用该工具仍可消除一些缺点，并添加了非常有用的注释。 objc2_analyzer以及我们的其他IDA Pro插件和脚本可在我们的[GitHub]( https://github.com/fireeye/flare-ida )页面上获得。

### 结论

flare-emu是一种灵活的工具，您可以在您的军械库中收藏它，它可以应用于各种代码分析问题。 在本博文中使用它提出并解决了几个示例问题，但这只是其应用可能性的一瞥。如果您没有尝试模拟解决代码分析问题的方法，我们希望您现在可以选择它。 而且，我们希望您能从使用这些新工具中受益匪浅！

