---
title: 杀软的无奈-手工构建免杀的ELF文件(四)
url: 1699.html
password: fakefake
id: 1699
categories:
  - 学习记录
date: 2021-05-16 19:57:14
tags:
  - 杀软的无奈
---


## 前言

在上一节我们已经通过自己编写的编码器对shellcode进行了编码，并且构建了一个ELF文件，但是出乎意料的是`McAfee` 和 `McAfee-GW-Edition` 还会报毒为木马，经过我的研究，我发现`McAfee`判黑的逻辑非常简单，只要文件大小小于某个阈值，并且`EntryPoint`附近有无法反汇编的数据，就会被报黑。这么看来，想让上一节的ELF文件不被所有的引擎检测就非常简单了，只需要在文件结尾再写一些乱数据就搞定了。

<!-- more -->

```python
import random
with open(FILENAME,"wb") as fd:
    fd.write( elf_header_bytes + elf_pheader_bytes + shellcode )
    fd.write( bytes( [ random.randint(0x00,0xff) for i in  range(1024)] ) )
```

![](https://pic.wonderkun.cc//uploads/note/20210614164029.png)

简单的这样操作一下就无法被检测出来了，从`McAfee`上的检测逻辑上就可以管中窥豹，看到杀软在做检测时候的无奈，所以恶意代码检测还是非常困难的 ...

直接填充垃圾数据来逃过检测肯定不是一个技术爱好者的最终追求，最好的方式还是去做一个真正看起来正常，并且执行起来也正常的ELF，这样才更具备更高的迷惑性。接下来的内容就开始一步步的实现这个目标。

## 链接视图和装载视图

ELF文件是`Executable and Linkable Format`(可执行与可链接格式)的简称，即可以参与执行也可以参与链接。从链接的角度来看，elf文件是`Section`(节)的形式存储的，而在装载的角度上，Elf文件又可以按`Segment`（段）来划分。区别就是在链接视角下，Program Header Table 是可选的，但是Section Header Table是必选的，执行视角的就会反过来。节信息是ELF中信息的组织单元，段信息是节信息的汇总，指出一大段信息(包含若干个节)在加载执行过程中的属性。

![](https://pic.wonderkun.cc//uploads/note/20210615001514.png)

由于在很多翻译文章中，段和节的概念总是混淆，导致傻傻分不清楚，所以在以后的文章中我们统一约定 `Segment` 为段，`Section`为节。

## 丰富手工构建的ELF文件的段信息

ELF文件常见的段类型有如下几种:

| 名字                | 取值                   | 说明                                                         |
| :------------------ | :--------------------- | :----------------------------------------------------------- |
| PT_NULL             | 0                      | 表明段未使用，其结构中其他成员都是未定义的。                 |
| PT_LOAD             | 1                      | 此类型段为一个可加载的段，大小由 p_filesz 和 p_memsz 描述。文件中的字节被映射到相应内存段开始处。如果 p_memsz 大于 p_filesz，“剩余” 的字节都要被置为 0。p_filesz 不能大于 p_memsz。可加载的段在程序头部中按照 p_vaddr 的升序排列。 |
| PT_DYNAMIC          | 2                      | 此类型段给出动态链接信息，指向的是 .dynamic 节。                                   |
| PT_INTERP           | 3                      | 此类型段给出了一个以 NULL 结尾的字符串的位置和长度，该字符串将被当作解释器调用。这种段类型仅对可执行文件有意义（也可能出现在共享目标文件中）。此外，这种段在一个文件中最多出现一次。而且这种类型的段存在的话，它必须在所有可加载段项的前面。 |
| PT_NOTE             | 4                      | 此类型段给出附加信息的位置和大小。                           |
| PT_SHLIB            | 5                      | 该段类型被保留，不过语义未指定。而且，包含这种类型的段的程序不符合 ABI 标准。 |
| PT_PHDR             | 6                      | 该段类型的数组元素如果存在的话，则给出了程序头部表自身的大小和位置，既包括在文件中也包括在内存中的信息。此类型的段在文件中最多出现一次。**此外，只有程序头部表是程序的内存映像的一部分时，它才会出现**。如果此类型段存在，则必须在所有可加载段项目的前面。 |
| PT_LOPROC~PT_HIPROC | 0x70000000 ~0x7fffffff | 此范围的类型保留给处理器专用语义。                           |

其中 `PT_LOAD` 和 `PT_DYNAMIC` 这两种类型的段在执行的时候会被加载到内存中去。
现在问题来了，我们现在需要为ELF文件伪造哪些段，并且分别存储什么样的数据才会显得像是一个正常的ELF文件呢？

**最好的学习方法是模仿**，我们打开一个gcc编译的正常的ELF文件，看一下明白了：


![](https://pic.wonderkun.cc//uploads/note/20210615103553.png)

可以看到主要有如下几个的段：

1. PT_PHDR: 不必再解释了。
2. PT_INERP: 指出了解释器的路径，一般的值为 `/lib/ld-linux.so.2`。 比较有意思的是如果把这个数据给修改了， 文件就无法正常执行了。例如下面的实验：

  ```bash
  $ strings ./a.out    | grep /lib/ld-linux  
  /lib/ld-linux.so.3
  # 把 PT_INERP 的数据修改为 '/lib/ld-linux.so.3' 

  $ ./a.out 
  bash: ./a.out: No such file or directory
  # 尝试执行就会报错，告诉你 ./a.out 文件存在

  $ /lib/ld-linux.so.2  ./a.out 
  dds

  # 使用 /lib/ld-linux.so.2 进行加载就可以正常执行 
  ```

3. PT_LOAD: 不必再解释了。
4. PT_DYNAMIC:  此类型段给出动态链接信息，指向的是 .dynamic 节。动态链接的ELF文件会有这个段。
5. PT_NOTE: 不必再解释了。
6. PT_GNU_EH_FRAME: 指向 .eh_frame_hdr 节，与异常处理相关，我们暂时先不关注
7. PT_GNU_STACK: 用来标记栈是否可执行的，编译选项 `-z execstack/noexecstack` 的具体实现。
8. PT_GNU_RELRO:  relro(read only relocation)安全机制，linker指定binary的一块经过dynamic linker处理过 relocation之后的区域为只读，从定位之后的函数指针被修改。

接下来我们为ELF文件伪造如下段: `PT_PHDR`,`PT_INERP`,`两个PT_LOAD`,`PT_NOTE`,还是接上一节的代码继续写:

```python

```



