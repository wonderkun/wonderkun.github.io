---
title: php_apache2_操作系统之间的一些黑魔法
url: 626.html
id: 626
categories:
  - hack_ctf
date: 2017-08-22 09:37:22
tags:
  - php
  - ctf
---

### 0x00 前言

做了一个CTF题目，遇到了一些有趣的东西，所以写了这篇文章记录了一下。 但是我却不明白造成这个问题的原因在哪里，所以不知道给文章起什么标题，就姑且叫这个非常宽泛的名字吧。

<!--more-->
### 0x01 CTF题目原型

在遇到的题目中，最后一步是getshell，大概可以简化为以下代码：

```php
<?php 

// 测试环境 linux + apache2  + php 
// 没有开rewrite ，所以写 .htaccess 没用
// 没有用cgi ，所以写 .user.ini 也没有 
// 要求 getshell 
// 修改配置文件，crontab之类的都是没权限的。 
  
$content = $_POST['content']; 
$filename = $_POST['filename']; 
$filename = "backup/".$filename;

if(preg_match('/.+\.ph(p[3457]?|t|tml)$/i', $filename)){
   die("Bad file extension");
}else{
    $f = fopen($filename, 'w');
    fwrite($f, $content);
    fclose($f);
}
?>
```

我把这个问题发到phithon的代码审计圈里征求答案，师傅们的答案都在理，但是却不是我想要的那个答案，下面就来一一的分析以下。

### 0x02 一些不完美的做法  

我最开始的想法跟大多数师傅的想法一样

```php
因为正则表达式中的点（.）不会匹配换行符（0x0a），所以可以在扩展名前面插入一个换行符，构造的文件名为233%0a.php，
这样就可以绕过正则，而且还是合法的文件名(linux允许这样的文件名存在，而windows是不允许的)。
```

在我本地测试一下，一切都是那么的美好，轻松getshell:

