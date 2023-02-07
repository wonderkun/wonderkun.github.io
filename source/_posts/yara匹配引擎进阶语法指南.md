---
title: yara匹配引擎进阶语法指南
url: 2787.html
id: 2787
categories:
  - 学习记录
date: 2022-12-16 16:16:34
tags:
  - binary
  - blue & red
---


## 前言

具备检测相关经验的同学可能都对yara匹配引擎比较熟悉了，看雪论坛上也有非常详细的翻译文章 - [编写Yara规则检测恶意软件](https://bbs.kanxue.com/thread-226011.htm)
本文主要对yara文档容易被忽略的部分进行了翻译和总结，并且给出一些进阶用法的例子，提高对yara匹配引擎语法的理解程度。

**<br />**参考文档：**<br />
[https://yara.readthedocs.io/en/v4.2.3/writingrules.html](https://yara.readthedocs.io/en/v4.2.3/writingrules.html)

## 匹配字符串
yara的匹配字符串可以使用一些修饰符，总结下来有如下部分：

| 关键词 | 支持的字符串类型 | 概括 | 限制 |
| --- | --- | --- | --- |
| nocase | 文本，正则表达式 | 忽略大小写 | 不能与xor、base64、 或base64wide一起使用 |
| wide | 文本，正则表达式 | 通过交错空 (0x00) 字符来模拟 UTF16 | 无 |
| ascii | 文本，正则表达式 | 匹配 ASCII 字符，仅在wide使用时才需要 | 无 |
| xor | 文本 | 匹配具有单字节键的 XOR 文本字符串 | 不能与nocase、base64、 或base64wide一起使用 |
| base64 | 文本 |  base64 编码的字符串(分割成3条) | 不能与nocase、xor、 或fullword一起使用 |
| base64wide | 文本 |  base64 编码的字符串(分割成3条)，然后交错空字符，如 wide | 不能与nocase、xor、 或fullword一起使用 |
| fullword | 文本，正则表达式 | 匹配前后没有字母数字挨着的字符(串) | 不能与base64或一起使用base64wide一起使用 |
| private | 十六进制、文本、正则表达式 | 匹配不包含在输出中 | 无 |

### base64修饰符
```bash
rule Base64Example1
{
    strings:
        $a = "This program cannot" base64

    condition:
        $a
}
```
将至少会匹配如下三个字符串：
```bash
VGhpcyBwcm9ncmFtIGNhbm5vd
RoaXMgcHJvZ3JhbSBjYW5ub3
UaGlzIHByb2dyYW0gY2Fubm90
```
看起来很奇怪，原因如下：<br />**base64是将三个字节变成四个字节，如果不能被整除，那就会涉及到补位，同样的字符串可能因为前缀的不一样导致编码结果不同，这个不一致的循环次数是3，看如下的编码结果就明白了。**<br />![image.png](https://intranetproxy.alipay.com/skylark/lark/0/2022/png/327065/1665999287509-f33ed94f-782d-45be-b663-a578bd599ca0.png#clientId=u4e5591a9-74b3-4&errorMessage=unknown%20error&from=paste&height=208&id=ua1026f3d&name=image.png&originHeight=416&originWidth=980&originalType=binary&ratio=1&rotation=0&showTitle=false&size=97137&status=error&style=none&taskId=u30985312-8284-481f-b866-65b93522771&title=&width=490)<br />三个结果对应这三个不同前缀。<br/>详情请阅读文档：[https://www.leeholmes.com/searching-for-content-in-base-64-strings/](https://www.leeholmes.com/searching-for-content-in-base-64-strings/)<br />另外base64和base64wide修饰符支持自定义的字符码表，可以匹配一些被修改过的base64编码。

```bash
rule Base64Example2
{
    strings:
        $a = "This program cannot" base64("!@#$%^&*(){}[].,|ABCDEFGHIJ\x09LMNOPQRSTUVWXYZabcdefghijklmnopqrstu")

    condition:
        $a
}
```
### XOR修饰符
xor 修饰符是将声明的字符串按照 [0x01 - 0xFF] 都进行单字节异或，例如：
```bash
rule XorExample1
{
    strings:
        $xor_string = "This program cannot" xor

    condition:
        $xor_string
}
```
等价于：
```bash
rule XorExample2
{
    strings:
        $xor_string_00 = "This program cannot"
        $xor_string_01 = "Uihr!qsnfs`l!b`oonu"  // xor 0x1 
        $xor_string_02 = "Vjkq\"rpmepco\"acllmv" // xor 0x2 
        // Repeat for every single byte XOR
    condition:
        any of them
}
```
另外还支持参数，限定xor的范围：
```bash
rule XorExample5
{
    strings:
        $xor_string = "This program cannot" xor(0x01-0x3F)
    condition:
        $xor_string
}
```
## 匹配条件的语法
### 支持的运算符
所有运算符的优先级如下：

| 优先级 | 操作 | 描述 | 性质 |
| --- | --- | --- | --- |
| 1 | **[]**<br />**.** | Array subscripting   数组下标<br />Structure member access  结构成员访问 | 从左到右 |
| 2 | **–**<br />**~** | Unary minus  按位减<br />Bitwise not  按位非 | 从右到左 |
| 3 | *****<br />**\\**<br />**%** | Multiplication  乘法<br />Division  除法<br />Remainder  取余 | 从左到右 |
| 4 | **+**<br />**–** | Addition  加法<br />Subtraction  减法 | 从左到右 |
| 5 | **<<**<br />**>>** | Bitwise left shift  按位左移<br />Bitwise right shift  按位右移 | 从左到右 |
| 6 | **&** | Bitwise AND  按位与 | 从左到右 |
| 7 | **^** | Bitwise XOR  按位异或 | 从左到右 |
| 8 | **&#124;** | Bitwise OR  按位或 | 从左到右 |
| 9 | **<**<br />**<=**<br />**>**<br />**>=** | Less than  小于<br />Less than or equal to  小于等于<br />Greater than  大于<br />Greater than or equal to  大于等于 | 从左到右 |
| 10 | **==**<br />**!=**<br />**contains**<br />**icontains**<br />**startswith**<br />**istartswith**<br />**endswith**<br />**iendswith**<br />**matches** | Equal to  等于<br />Not equal to  不等于<br />String contains substring  包含<br />Like contains but case-insensitive  包含不区分大小写<br />String starts with substring  以开始字符串<br />Like startswith but case-insensitive 以开始字符串不区分大小写<br />String ends with substring  以结尾字符串<br />Like endswith but case-insensitive  以结尾字符串区分大小写<br />String matches regular expression  正则表达式 | 从左到右 |
| 11 | **not** | Logical NOT  逻辑非 | 从右到左 |
| 12 | **and** | Logical AND  逻辑与 | 从左到右 |
| 13 | **or** | Logical OR  逻辑或 | 从左到右 |

### 字符串计数
```bash
rule CountExample
{
    strings:
        $a = "dummy1"
        $b = "dummy2"
    condition:
        #a == 6 and #b > 10
}
```
还能指定范围计数：
```bash
#a in (filesize-500..filesize) == 2
```
### 字符串偏移或者虚拟地址
```bash
rule AtExample
{
    strings:
        $a = "dummy1"
        $b = "dummy2"
    condition:
        $a at 100 and $b at 200
}

rule InExample
{
    strings:
        $a = "dummy1"
        $b = "dummy2"
    condition:
        $a in (0..100) and $b in (100..filesize)
}
```
取字符串第i次出现的偏移，**注意只能用 == 运算符**
```bash
rule AtExample
{
    strings:
        $a = "dummy1"
        $b = "dummy2"
    condition:
        @a[3] == 100 
}
```
### 匹配长度
这个主要用于正则表达式，比如 `/fo*/`可以匹配字符串 'fo', 'foo','fooo'等，但是具体要选择哪一个呢？这里可以用!来去匹配长度：
```bash
rule MatchLength{
	strings:
    $a = /fo*/
	condition:
  	!a[1] == 4 // 匹配 fooo
}
```
### 访问指定位置的数据
使用以下函数从给定偏移量的文件中读取数据：
```bash
int8(<offset or virtual address>)
int16(<offset or virtual address>)
int32(<offset or virtual address>)
uint8(<offset or virtual address>)
uint16(<offset or virtual address>)
uint32(<offset or virtual address>)
int8be(<offset or virtual address>)
int16be(<offset or virtual address>)
int32be(<offset or virtual address>)
uint8be(<offset or virtual address>)
uint16be(<offset or virtual address>)
uint32be(<offset or virtual address>)
```
```bash
rule IsPE
{
    condition:
        // MZ signature at offset 0 and ...
        uint16(0) == 0x5A4D and
        // ... PE signature at offset stored in MZ header at 0x3C
        uint32(uint32(0x3C)) == 0x00004550
}
```
### 字符串集合
```bash
2 of ($a,$b,$c)
all of them       // all strings in the rule
any of them       // any string in the rule
all of ($a*)      // all strings whose identifier starts by $a
any of ($a,$b,$c) // any of $a, $b or $c
1 of ($*)         // same that "any of them"
none of ($b*)     // zero of the set of strings that start with "$b"


all of ($a*) in (filesize-500..filesize)
any of ($a*, $b*) in (1000..2000)
```
### for循环
#### 对多个字符串使用相同的条件
```bash
for expression of string_set : ( boolean_expression )

在集合string_set中，expression必须满足( boolean_expression )

例如：
for any of ($a,$b,$c) : ( $ at pe.entry_point )
布尔表达式中的 $ 符号不与任何特定字符串相关联，它将是 $a，然后是 $b，最后是 $c
```
其实这里可以发现any of 是一种简写:
```bash
any of ($a,$b,$c)
等价于
for any of ($a,$b,$c) : ( $ )
```
在 expression 中也可以使用 @, # ,! 等运算符：
```bash
for all of them : ( # > 3 )
for all of ($a*) : ( @ > @b )
```
#### 迭代字符串
可以使用以下语法访问给定字符串出现在文件或进程地址空间中的偏移量或虚拟地址：@a[i]，其中 i 是一个索引，指示出现了你所指的字符串 $a 。（@a[1]、@a[2]、…）
```bash
rule Occurrences
{
    strings:
        $a = "dummy1"
        $b = "dummy2"
    condition:
        for all i in (1,2,3) : ( @a[i] + 10 == @b[i] )
}
```
以上条件也可以写成：
```bash
for all i in (1..3) : ( @a[i] + 10 == @b[i]
```
另一个规则：
```bash
for all i in (1..#a) : ( @a[i] < 100 )   //#a 代表 $a 出现的次数
```
还有可以限定满足条件的迭代次数：
```bash
for 2 i in (1..#a) : ( @a[i] < 100 )
```
#### 迭代器
在 YARA 4.0 中，for..of运算符得到了改进，现在它不仅可以用于迭代整数枚举和范围（例如：1,2,3,4 和 1..4），还可以用于任何类型的可迭代数据类型，例如YARA 模块定义的数组和字典。例如，以下表达式在 YARA 4.0 中有效：
```bash
for any section in pe.sections : ( section.name == ".text"）

// 等价于
for any i in (0..pe.number_of_sections-1) : ( pe.sections[i].name == ".text" )

```
在迭代字典时，您必须提供两个变量名，它们将保存字典中每个条目的键和值，例如：
```bash
for any k,v in some_dict : ( k == "foo" and v == "bar" )
```
### 外部变量
外部变量允许您定义依赖于外部提供的值的规则。
```bash
rule ExternalVariableExample1
{
    condition:
        ext_var == 10
}
```
在这种情况下ext_var是一个外部变量，其值在运行时分配。外部变量可以是以下类型：整数、字符串或布尔值；它们的类型取决于分配给它们的值。整数变量可以替代条件中的任何整数常量，布尔变量可以占据布尔表达式的位置。例如：
```bash
rule ExternalVariableExample2
{
    condition:
        bool_ext_var or filesize < int_ext_var
}
```
string类型的外部变量可以与以下运算符一起使用：contains、startswith、endswith及其不区分大小写的对应运算符：icontains、istartswith和iendswith`。它们还可以与“matches运算符一起使用，如果字符串与给定的正则表达式匹配，则返回true。
```bash
rule ContainsExample
{
    condition:
        string_ext_var contains "text"
}
rule CaseInsensitiveContainsExample
{
    condition:
        string_ext_var icontains "text"
}
rule StartsWithExample
{
    condition:
        string_ext_var startswith "prefix"
}
rule EndsWithExample
{
    condition:
        string_ext_var endswith "suffix"
}
rule MatchesExample
{
    condition:
        string_ext_var matches /[a-z]+/is
}
```
## 偏门模块

1. Hash模块

[https://yara.readthedocs.io/en/latest/modules/hash.html](https://yara.readthedocs.io/en/latest/modules/hash.html)

2. Math模块

[https://yara.readthedocs.io/en/latest/modules/math.html](https://yara.readthedocs.io/en/latest/modules/math.html)

3. Dotnet 模块

[https://yara.readthedocs.io/en/latest/modules/dotnet.html](https://yara.readthedocs.io/en/latest/modules/dotnet.html)
## 一些进阶用法
### 打分
利用yara的math模块进行打分
```bash
math.to_number(SubRule1) * 60 + math.to_number(SubRule2) * 20 + math.to_number(SubRule3) * 70 > 80
```
### 判断.text section的墒值在7.4与7.6之间
```bash
for any section in pe.sections : ( 
section.name == ".text" 
and  math.in_range(math.entropy(section.raw_data_offset,section.raw_data_size),7.4,7.6))
```
### 导入表有且仅有`VirtualAlloc` 和 `CreateRemoteThread` 以及 ` _WriteProcessMemory_`
```bash
pe.imports("kernel32.dll","VirtualAlloc") 
and 
pe.imports("kernel32.dll","CreateRemoteThread") 
and 
pe.imports("kernel32.dll","WriteProcessMemory") 
and 
pe.imports("kernel32.dll")  == 3
```
### 有某个图标，并且无签名(不够灵活，没法设定一个hash列表)
```bash
import "hash"
import "pe"

rule iconForge{

   condition:
    	for any res in pe.resources: (
          res.type == pe.RESOURCE_TYPE_ICON
            hash.md5( res.offset,res.length) == "xxxxx"
            ) 
        and 
            pe.number_of_signatures == 0
}
```
### 匹配PDB路径
```bash
pe.pdb_path icontains "shellcode" or pe.pdb icontains "qianxin"
```
### 匹配特征在具体的节区
```
import "pe"
import "console"

rule test{

    strings:
        $a = {55 8B EC F6 45 08 01 56 8B F1 C7 06 94 1F 43 00}

    condition:
        $a in (
            pe.sections[ pe.section_index(".text") ].raw_data_offset..pe.sections[ pe.section_index(".text") ].raw_data_offset+pe.sections[ pe.section_index(".text") ].raw_data_size
        )
}
```

