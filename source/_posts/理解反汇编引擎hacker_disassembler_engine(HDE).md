---
title: 理解反汇编引擎hacker_disassembler_engine(HDE)
url: 841.html
id: 841
categories:
  - 代码控
date: 2019-03-16 10:17:51
tags:
  - binary
  - disassm
  
---



我需要使用一个mini的反汇编引擎嵌入我的C项目中，能够做简单的指令分析工作，帮我区分操作码和数据。发现国外大佬写的Hacker_disassembler_engine很满足我的需求，但是奈何我看不懂啊，不得不学习一下intel的opcode，于是有了下文。


<!--more-->
## intel机器码

intel的指令体系为复杂指令系统（CISC），它这里的复杂绝非浪得虚名，由于以往的机器上内存是个很昂贵的设备，因此，intel的指令编码尽可能地利用了每一个bit，再加上兼容性的考虑，使得整个intel指令结构异常复杂。 

物理上，CPU的逻辑运算单元只操作计算机中的两个对象：寄存器和内存。除了这两个操作对象之外，还有一种对象，那就是立即数（immediate），物理上指令执行时，这个数字是在CPU中的，也就是CPU取得的指令中，这个数就已经在那里了。所有的指令编码都是围绕着这三个操作对象进行的，不同的是立即数不需要去找，寄存器简单的编码就行了，而内存不但需要指出其位置，还要指出其大小。此外，还有一些辅助的操作说明，比如是否重复一些操作等等。

### intel指令格式

看一下intel的确切的指令格式：