![http://pic.wonderkun.cc/uploads/2017/08/1.png](http://pic.wonderkun.cc/uploads/2017/08/1.png)

我本地的环境是 mac默认安装的apache+php。

当我在ubuntu上测试的时候傻眼了，

![http://pic.wonderkun.cc/uploads/2017/08/2.png](http://pic.wonderkun.cc/uploads/2017/08/2.png)

ubuntu上的apache并没有把这个文件当做php文件来解析。这到底是为什么呢？这里先留个坑，一会仔细讲。

这种方法不行之后，很快就有人想到了，会不是是apache2的文件解析漏洞呢？然后我就在ubuntu上测试了一下

![http://pic.wonderkun.cc/uploads/2017/08/3.png](http://pic.wonderkun.cc/uploads/2017/08/3.png)

apache的版本是2.4.7，并不存在解析漏洞。

然后我又在本地测试了一下。

![http://pic.wonderkun.cc/uploads/2017/08/4.png](http://pic.wonderkun.cc/uploads/2017/08/4.png)

**What fuck!!!**  我的本地竟然存在php文件解析漏洞，这笔记本是假的吧，装的apache也是假的吧。版本都是2.4.25了怎么还会存在文件解析漏洞呢？ 

**在我的印象中apache的文件解析漏洞是在2.3.x以下版本才会存在的啊？这到底是为什么？**

之后朋友又给我发来了一张图片，我当时就炸毛了，他的版本是2.4.18，并不存在漏洞。我觉得我这apache可能是假的。

![http://pic.wonderkun.cc/uploads/2017/08/5.png](http://pic.wonderkun.cc/uploads/2017/08/5.png)

经过冷静的思考，我得出结论：**Apache文件解析漏洞，可能与apache的版本并没有关系，而是与apache解析php的配置相关。**

### 0x03 再提apache的文件解析漏洞 

apache的文件解析漏洞正火的时候，我还没上大学呢，所以也没有真正的去分析产生这种漏洞的原因，一直模糊的认为这是apache本身的问题：Apache 解析文件的规则是从右到左开始判断解析,如果后缀名为不可识别文件解析,就再往左判断。 

所以我以为apache后来已经修复了这个bug了，不会再出现文件解析漏洞了。

经过比对，我发现我本地mac上的php5.conf是这样写的：

```Bash
➜  ~ cat /private/etc/apache2/other/php5.conf
<IfModule php5_module>
	AddType application/x-httpd-php .php
	AddType application/x-httpd-php-source .php
	<IfModule dir_module>
		DirectoryIndex index.html index.php
	</IfModule>
</IfModule>
```

而ubuntu上的php5.conf是这样的：

```php
<FilesMatch ".+\.ph(p[345]?|t|tml)$">
    SetHandler application/x-httpd-php
</FilesMatch>
<FilesMatch ".+\.phps$">
    SetHandler application/x-httpd-php-source
    Order Deny,Allow
    Deny from all
</FilesMatch>
# Deny access to files without filename (e.g. '.php')
<FilesMatch "^\.ph(p[345]?|t|tml|ps)$">
    Order Deny,Allow
    Deny from all
</FilesMatch>
```

看ubuntu的配置

```Bash
<FilesMatch ".+\.ph(p[345]?|t|tml)$">
```

这个正则和题目中的正则是一样的，很容易明白，当文件名和这个正则匹配上之后，就交给mod_php处理。

这就解释了为什么`233%0a.php`不会被解析的。

还有下面这段,也禁止解析以`.`开头的php文件执行的：

```bash
<FilesMatch "^\.ph(p[345]?|t|tml|ps)$">
    Order Deny,Allow
    Deny from all
</FilesMatch>
```

所以我觉得产生文件解析漏洞的根源是这句话：

```Bash
AddType application/x-httpd-php .php
```

为了验证我的想法，我把这句修改为下面这样，然后重启apache

```Bash
AddType application/x-httpd-php .phtml
```

![http://pic.wonderkun.cc/uploads/2017/08/6.png](http://pic.wonderkun.cc/uploads/2017/08/6.png)

在这种情况下.php后缀已经不再被解析了，而被解析的是.phtml和.phtml.xxxxxxx

所以这样的错误配置才是引起apache 解析漏洞的关键。

最后感悟：无论是apache文件解析漏洞还是nginx文件解析漏洞，本来都不应该是apache，nginx 或者php的锅，它们有的只是功能，而且开发这些功能也是为了方便使用者，而恰好这些功能恰好被一个管理员用在了不恰当的时候，所以才造成了漏洞。

### 0x04 回到题目中

 经过测试发现一个可以再windows和linux上都行得通的方法：

```Bash
filename=1.php/.&content=<?php phpinfo();?>
```

在操作系统中，都是禁止使用`/`作为文件名的，但是不知道为什么后面加一个`.`就可以成功的写入1.php了。

而且奇怪的是无论是在windows上还是linux上，每次都只可以创建新文件，不能覆盖老文件。要想知道php里面是怎么处理这个路径的，就需要看php源代码了，但是我目前并没有看明白里面的处理逻辑，等我抽个时间分析完了，再做补充吧。

### 0x5 问题成因分析 

经过了一段时间的分析，我终于找到了php在文件路径处理上的问题所在。

由于我对php源码不太熟悉，分析过程踩了一些坑，下面记录一下分析过程。

我用的是`php5.6.8`版本记进行分析的，源码可以直接从`https://github.com/php/php-src`下载，然后checkout出`php5.6.8`版本即可。对于编译过程不再详说，为了方便分析，建议修改`MakeFile：58`行为：

```C
CFLAGS_CLEAN = -g -O0 -fvisibility=hidden  //去掉优化编译选项
```

现在php源码全局搜索找出`file_put_contents`函数的实现入口，在`ext/standard/file.c`的579行，发现了下面代码：

```c
PHP_FUNCTION(file_put_contents)  
{
	.....
```

这就是`file_put_contents`函数的入口，在这里下一个断点，然后执行。

```bash
➜  cli git:(php-5.6.8) ✗ gdb -q ./php
Reading symbols from ./php...done.
gdb-peda$ b  ext/standard/file.c:579
Breakpoint 1 at 0x10012b3ce: file ext/standard/file.c, line 579.
gdb-peda$ r ~/Desktop/2.php
Starting program: /Users/wonderkun/script/php-src/sapi/cli/php ~/Desktop/2.php
```

```php
#2.php 的内容如下
<?php
file_put_contents("./test.php/.","<?=phpinfo()=>");
```

跟踪到file.c:616行

```c
stream = php_stream_open_wrapper_ex(filename, mode, ((flags & PHP_FILE_USE_INCLUDE_PATH) ? USE_PATH : 0) | REPORT_ERRORS, NULL, context);
//调用php_stream_open_wrapper_ex进行了写文件处理
```

单步跟进次函数：

```Bash
gdb-peda$ s
_php_stream_open_wrapper_ex (path=0x1012181d8 "./test.php/.", mode=0x7fff5fbfdf2d "wb", options=0x8, opened_path=0x0, context=0x1006d0520) at main/streams/streams.c:2022
2022		php_stream *stream = NULL;
```

在`/main/stream/stream.c:2022`行找到了次函数的实现。

跟踪到`/main/stream/stream.c:2064`行：

```c
stream = wrapper->wops->stream_opener(wrapper,
				path_to_open, mode, options ^ REPORT_ERRORS,
				opened_path, context STREAMS_REL_CC TSRMLS_CC);
```

跟进此函数：

```Bash
gdb-peda$ s
php_plain_files_stream_opener (wrapper=0x1004ae498, path=0x1012181d8 "./test.php/.", mode=0x7fff5fbfdf2d "wb", options=0x0, opened_path=0x0, context=0x1006d0520)
    at main/streams/plain_wrapper.c:1020
1020		if (((options & STREAM_DISABLE_OPEN_BASEDIR) == 0) && php_check_open_basedir(path TSRMLS_CC)) {
```

在`main/streams/plain_wrapper.c:1020`，找到此函数实现：

```c
static php_stream *php_plain_files_stream_opener(php_stream_wrapper *wrapper, const char *path, const char *mode,
		int options, char **opened_path, php_stream_context *context STREAMS_DC TSRMLS_DC)
{
	if (((options & STREAM_DISABLE_OPEN_BASEDIR) == 0) && php_check_open_basedir(path TSRMLS_CC)) {
		return NULL;
	}

	return php_stream_fopen_rel(path, mode, opened_path, options);
}
```

继续跟进 `php_stream_fopen_rel`函数，在main/streams/plain_wrapper.c的1024行：

```Bash
gdb-peda$ s
_php_stream_fopen (filename=0x1012181d8 "./test.php/.", mode=0x7fff5fbfdf2d "wb", opened_path=0x0, options=0x0) at main/streams/plain_wrapper.c:920
920		char *realpath = NULL;
```

跟进到`main/streams/plain_wrapper.c:937`，进入函数`expand_filepath(filename, NULL TSRMLS_CC)`

```Bash
gdb-peda$ s
expand_filepath (filepath=0x1012181d8 "./test.php/.", real_path=0x0) at main/fopen_wrappers.c:732
732		return expand_filepath_ex(filepath, real_path, NULL, 0 TSRMLS_CC);
```

在`main/fopen_wrappers.c:732`行，看到函数实现：

```C
PHPAPI char *expand_filepath(const char *filepath, char *real_path TSRMLS_DC)
{
	return expand_filepath_ex(filepath, real_path, NULL, 0 TSRMLS_CC);
}
```

继续跟踪函数`expand_filepath_ex`,在`main/fopen_wrappers.c:738`行

```c
PHPAPI char *expand_filepath_ex(const char *filepath, char *real_path, const char *relative_to, size_t relative_to_len TSRMLS_DC)
{
	return expand_filepath_with_mode(filepath, real_path, relative_to, relative_to_len, CWD_FILEPATH TSRMLS_CC);
}
```

继续跟踪函数`expand_filepath_with_mode`,在`main/fopen_wrappers.c:746`行：

```bash
gdb-peda$ s
expand_filepath_with_mode (filepath=0x1012181d8 "./test.php/.", real_path=0x0, relative_to=0x0, relative_to_len=0x0, realpath_mode=0x1) at main/fopen_wrappers.c:752
752		if (!filepath[0]) {
```

执行到`main/fopen_wrappers.c:797`行：

```c
	if (virtual_file_ex(&new_state, filepath, NULL, realpath_mode TSRMLS_CC)) {
		efree(new_state.cwd);
		return NULL;
	}
```

跟进`virtual_file_ex`函数：

```bash
gdb-peda$ s
virtual_file_ex (state=0x7fff5fbfd800, path=0x1012181d8 "./test.php/.", verify_path=0x0, use_realpath=0x1) at Zend/zend_virtual_cwd.c:1181
1181		int path_length = strlen(path);
```

继续向下执行，读代码可以发现结构体state中存储着要被写入的文件的路径，

```bash
gdb-peda$ p *state
$6 = {
  cwd = 0x1006d0958 "/Users/wonderkun/script/php-src/sapi/cli",
  cwd_length = 0x28
}
```

发现`Zend/zend_virtual_cwd.c：1320`行,代码如下，修改了path_length,之后把path_length赋值给了state.cwd_length,所以`tsrm_realpath_r`一定是对路径做处理的函数，是这个问题的关键。

```C
path_length = tsrm_realpath_r(resolved_path, start, path_length, &ll, &t, use_realpath, 0, NULL TSRMLS_CC);
```

跟进此函数：

```Bash
gdb-peda$ s
tsrm_realpath_r (path=0x7fff5fbfd370 "/Users/wonderkun/script/php-src/sapi/cli/./test.php/.", start=0x1, len=0x35, ll=0x7fff5fbfd340, t=0x7fff5fbfd338, use_realpath=0x1,
    is_dir=0x0, link_is_dir=0x0) at Zend/zend_virtual_cwd.c:781
```

从最开始的函数入口，到找到问题存在的函数，整个调用栈是这样的，方便大家看：

```bash
gdb-peda$ bt
#0  tsrm_realpath_r (path=0x7fff5fbfd370 "/Users/wonderkun/script/php-src/sapi/cli/./test.php/.", start=0x1, len=0x35, ll=0x7fff5fbfd340, t=0x7fff5fbfd338, use_realpath=0x1,
    is_dir=0x0, link_is_dir=0x0) at Zend/zend_virtual_cwd.c:794
#1  0x000000010028c615 in virtual_file_ex (state=0x7fff5fbfd800, path=0x1012181d8 "./test.php/.", verify_path=0x0, use_realpath=0x1) at Zend/zend_virtual_cwd.c:1320
#2  0x00000001001c1e9e in expand_filepath_with_mode (filepath=0x1012181d8 "./test.php/.", real_path=0x0, relative_to=0x0, relative_to_len=0x0, realpath_mode=0x1)
    at main/fopen_wrappers.c:797
#3  0x00000001001c1bc3 in expand_filepath_ex (filepath=0x1012181d8 "./test.php/.", real_path=0x0, relative_to=0x0, relative_to_len=0x0) at main/fopen_wrappers.c:740
#4  0x00000001001c0364 in expand_filepath (filepath=0x1012181d8 "./test.php/.", real_path=0x0) at main/fopen_wrappers.c:732
#5  0x00000001001e1c8a in _php_stream_fopen (filename=0x1012181d8 "./test.php/.", mode=0x7fff5fbfdf2d "wb", opened_path=0x0, options=0x0) at main/streams/plain_wrapper.c:937
#6  0x00000001001e25f4 in php_plain_files_stream_opener (wrapper=0x1004ae498, path=0x1012181d8 "./test.php/.", mode=0x7fff5fbfdf2d "wb", options=0x0, opened_path=0x0,
    context=0x1006d0520) at main/streams/plain_wrapper.c:1024
#7  0x00000001001dbb12 in _php_stream_open_wrapper_ex (path=0x1012181d8 "./test.php/.", mode=0x7fff5fbfdf2d "wb", options=0x8, opened_path=0x0, context=0x1006d0520)
    at main/streams/streams.c:2064
#8  0x000000010012b6e5 in zif_file_put_contents (ht=0x2, return_value=0x1006d0848, return_value_ptr=0x10069b160, this_ptr=0x0, return_value_used=0x0) at ext/standard/file.c:616
#9  0x000000010034a8bc in zend_do_fcall_common_helper_SPEC (execute_data=0x10069b178) at Zend/zend_vm_execute.h:558
#10 0x00000001002d32f7 in ZEND_DO_FCALL_SPEC_CONST_HANDLER (execute_data=0x10069b178) at Zend/zend_vm_execute.h:2599
#11 0x000000010029eadf in execute_ex (execute_data=0x10069b178) at Zend/zend_vm_execute.h:363
#12 0x000000010029f53e in zend_execute (op_array=0x1006cf438) at Zend/zend_vm_execute.h:388
#13 0x0000000100257838 in zend_execute_scripts (type=0x8, retval=0x0, file_count=0x3) at Zend/zend.c:1341
#14 0x00000001001b73af in php_execute_script (primary_file=0x7fff5fbff230) at main/main.c:2597
#15 0x0000000100396835 in do_cli (argc=0x2, argv=0x7fff5fbff948) at sapi/cli/php_cli.c:994
#16 0x0000000100395737 in main (argc=0x2, argv=0x7fff5fbff948) at sapi/cli/php_cli.c:1378
```

`tsrm_realpath_r`函数中存在递归，所以完全理解起来还是比较复杂的，但是只需要看懂其中的一层，就可以理解其他的部分了，看如下关键代码：

```c
		i = len;  
       // i的初始值为字符串的长度
		while (i > start && !IS_SLASH(path[i-1])) {
			i--;   
          // 把i定位到第一个/的后面
		}
		if (i == len ||
			(i == len - 1 && path[i] == '.')) {
			len = i - 1;  
           //  删除路径中最后的 /. , 也就是 /path/test.php/. 会变为 /path/test.php  
			is_dir = 1;
			continue;
		} else if (i == len - 2 && path[i] == '.' && path[i+1] == '.') {
			//删除路径结尾的 /.. 
			is_dir = 1;
			if (link_is_dir) {
				*link_is_dir = 1;
			}
			if (i - 1 <= start) {
				return start ? start : len;
			}
			j = tsrm_realpath_r(path, start, i-1, ll, t, use_realpath, 1, NULL TSRMLS_CC);
		   // 进行递归调用的时候，这里把strlen设置为了i-1，
```

可以看出在做路径处理的时候，会递归的删除掉路径中存在的`/.`,所以导致写入文件成功。但是为什么不能覆盖老文件呢？

还要多谢@yihchin大牛帮我分析，看Zend/zend_virtual_cwd.c文件的两段代码：

```c
1077 if (save && php_sys_lstat(path, &st) < 0) {
1078			if (use_realpath == CWD_REALPATH) {
1079				/* file not found */
1080				return -1;
1081			}
1082			/* continue resolution anyway but don't save result in the cache */
1083			save = 0;
1084		}
```

```c
1120 if (save) {
1121				directory = S_ISDIR(st.st_mode);
1122				if (link_is_dir) {
1123					*link_is_dir = directory;
1124				}
1125				if (is_dir && !directory) {
1125					/* not a directory */
1127					free_alloca(tmp, use_heap);
1128					return -1;
1129				}
1130			}
```

`php_sys_lstat`是一个宏定义，其实是系统函数`lstat`,主要功能是获取文件的描述信息存入`st`结构体中,由于上面分析会删除掉路径中的`/.`，所以调用时传入的`path=/Users/wonderkun/script/php-src/sapi/cli/./test.php` 。  当第一次执行时不存在`test.php`文件，函数`php_sys_lstat`返回 `-1`,所以第1083行会被执行，重置save为0，所以1120-1130行都没有被执行。

当第二次执行，覆盖老文件的时候，`/Users/wonderkun/script/php-src/sapi/cli/./test.php`已经是一个存在的文件了，所以`php_sys_lstat`返回0，st中存储的是一个文件的信息，save还是1，导致1120-1130行被执行。由于之前php认为`/Users/wonderkun/script/php-src/sapi/cli/./test.php/.` 是一个目录（is_dir是1），现在有获取到`/Users/wonderkun/script/php-src/sapi/cli/./test.php`   是一个文件，所以`is_dir && !directory`为true，函数返回了-1，得到的路径长度出错，所以无法覆盖老文件了。  
