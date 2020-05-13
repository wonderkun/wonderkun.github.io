---
title: minHook源码阅读分析
url: 763.html
id: 763
categories:
  - code
date: 2019-03-19 10:41:34
tags:
  - c
  - binary
  - windows
---







## minhook源码阅读分析

minhook是一个inline Hook的库，同时支持x32和x64系统，并且是开源的，地址在这里[https://www.codeproject.com/Articles/44326/MinHook-The-Minimalistic-x-x-API-Hooking-Libra](https://www.codeproject.com/Articles/44326/MinHook-The-Minimalistic-x-x-API-Hooking-Libra)。下面就简单的分析一下它的工作过程。

<!-- more-->
### 0x1 调用实例

首先看一下官网上给出的c的调用的例子：

```c
#include <Windows.h>
#include "./include/MinHook.h"


typedef int (WINAPI *MESSAGEBOXW)(HWND, LPCWSTR, LPCWSTR, UINT);

// Pointer for calling original MessageBoxW.
MESSAGEBOXW fpMessageBoxW = NULL;

// Detour function which overrides MessageBoxW.
int WINAPI DetourMessageBoxW(HWND hWnd, LPCWSTR lpText, LPCWSTR lpCaption, UINT uType)
{
 	return fpMessageBoxW(hWnd, L"Hooked!", lpCaption, uType);
}

int main()
{
	// Initialize MinHook.
	if (MH_Initialize() != MH_OK)
	{
		return 1;
	}
	// Create a hook for MessageBoxW, in disabled state.
	if (MH_CreateHook(&MessageBoxW, &DetourMessageBoxW,
		reinterpret_cast<LPVOID*>(&fpMessageBoxW)) != MH_OK)
	{
		return 1;
	}
	// or you can use the new helper function like this.
	//if (MH_CreateHookApiEx(
	//    L"user32", "MessageBoxW", &DetourMessageBoxW, &fpMessageBoxW) != MH_OK)
	//{
	//    return 1;
	//}
	// Enable the hook for MessageBoxW.
	if (MH_EnableHook(&MessageBoxW) != MH_OK)
	{
		return 1;
	}

	// Expected to tell "Hooked!".
	MessageBoxW(NULL, L"Not hooked...", L"MinHook Sample", MB_OK);

	// Disable the hook for MessageBoxW.
	if (MH_DisableHook(&MessageBoxW) != MH_OK)
	{
		return 1;
	}
	// Expected to tell "Not hooked...".
	MessageBoxW(NULL, L"Not hooked...", L"MinHook Sample", MB_OK);

	// Uninitialize MinHook.
	if (MH_Uninitialize() != MH_OK)
	{
		return 1;
	}
	return 0;
}
```

### 0x2 初始化钩子的过程

根据这个调用流程跟踪一下源代码，首先看`MH_Initialize`函数，此函数就干了一件事情，初始化了一个大小自增长的堆，并将堆的句柄存储在全局变量`g_hHeap`中。

```c
 g_hHeap = HeapCreate(0, 0, 0);
```

接下来就是创建hook的过程了，这里需要注意几个结构体：

```c
struct
{
    PHOOK_ENTRY pItems;     // Data heap
    UINT        capacity;   // Size of allocated data heap, items
    UINT        size;       // Actual number of data items
} g_hooks;
```

g_hooks是一个全局变量，此结构体存储了当前创建的所有钩子，每个钩子的信息都存在了`pItems`这个指针里。`PHOOK_ENTRY`结构体的定义如下：

```c
typedef struct _HOOK_ENTRY
{
    LPVOID pTarget;             // Address of the target function.
    LPVOID pDetour;             // Address of the detour or relay function.
    LPVOID pTrampoline;         // Address of the trampoline function.
    UINT8  backup[8];           // Original prologue of the target function.

    UINT8  patchAbove  : 1;     // Uses the hot patch area.
    UINT8  isEnabled   : 1;     // Enabled.
    UINT8  queueEnable : 1;     // Queued for enabling/disabling when != isEnabled.

    UINT   nIP : 4;             // Count of the instruction boundaries.
    UINT8  oldIPs[8];           // Instruction boundaries of the target function.
    UINT8  newIPs[8];           // Instruction boundaries of the trampoline function.
} HOOK_ENTRY, *PHOOK_ENTRY;
```

`pTarget`存储了被hook的函数的地址，`pDetour`是你写的假的函数的地址，`pTrampoline`是一个中间的跳转函数，一会再细说。`backup[8]`是对被`Hook`函数的前五字节的备份，`nIp`表示被Hook函数的前五个字节可以是几条指令，`oldIPs`,`newIPs`分别存储了被Hook函数前五字节每条指令的偏移和中间跳转函数对应的每条指令的偏移，关于这个一会再细说。

接下来调用`MH_CreateHook`函数，在这个函数里面，首先调用`FindHookEntry`查找`g_hooks`中是否已经存放了被hook的目标，如果不存在，就进入创建一个`_HOOK_ENTRY`的过程。

```c
static UINT FindHookEntry(LPVOID pTarget)
{
    UINT i;
    for (i = 0; i < g_hooks.size; ++i)
    {
        if ((ULONG_PTR)pTarget == (ULONG_PTR)g_hooks.pItems[i].pTarget)
            return i;
    }
    return INVALID_HOOK_POS;
}
```

但是在初始化`_HOOK_ENTRY`之前先要初始化一个`_TRAMPOLINE`，这部分是minHook的关键,结构体定义如下：

```c
typedef struct _TRAMPOLINE
{
    LPVOID pTarget;         // [In] Address of the target function.
    LPVOID pDetour;         // [In] Address of the detour function.
    LPVOID pTrampoline;     // [In] Buffer address for the trampoline and relay function.

#if defined(_M_X64) || defined(__x86_64__)
    LPVOID pRelay;          // [Out] Address of the relay function.
#endif
    BOOL   patchAbove;      // [Out] Should use the hot patch area?
    UINT   nIP;             // [Out] Number of the instruction boundaries.
    UINT8  oldIPs[8];       // [Out] Instruction boundaries of the target function.
    UINT8  newIPs[8];       // [Out] Instruction boundaries of the trampoline function.
} TRAMPOLINE, *PTRAMPOLINE;
```

这个结构体其他部分的定义跟`_HOOK_ENTRY`结构体一毛一样，但是这里有一个初始化`pTrampoline`指针的函数`AllocateBuffer`，此函数中核心逻辑在`GetMemoryBlock`中，关键代码如下：

```c
        while ((ULONG_PTR)pAlloc >= minAddr)
        {
            pAlloc = FindPrevFreeRegion(pAlloc, (LPVOID)minAddr, si.dwAllocationGranularity); // 按照虚拟内存分配粒度找一块free的内存空间
            if (pAlloc == NULL)
                break;

            pBlock = (PMEMORY_BLOCK)VirtualAlloc(
                pAlloc, MEMORY_BLOCK_SIZE, MEM_COMMIT | MEM_RESERVE, PAGE_EXECUTE_READWRITE);
            if (pBlock != NULL)
                break;
        }
    }

    // Alloc a new block below if not found.
    if (pBlock == NULL)
    {
        LPVOID pAlloc = pOrigin;
        while ((ULONG_PTR)pAlloc <= maxAddr)
        {
            pAlloc = FindNextFreeRegion(pAlloc, (LPVOID)maxAddr, si.dwAllocationGranularity);
            if (pAlloc == NULL)
                break;

            pBlock = (PMEMORY_BLOCK)VirtualAlloc(
                pAlloc, MEMORY_BLOCK_SIZE, MEM_COMMIT | MEM_RESERVE, PAGE_EXECUTE_READWRITE);
            if (pBlock != NULL)
                break;
        }
    }
```

大意是在被Hook函数的左右512M空间找找到处于空闲状态的内存空间，并返回其地址。接下来就是初始化`TRAMPOLINE`结构体的函数`CreateTrampolineFunction`，此函数比较复杂，在一个大的do-while循环中主要干了两件事情

1. 将被Hook的函数的前五个字节放置在`pTrampoline`指向的buffer中，创建中间函数。也就是我们自己定义函数指针`fpMessageBoxW`的函数体。但是在拷贝的时候，比较麻烦的一点就是，需要进行指令分析，因为`call`，`jmp`,`jcc`这类指令的操作数需要做相对地址转换（都是相对于eip的）。

```c
 do
    {
        HDE       hs;
        UINT      copySize;
        LPVOID    pCopySrc;
        ULONG_PTR pOldInst = (ULONG_PTR)ct->pTarget     + oldPos;
        ULONG_PTR pNewInst = (ULONG_PTR)ct->pTrampoline + newPos;

        copySize = HDE_DISASM((LPVOID)pOldInst, &hs); //对目标代码进行反汇编
        if (hs.flags & F_ERROR)
            return FALSE;

        pCopySrc = (LPVOID)pOldInst;
        if (oldPos >= sizeof(JMP_REL))
        {
            // The trampoline function is long enough.
            // Complete the function with the jump to the target function.
#if defined(_M_X64) || defined(__x86_64__)
            jmp.address = pOldInst; // x64模式写， 0xFF25 disp64进行jmp
#else
            jmp.operand = (UINT32)(pOldInst - (pNewInst + sizeof(jmp)));
#endif
            pCopySrc = &jmp;
            copySize = sizeof(jmp);

            finished = TRUE;
        }
#if defined(_M_X64) || defined(__x86_64__)
        else if ((hs.modrm & 0xC7) == 0x05) // 在x64模式下添加的 [rip+disp32] 的间接寻址模式
        {
            // Instructions using RIP relative addressing. (ModR/M = 00???101B)
			// 使用RIP相对指令跳转
            // Modify the RIP relative address.
            PUINT32 pRelAddr;

            // Avoid using memcpy to reduce the footprint.
#ifndef _MSC_VER
            memcpy(instBuf, (LPBYTE)pOldInst, copySize);
#else
            __movsb(instBuf, (LPBYTE)pOldInst, copySize);
#endif
            pCopySrc = instBuf;
            // Relative address is stored at (instruction length - immediate value length - 4).
            pRelAddr = (PUINT32)(instBuf + hs.len - ((hs.flags & 0x3C) >> 2) - 4);
            *pRelAddr
                = (UINT32)((pOldInst + hs.len + (INT32)hs.disp.disp32) - (pNewInst + hs.len)); 
			
			// 写入相对跳转地址
            // Complete the function if JMP (FF /4).
            if (hs.opcode == 0xFF && hs.modrm_reg == 4)
                finished = TRUE;
        }
#endif
        else if (hs.opcode == 0xE8) // 如果是call指令
        {
            // Direct relative CALL
            ULONG_PTR dest = pOldInst + hs.len + (INT32)hs.imm.imm32; //call 指令的目的跳转地址
#if defined(_M_X64) || defined(__x86_64__)
            call.address = dest;
#else
            call.operand = (UINT32)(dest - (pNewInst + sizeof(call))); // 修改call指令的目的跳转地址
#endif
            pCopySrc = &call;
            copySize = sizeof(call);
        }
        else if ((hs.opcode & 0xFD) == 0xE9) // 如果是jmp
        {
            // Direct relative JMP (EB or E9)
            ULONG_PTR dest = pOldInst + hs.len;

            if (hs.opcode == 0xEB) // isShort jmp
                dest += (INT8)hs.imm.imm8;
            else
                dest += (INT32)hs.imm.imm32;

            // Simply copy an internal jump.
            if ((ULONG_PTR)ct->pTarget <= dest
                && dest < ((ULONG_PTR)ct->pTarget + sizeof(JMP_REL)))
            {
                if (jmpDest < dest)
                    jmpDest = dest;
            }
            else
            {
#if defined(_M_X64) || defined(__x86_64__)
                jmp.address = dest;
#else
                jmp.operand = (UINT32)(dest - (pNewInst + sizeof(jmp)));
#endif
                pCopySrc = &jmp;
                copySize = sizeof(jmp);

                // Exit the function If it is not in the branch
                finished = (pOldInst >= jmpDest);
            }
        }
        else if ((hs.opcode & 0xF0) == 0x70
            || (hs.opcode & 0xFC) == 0xE0
            || (hs.opcode2 & 0xF0) == 0x80)
        {
            // Direct relative Jcc
            ULONG_PTR dest = pOldInst + hs.len;

            if ((hs.opcode & 0xF0) == 0x70      // Jcc
                || (hs.opcode & 0xFC) == 0xE0)  // LOOPNZ/LOOPZ/LOOP/JECXZ
                dest += (INT8)hs.imm.imm8;
            else
                dest += (INT32)hs.imm.imm32;

            // Simply copy an internal jump.
            if ((ULONG_PTR)ct->pTarget <= dest
                && dest < ((ULONG_PTR)ct->pTarget + sizeof(JMP_REL)))
            {
                if (jmpDest < dest)
                    jmpDest = dest;
            }
            else if ((hs.opcode & 0xFC) == 0xE0)
            {
                // LOOPNZ/LOOPZ/LOOP/JCXZ/JECXZ to the outside are not supported.
                return FALSE;
            }
            else
            {
                UINT8 cond = ((hs.opcode != 0x0F ? hs.opcode : hs.opcode2) & 0x0F);
#if defined(_M_X64) || defined(__x86_64__)
                // Invert the condition in x64 mode to simplify the conditional jump logic.
                jcc.opcode  = 0x71 ^ cond;
                jcc.address = dest;
#else
                jcc.opcode1 = 0x80 | cond;
                jcc.operand = (UINT32)(dest - (pNewInst + sizeof(jcc)));
#endif
                pCopySrc = &jcc;
                copySize = sizeof(jcc);
            }
        }
        else if ((hs.opcode & 0xFE) == 0xC2)
        {
            // RET (C2 or C3)

            // Complete the function if not in a branch.
            finished = (pOldInst >= jmpDest);
        }

        // Can't alter the instruction length in a branch.
        if (pOldInst < jmpDest && copySize != hs.len)
            return FALSE;

        // Trampoline function is too large.
        if ((newPos + copySize) > TRAMPOLINE_MAX_SIZE)
            return FALSE;

        // Trampoline function has too many instructions.
        if (ct->nIP >= ARRAYSIZE(ct->oldIPs))
            return FALSE;

        ct->oldIPs[ct->nIP] = oldPos;
        ct->newIPs[ct->nIP] = newPos;
        ct->nIP++;

        // Avoid using memcpy to reduce the footprint.
#ifndef _MSC_VER
        memcpy((LPBYTE)ct->pTrampoline + newPos, pCopySrc, copySize);
#else
        __movsb((LPBYTE)ct->pTrampoline + newPos,(LPBYTE)pCopySrc, copySize);
#endif
        newPos += copySize;
        oldPos += hs.len;
    }
    while (!finished);
```

2. 接下来就是还需要在`pTrampoline`的末尾写上一个长跳转指令，跳转到被Hook函数的指定位置开始执行(注意不是被Hook函数的开始，因为被Hook函数的开始部分已经在pTrampoline指向的buffer的前五个字节中已经被执行了)。（其实这部分代码是在do-while循环中完成的）

```c
    JMP_ABS jmp = {
        0xFF, 0x25, 0x00000000, // FF25 00000000: JMP [RIP+6]
        0x0000000000000000ULL   // Absolute destination address
    }; 
    // 0xff25的一个长跳转
    
if (oldPos >= sizeof(JMP_REL))
        {
            // The trampoline function is long enough.
            // Complete the function with the jump to the target function.
#if defined(_M_X64) || defined(__x86_64__)
            jmp.address = pOldInst; // x64模式写， 0xFF25 disp64进行jmp
#else
            jmp.operand = (UINT32)(pOldInst - (pNewInst + sizeof(jmp)));
#endif
            pCopySrc = &jmp;
            copySize = sizeof(jmp);
            finished = TRUE;
}
```

### 0x3 安装钩子

钩子函数已经初始化成功了，接下来就需要开始安装了，调用`MH_EnableHook`函数。核心操作在函数`EnableHookLL`中：

```c
static MH_STATUS EnableHookLL(UINT pos, BOOL enable)
{
    PHOOK_ENTRY pHook = &g_hooks.pItems[pos];
    DWORD  oldProtect;
    SIZE_T patchSize    = sizeof(JMP_REL);
    LPBYTE pPatchTarget = (LPBYTE)pHook->pTarget;

    if (pHook->patchAbove)
    {
        pPatchTarget -= sizeof(JMP_REL);
        patchSize    += sizeof(JMP_REL_SHORT);
    }

    if (!VirtualProtect(pPatchTarget, patchSize, PAGE_EXECUTE_READWRITE, &oldProtect))
        return MH_ERROR_MEMORY_PROTECT;

    if (enable)
    {
        PJMP_REL pJmp = (PJMP_REL)pPatchTarget;
        pJmp->opcode = 0xE9;
        pJmp->operand = (UINT32)((LPBYTE)pHook->pDetour - (pPatchTarget + sizeof(JMP_REL)));

        if (pHook->patchAbove)
        {
            PJMP_REL_SHORT pShortJmp = (PJMP_REL_SHORT)pHook->pTarget;
            pShortJmp->opcode = 0xEB;
            pShortJmp->operand = (UINT8)(0 - (sizeof(JMP_REL_SHORT) + sizeof(JMP_REL)));
        }
    }
    else
    {
        if (pHook->patchAbove)
            memcpy(pPatchTarget, pHook->backup, sizeof(JMP_REL) + sizeof(JMP_REL_SHORT));
        else
            memcpy(pPatchTarget, pHook->backup, sizeof(JMP_REL));
    }

    VirtualProtect(pPatchTarget, patchSize, oldProtect, &oldProtect);

    // Just-in-case measure.
    FlushInstructionCache(GetCurrentProcess(), pPatchTarget, patchSize);

    pHook->isEnabled   = enable;
    pHook->queueEnable = enable;

    return MH_OK;
}
```

核心代码就下面三行：

```c
        PJMP_REL pJmp = (PJMP_REL)pPatchTarget;
        pJmp->opcode = 0xE9;
        pJmp->operand = (UINT32)((LPBYTE)pHook->pDetour - (pPatchTarget + sizeof(JMP_REL)));

```

在被Hook的函数的前五个字节写上`0xe9+跳转地址`,跳转到我们创建假的函数地址的位置。

但是再执行`EnableHookLL`还要执行一个操作，就是先暂停本进程出去本线程之外的所有线程,调用`freeze`函数实现操作：

```c
static VOID Freeze(PFROZEN_THREADS pThreads, UINT pos, UINT action)
{
    pThreads->pItems   = NULL;
    pThreads->capacity = 0;
    pThreads->size     = 0;
    EnumerateThreads(pThreads);

    if (pThreads->pItems != NULL)
    {
        UINT i;
        for (i = 0; i < pThreads->size; ++i)
        {
            HANDLE hThread = OpenThread(THREAD_ACCESS, FALSE, pThreads->pItems[i]);
            if (hThread != NULL)
            {
                SuspendThread(hThread);
                ProcessThreadIPs(hThread, pos, action);
                CloseHandle(hThread);
            }
        }
    }
}
```

跟踪一下`ProcessThreadIPs`函数的操作：

```c
static void ProcessThreadIPs(HANDLE hThread, UINT pos, UINT action)
{
    // If the thread suspended in the overwritten area,
    // move IP to the proper address.

    CONTEXT c;
#if defined(_M_X64) || defined(__x86_64__)
    DWORD64 *pIP = &c.Rip;
#else
    DWORD   *pIP = &c.Eip;
#endif
    UINT count;

    c.ContextFlags = CONTEXT_CONTROL;
    if (!GetThreadContext(hThread, &c))
        return;

    if (pos == ALL_HOOKS_POS)
    {
        pos = 0;
        count = g_hooks.size;
    }
    else
    {
        count = pos + 1;
    }

    for (; pos < count; ++pos)
    {
        PHOOK_ENTRY pHook = &g_hooks.pItems[pos];
        BOOL        enable;
        DWORD_PTR   ip;

        switch (action)
        {
        case ACTION_DISABLE:
            enable = FALSE;
            break;

        case ACTION_ENABLE:
            enable = TRUE;
            break;

        default: // ACTION_APPLY_QUEUED
            enable = pHook->queueEnable;
            break;
        }
        if (pHook->isEnabled == enable)
            continue;

        if (enable)
            ip = FindNewIP(pHook, *pIP);
        else
            ip = FindOldIP(pHook, *pIP);
        if (ip != 0)
        {
            *pIP = ip;
            SetThreadContext(hThread, &c);
        }
    }
}
```

emm，这里直接修改了其他线程的Eip，操作有点秀啊。。。。。

接下来就是恢复线程的操作了,不在细说。

### 0x4 Hook之后的调用过程

就以实例代码中的Hook`MessageBoxW`的调用过程为例，以下图展示：

```c
                                                              DetourMessageBoxW
                                          ^------------>+------------------ --- --+
        +--------------------+            |             |    push ebp             |
        |  // user code      |            |             |    mov ebp,esp          |
      +-+   call MessageBoxW |            |             |    ......               |
      | +--------------------+            |             |    ;your code           |
      |                                   |             |    .....                |
      |                                   |             |    call fpMessage oxW   +--+
      |                                   |             +------------------ --- --+  |
      |                                   |                                          |
      v        origin MessageBoxW         |                   fpMessageBoxW          |
+-----+------------------------------+    |            +--------------------------+<-+
|    0xe9 address_D tourMessageBoxW  +----+            |                          |
|          .......other code......   |                 |    ; origin 5 bytes      |
+------------------------------------+<--^|            |    ; of MesageBoxW       |
                                          |            |                          |
                                          +------------|    jmp MessageBoxW+5     |
                                                       +--------------------------+
```

### 0x5 需要改进的地方

因为想做不被执行程序感知的Hook，这里明显的问题是，被Hook的系统API的第一条指令都是`0xe9...`很容易被发现。另外一个问题是这里没有对栈做处理，导致也可以通过`unblance stack`技巧轻易发现API被Hook过。

所以接下来的工作就是修改这个两个地方。