![http://pic.wonderkun.cc/uploads/2019/03/19559.jpg](http://pic.wonderkun.cc/uploads/2019/03/19559.jpg)
 prefix部分是指令操作的一些辅助说明，opcode编码了进行什么样的操作，跟汇编格式里面的mnemonic对应，CPU知道了什么操作之后就会寻找操作的对象，是寄存器还是内存？ModR/M部分就给出了操作的对象，R是register，M是memory，而Mod指示了到底是寄存器还是内存。如果ModR/M的字节数足够大的话，那么或许就不需要后面的两个部分了，实际上ModR/M只有一个字节，能编码所有的寄存器，却不能编码所有的内存寻址模式，intel使用后面两个部分来辅助ModR/M完成确切的内存定位SIB和displacement。寻址方式跟CPU对内存的管理密切相关，intel的寻址方式很多，但全部都编码到了SIB和displacement之中。但是需要注意一个OpCode不只对应一个mnemonic，一个mnemonic不只对应一个OpCode。 

### 定长指令

定长指令（指的是一个Opcode对应的指令长度是一定的），其对应的汇编指令格式是固定的（比如0X40不能加立即数和偏移量就只能表示inc eax；而B0只能加一个字节的立即数指令长度为2字节，B0 XX即为mov al,XX不能能表示其他任何指令），但不管是定长还是不定长的硬编码，其都可以从下面的Opcode Map表（TableA-2和TableA-3）中找查出来（红色圈出来的是比较重要的以及我们要分析的定长指令）：

![http://pic.wonderkun.cc/uploads/2019/03/20170823171705782.png](http://pic.wonderkun.cc/uploads/2019/03/20170823171705782.png)

一个1Byte的定长指令，其16进制为类似于“AB”的形式，而第一个A是Opcode Map表中的行号，第二个的B是其列号，行号和列号就能确定一个具体的指令。比如：第4行第5列索引出来的指令为（绿色圈出来）：`inc ebp`，第5行第0列为`push eax `等等。

但是由于指令的Opcode部分不止有一个字节的，还有两个字节的，那么两个字节的仅仅用该表是无法表示的，设计人员在设计时，留了一个特殊的位置即`0F`，`0F`作为两字节指令的第一字节，而第二字节再另外一张表中。也就是说所有两字节的指令都是以0F开头的（注意：这里说的两字节都是仅仅指Opcode的长度）。而另外一张表（TableA-4与TableA-5）如下所示：

![http://pic.wonderkun.cc/uploads/2019/03/20170823173339390.png](http://pic.wonderkun.cc/uploads/2019/03/20170823173339390.png)

来看几个一字节的指令，看一下规律：

```
50	<–> push eax
51	<–> push ecx
52	<–> push edx
53	<–> push ebx
54	<–> push esp
55	<–> push ebp
56	<–> push esi
57	<–> push edi

90 xchg eax,eax <==> nop
91	<–> xchg eax,ecx
92	<–> xchg eax,edx
93	<–> xchg eax,ebx
94	<–> xchg eax,esp
95	<–> xchg eax,ebp
96	<–> xchg eax,esi
97	<–> xchg eax,edi
```

这里可以发现一个规律，都是寄存器跟编号之间有一定的对应关系，比如0对对应eax,寄存器编号如下所示。

![http://pic.wonderkun.cc/uploads/2019/03/20170823180331161.png](http://pic.wonderkun.cc/uploads/2019/03/20170823180331161.png)

#### 修改EIP并且与JCC对应的定长指令

硬编码中的Opcode后面的立即数并非是跳转的地址，`跳转地址=当前指令地址+当前指令长度+imm`

##### 近距离JCC跳转

条件跳转：Opcode后面跟一个立即数的偏移，因此指令共两个字节(跳转地址只占有一个字节)
立即数是有符号的：最高位为0(7F)向下跳，最高位为1(80)向上跳

```
70	<–> JO(O标志位为1跳转)
71	<–> JNO
72	<–> JB/JNAE/JC
73	<–> JNB/JAE/JNC
74	<–> JZ/JE
75	<–> JNZ/JNE
76	<–> JBE/JNA
77	<–> JNBE/JA
78	<–> JS
79	<–> JNS
7A	<–> JP/JPE
7B	<–> JNP/JPO
7C	<–> JL/JNGE
7D	<–> JNL/JGE
7E	<–> JLE/JNG
7F	<–> JNLE/JG
```

##### 0F80~0F8F远距离JCC跳转

后面跟一个四字节的立即数，指令长共6字节`80000000~7fffffff`。

#### 其他修改EIP的指令

同JCC指令的硬编码一样，其硬编码中Opcode后面的立即数也不是要跳转的地址，计算方式同JCC相同：`跳转地址=当前指令地址+当前指令长度+imm`。

##### 与ECX相关的跳转指令（循环指令）

```c
E0	<–> loopne/loopnz Ib(dec ecx)	(ZF=0 && ECX != 0)
E1	<–> loope/loopz Ib(dec ecx)	(ZF=1 && ECX != 0)
E2	<–> loop Ib(dec ecx)	(满足ECX != 0就跳转)
E3	<–> jecxz/jrcxz Ib	(满足ECX=0跳转)
注意： Ib即为byte类型立即数（Immediate data），Iw则是Immediate data word，Id即为Immediate data dword，Ap即六字节长度的直接地址
```

测试如下：

![http://pic.wonderkun.cc/uploads/2019/03/20170823182949234.png](http://pic.wonderkun.cc/uploads/2019/03/20170823182949234.png)

##### 直接CALL与间接CALL

所谓直接call即编译时确定地址，间接call即地址存在内存中，并且在内存中的地址也是运行时才确定。

```
E8	<–> call Id
E9	<–> jmp Id
EA	<–> jmp Ap,jmp CS:Id	(**前四个字节为跳转地址，后两个字节为段选择子.**即高两字节赋给CS，低四字节赋给EIP)
EB	<–> jmp Ib
FF	<–> call dword ptr [edx]
```

E8call为直接call，call后面的地址即为要跳转的地址，FFcall为间接call，后面跟的内存那只能够存放着即将要跳转的地址。比如用对象指针访问一个普通成员函数和一个虚函数，其call的硬编码都不同：

![http://pic.wonderkun.cc/uploads/2019/03/20170823184446611-1.png](http://pic.wonderkun.cc/uploads/2019/03/20170823184446611-1.png)

##### ret和retf

```
C3	<–>ret	(pop eip)
C2	<–>ret Iw	(pop eip后，栈顶esp = esp + Iw)
CB	<–>retf	(出栈8字节，低四字节赋给EIP，高四字节的低两字赋给CS)
CA	<–>retf Iw	(在CB的基础上再做一步esp = esp + Iw)
```

#### 指令前缀

我们在上面提过，修改寄存器的指令中不存在16位寄存器修改的硬编码。而这些与16位寄存器相关的编码是通过加上`指令前缀（Instruction Prefixes）`的方式来实现的，有指令前缀则原本的32位寄存器操作指令，就会变为16位寄存器操作指令来用，不仅是定长指令如此，不定长指令也是如此。但指令前缀不仅能进行16位32位寄存器操作硬编码转换，我们一一来看几种常用的指令前缀：

##### 段前缀

首先在32位汇编中，8个段寄存器：ES、CS、SS、DS、FS、GS、LDTR、TR(顺序固定)，不再用段寄存器寻址而只做权限控制。段寄存器其实是个结构体，共96位，用汇编指令只能访问其中16位。

```
2E - CS
36 - SS
3E - DS
26 - ES
64 - FS
65 - GS
```

![http://pic.wonderkun.cc/uploads/2019/03/20170823190239236.png](http://pic.wonderkun.cc/uploads/2019/03/20170823190239236.png)

其中8925是Opcode，而不同的指令前缀代表了不同的段寄存器。

```
注意:如果没有特殊说明即没有人为指定段前缀，且中括号里面有寄存器的时候有如下约定:
1.[]里不存在ebp/esp/edi则默认为DS:[]
2.[]里存在ebp/esp则默认为SS:[]
3.[]里存在edi默认是ES:[],esi默认是DS:[]
```

##### 操作指令前缀：修改默认长度

这个即所谓指令前缀解决无16位寄存器操作指令的问题：`0X66`前缀修饰Opcode，则修正32位长度为16位：
如下所示（无论定长指令50还是不定长指令89均相同）：

![http://pic.wonderkun.cc/uploads/2019/03/20170823190715685.png](http://pic.wonderkun.cc/uploads/2019/03/20170823190715685.png)

##### 操作指令前缀:修改默认寻址方式

**0X67**作为前缀修改操作数宽度(将硬编码默认对应的操作数宽度改为16位)
如下所示（操作指令前缀将寻址方式按16位汇编的寻址方式进行寻址）：

![http://pic.wonderkun.cc/uploads/2019/03/20170823190949527.png](http://pic.wonderkun.cc/uploads/2019/03/20170823190949527.png)

同一Opcode因为有无指令前缀而长度不同，因此加上指令前缀前后相当于Opcode的指令长度也是不定的，但是这些“不定长”可预见的。有前缀则指令长度加一。而真正的不定长指令却不是如此的。

### 不定长指令

#### ModR/M

首先来看几条指令的通用公式

```
88  <–>mov Eb,Gb	
89	<–>mov Ev,Gv
8A  <–>mov Gb,Eb
8B	<–>mov Gv,Ev
```

这些指令都是可以从opcode map中查到的。

对几个关键词做如下解释：

```
G:通用寄存器
E:寄存器/内存
b:字节
v:word\double word\quadword(16/32/64位,取决于CPU模式)
```

##### 指令长度常规情况分析

如果确定是不定长指令，则其后必定存在一个字节的ModR/M，而ModR/M的bit信息指出了通用形式的不定长指令的具体形式，ModR/M的格式如下所示：

``` 
+------+-------+--------+
| 7,6  |5,4,3  |  2,1,0 |
+------+-------+--------+
  Mod  Reg/Opcode  R/M
```

**其中第3、4、5位三位即Reg/Opcode来确定是哪一个通用寄存器G**，（**暂时仅考虑Reg/Opcode中reg的情况**）；
**其它两部分来确定E是什么（R/M）以及具体细节。**

（Mod值有0-3四种情况、Reg/Opcode和R/M有0-7八种情况；Mod的00~10是内存，11是寄存器；R/M与Reg/Opcode的值即为寄存器的编号：eax/ax/al编号0、ecx/cx/cl编号为1…）

我们拿一条指令来具体分析：

```
测试一："88 01 02 03 04 05 06 …"
分析：
1. "88"我们知道其同通式是“mov Eb,Gb”，因此88是不定长指令，所以其后的一个字节"01"即为ModR/M；
2. 我们将“01”按照ModR/M的格式拆分成三部分：
01== 0000 0001 ==> 00 000 001三部分 ==> Mod=00=0，Eb即为byte ptr的内存；Reg/Opcode=000=0，即为eax/ax/al寄存器（Eb即byte则为al）；R/M=001=1，即为ecx
3. 确定出“8801”的汇编指令为：mov byte ptr [ecx],al ==>mov byte ptr ds:[ecx],al（没有指令前缀则DS是默认的）
4. 而“02 03 04 05 06…”就是下一条指令的编码了。
```

```
测试二：89 01 …(以32位CPU为准)
1. 由89可以确定是mov Ev,Gv格式（v在32位CPU下是dword）;
2. 01 == 00 000 001三部分 ==>Mod=00(DS:[])；Reg/Opcode=000(EAX)；R/M=001(ECX)
3. 所以汇编指令为:mov dword ptr ds:[ecx],eax
```

**以上计算步骤归结为一张表：**

![http://pic.wonderkun.cc/uploads/2019/03/20170824110923395.png](http://pic.wonderkun.cc/uploads/2019/03/20170824110923395.png)

该表分为五大块：寄存器编号部分的最上面一块，以及以Mod分界的下面的四块。用ModR/M解析出来的Reg/Opcode去第一块中查具体寄存器；以Mod和R/M去查Mod块中具体的某一行，最后再合并查到的各部分得到汇编指令。

```
测试三：8A 82 12 34 56 78
1. 8A确定是mov Gb,Eb格式;
2. 82 ==> 1000 0010 ==> 10 000 010三部分
3. 查表得Reg=al，Mod与R/M确定内存格式：disp32[edx]（disp32即32位偏移地址，在硬编码中高地址在低字节存放）
4. 汇编指令为:mov al,byte ptr ds:[edx+78563412]
```

##### 非常规情况分析

有一种特殊情况就是`Mod=00且R/M=101`时的情况（对应的ModR/M的值由05、0D、15、1D、25、2D、35、3D八种具体情况），这些情况只需要将原来的ebp换成一个disp32即可（该数即机器指令中紧接着ModR/M后面的四个字节）。这其实也是不需要其它辅助性工作就能解析出来的，测试如下：

![http://pic.wonderkun.cc/uploads/2019/03/20170824111514969.png](http://pic.wonderkun.cc/uploads/2019/03/20170824111514969.png)

#### ModR/M中的特殊情况与SIB引出

红框框出来的内容，仅仅依靠Table2-2一张表是无法解析出来的。还需要**SIB**和另外一张表（SIB的解析步骤归结的一张表）才能够解析的，Table2-2的Notes部分也提到了这张表Table2-3：

![http://pic.wonderkun.cc/uploads/2019/03/20170824125936480.png](http://pic.wonderkun.cc/uploads/2019/03/20170824125936480.png)

我们先来分析该表的一般情况：该表是根据SIB的bit信息来索引查看的，SIB是紧接着ModR/M的一个字节。不定长指令后必有ModR/M，而ModR/M的Mod不为"11"且R/M值为"100"（ESP）时则ModR/M后就有SIB。
我们先来看SIB的格式与解析方式：

```
+------+------------+--------+
| 7,6  |   5,4,3    | 2,1,0  |
+------+------------+--------+
scale      index       base
```

该三部分均存在于[]的括号中，格式为：Base + Index*2^(Scale)，Base为寄存器编号索引的寄存器，Index也是寄存器编号索引的寄存器，Scale为00~11，因此格式又为：Base + Index * 1/2/4/8所以格式形如：ds:[eax+ecx*4]。

```c
解析"88 84 48 12 34 56 78"：
1. Opcode = 88 --> 指令格式：mov Eb,Gb	
2. ModR/M = 84 --> 10 000 100 -->[reg+disp32]（普通格式）， al，esp
3. 由于Mod为10，且R/M为ESP，则属于特殊情况，不遵循普通格式，所以下一个字节为SIB（可确定汇编指令为：mov byte ptr [–][–][disp32],al）
4. [–][–]解析：SIB = 48H --> 01 001 000；Scale=1，Index=1（ECX），Base=0（EAX）
5. 得到汇编指令为：mov byte ptr [eax][ecx*2^1][78563412],al ==> mov byte ptr [eax+ecx*2+78563412],al
```

看一个例子：

```
00162560 >  888448 12345678 mov byte ptr ds:[eax+ecx*2+0x78563412],al
```

#### SIB中的特殊情况

其实就只有一种情况需要特别对待，我们知道[–][–]两部分分别为：[Base]和[Index * 2^(Scale) ]。若`index == 100（ESP）`则`[Index * 2^(Scale)]`部分不存在。

index 等于100（SIB = 64/65），base等于101与（65）否（64）,结果都一样（index都不存在）：

```
00162560 >  889C64 12345678 mov byte ptr ss:[esp+0x78563412],bl
00162560 >  889C65 12345678 mov byte ptr ss:[ebp+0x78563412],bl
```

## HDE反汇编结构体的理解

其实有了上面的预备知识，HDE中表示指令的结构体就容易完全理解了：

```c
typedef struct {
    uint8_t len;      /* len of command                                */
    uint8_t p_rep;    /* rep/repz (0xf3) & repnz (0xf2) prefix         */  
    uint8_t p_lock;   /* lock prefix: 0xf0                             */
    uint8_t p_seg;    /* segment prefix: 0x26,0x2e,0x36,0x3e,0x64,0x65 */
    uint8_t p_66;     /* operand-size override prefix: 0x66            */
    uint8_t p_67;     /* address-size override prefix: 0x67            */
    uint8_t opcode;   /* opcode                                        */
    uint8_t opcode2;  /* second opcode (if first opcode is 0x0f)       */
    uint8_t modrm;    /* ModR/M byte                                   */
    uint8_t modrm_mod;  /*   mod field of ModR/M                       */
    uint8_t modrm_reg;  /*   reg field of ModR/M                       */
    uint8_t modrm_rm;    /*   r/m field of ModR/M                      */
    uint8_t sib;         /* SIB byte                                   */
    uint8_t sib_scale;   /*   scale field of SIB                       */
    uint8_t sib_index;   /*   index field of SIB                       */
    uint8_t sib_base;    /*   base field of SIB                        */
    union {
        uint8_t imm8;      /* immediate value imm8                      */
        uint16_t imm16;    /* immediate value imm16                     */
        uint32_t imm32;    /* immediate value imm32                     */
    } imm;
    union {
        uint8_t disp8;     /* displacement disp8                        */
        uint16_t disp16;
        uint32_t disp32;
    } disp;
    uint32_t flags;        /* flags                                     */
} hde32s;
```

英文的注释还是不太明白，下面详细说一下每个字段的含义：

```
len : 当前指令的长度
p_rep： 为0xf3的时候是rep/repz，为0xf2的时候是repnz前缀，这两条指令是用来做循环的
p_lock： 0xf0前缀
p_seg：断前缀，2E - CS，36 - SS，3E - DS，26 - ES，64 - FS，65 - GS
p_66： 0x66前缀，修改默认的寄存器长度
p_67: 0x67前缀，修改默认寻址方式
opcode： 第一个操作码，也可能是0x0f(我们前面说0x0f也算前缀，他这里把他作为操作码了)
opcode2： 第二个操作码，只有当是以0x0f开头的指令，这里才会出现内容
modrm：  ModR/M byte字节,后面的三个是这个字节分开后的三块内容
modrm_mod：mod field of ModR/M 
modrm_reg：  reg field of ModR/M
modrm_rm： r/m field of ModR/M 
sib： SIB byte
imm：是这个指令的立即数
```

下面用一个包含modR/M,sib这样的变长指令做一个测试：

```c
	unsigned char code[] = { 0x88,0x84,0x48,0x12,0x34,0x56,0x78};
	hde32s hs;
	unsigned int length = hde32_disasm(code, &hs);
```

可以得到结构体如下：

![http://pic.wonderkun.cc/uploads/2019/03/20190315205133.png](http://pic.wonderkun.cc/uploads/2019/03/20190315205133.png)

这下舒服多了，终于看懂了。。。。

## 参考

[http://read.pudn.com/downloads128/ebook/543578/OpCode.pdf](http://read.pudn.com/downloads128/ebook/543578/OpCode.pdf)
[https://blog.csdn.net/Apollon_krj/article/details/77508073](https://blog.csdn.net/Apollon_krj/article/details/77508073)
[https://blog.csdn.net/Apollon_krj/article/details/77524601](https://blog.csdn.net/Apollon_krj/article/details/77524601)