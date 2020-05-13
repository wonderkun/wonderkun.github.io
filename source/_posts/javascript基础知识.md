---
title: javascript基础知识
url: 774.html
id: 774
categories:
  - 代码控
date: 2019-07-18 12:48:56
tags:
  - javascript
---



## javascript基础知识

初学javascript，有什么写的不对的地方，请师傅们斧正。

<!--more-->

### 0x1 怪异的javascript对象

对象是一个包含相关数据和方法的集合（通常由一些变量和函数组成，我们称之为对象里面的属性和方法）。在其他经典的面向对象的语言中我们并没有办法直接去创建对象，我们都需要先用`class`这样的关键词创建一个对象模板（被称为类），然后调用类的构造函数去初始化一个对象出来，在类中描述的属性和方法会复制一份到对象中去，然而对于javascript来说，情况并非如此（不像“经典”的面向对象的语言，从构建函数创建的新实例的特征并非全盘复制，而是通过一个叫做原形链的参考链链接过去的，所以这并非真正的实例，严格的讲， JavaScript 在对象间使用和其它语言的共享机制不同，这个后面再讲），我们可以直接创建一个对象而不需要对象模板,创建方法请参考第二节。

###  0x2 javascript对象的基础知识

在javascript中我们可以直接创建一个对象，而不需要对象模板，

```javascript
var person = {
  name : ['Bob', 'Smith'],
  age : 32,
  gender : 'male',
  interests : ['music', 'skiing'],
  bio : function() {
    alert(this.name[0] + ' ' + this.name[1] + ' is ' + this.age + ' years old. He likes ' + this.interests[0] + ' and ' + this.interests[1] + '.');
  },
  greeting: function() {
    alert('Hi! I\'m ' + this.name[0] + '.');
  }
};
```

一个如上所示的对象被称之为对象的字面量(literal)——手动的写出对象的内容来创建一个对象。不同于从类实例化一个对象。

访问person的属性和方法，可以使用如下方式：

```javascript
person.age // 点号访问法
person["age"] //括号表示法
```

也可以在一个对象中来作为另一对象的值，例如修改person的name成员

```javascript
name : {
  first : 'Bob',
  last : 'Smith'
},
```

这样其实创建了一个子命名空间，可以使用如下方式访问：

```
person.name.first
person["name"]["first"]
```

关键字"this"指向了当前代码运行时的对象，这里即指person对象。

除此之外，还可以直接修改对象中的属性和方法：

```javascript
person.age = 45
person.greeting = function() {
    alert('Hi! I\'m ' + this.name.first + '.');
  }
```

### 0x3 构建函数和对象示例

但是我们不能仅满足于以上的创建对象的方法，因为很多时候我们需要创建很多的对象(假如我要定义1万个人，它们都具有相同的属性和方法，只是属性的值不一样，我总不能把上面的那个定义抄一万次吧)。所以javascript也需要有一个像经典语言那样的能够创建对象模板的方法，可以根据模板自动化的创建我们需要的对象。JavaScript 用一种称为**构建函数**的特殊函数来定义对象和它们的特征。**构建函数**提供了创建您所需对象（实例）的有效方法，将对象的数据和特征函数按需联结至相应对象。

一个例子如下：

```javascript
function Person(name) {
  this.name = name;
  this.greeting = function() {
    alert('Hi! I\'m ' + this.name + '.');
  };
}
```

这个构建函数是 JavaScript 版本的类，这里使用了`this`关键词，指向这个构建函数创建的示例自身，而非指向构建函数（这跟其他面向对象语言中的this的含义一样）。

**一个构建函数通常是大写字母开头，这样便于区分构建函数和普通函数。**

使用构建函数创建新的实例:

```javascript
var person1 = new Person('Bob'); //
var person2 = new Person('Sarah');
```

当新的对象被创立, 变量`person1`与`person2`有效地包含了以下值：

```javascript
{
  name : 'Bob',
  greeting : function() {
    alert('Hi! I\'m ' + this.name + '.');
  }
}

{
  name : 'Sarah',
  greeting : function() {
    alert('Hi! I\'m ' + this.name + '.');
  }
}
```

#### 创建实例的其他方法

##### Object()构造函数

```javascript
var person1 = new Object(); //首先, 您能使用Object()构造函数来创建一个新对象。 是的， 一般对象都有构造函数，它创建了一个空的对象。

//这样就在person1变量中存储了一个空对象。然后, 可以根据需要, 使用点或括号表示法向此对象添加属性和方法
person1.name = 'Chris';
person1['age'] = 38;
person1.greeting = function() {
  alert('Hi! I\'m ' + this.name + '.');
}
```

还可以将对象文本传递给Object() 构造函数作为参数， 以便用属性/方法填充它

```javascript
var person1 = new Object({
  name : 'Chris',
  age : 38,
  greeting : function() {
    alert('Hi! I\'m ' + this.name + '.');
  }
});
```

##### 使用create()方法

JavaScript有个内嵌的方法`create()`, 它允许您基于现有对象创建新的对象实例。

```javascript
var person2 = Object.create(person1);

person2.name
person2.greeting()
```

您可以看到，`person2`是基于`person1`创建的， 它们具有相同的属性和方法。这非常有用， 因为它允许您创建新的对象实例而无需定义构造函数。

### 0x4 基于原型的语言

JavaScript 常被描述为一种**基于原型的语言 (prototype-based language)**——每个对象拥有一个**原型对象**，对象以其原型为模板、从原型继承方法和属性。原型对象也可能拥有原型，并从中继承方法和属性，一层一层、以此类推。这种关系常被称为**原型链 (prototype chain)**，它解释了为何一个对象会拥有定义在其他对象中的属性和方法。

在传统的 OOP 中，首先定义“类”，此后创建对象实例时，类中定义的所有属性和方法都被复制到实例中。在 JavaScript 中并不如此复制——而是在对象实例和它的构造器之间建立一个链接（它是__proto__属性，是从构造函数的`prototype`属性派生的），之后通过上溯原型链，在构造器中找到这些属性和方法。

#### 使用javascript中的原型

在javascript中，函数可以有属性。 每个函数都有一个特殊的属性叫作`原型（prototype）`,

```javascript
function doSomething(){}
doSomething.prototype
/*
doSomething 函数有一个默认的原型属性如下：
{
    constructor: ƒ doSomething(),
    __proto__: {
        constructor: ƒ Object(),
        hasOwnProperty: ƒ hasOwnProperty(),
        isPrototypeOf: ƒ isPrototypeOf(),
        propertyIsEnumerable: ƒ propertyIsEnumerable(),
        toLocaleString: ƒ toLocaleString(),
        toString: ƒ toString(),
        valueOf: ƒ valueOf()
    }
}
*/

// 我们可以添加一些属性到 doSomething 的原型上面
doSomething.prototype.foo = "bar"; 

//然后，我们可以使用 new 运算符来在现在的这个原型基础之上，创建一个 doSomething 的实例。
var doSomeInstancing = new doSomething();
doSomeInstancing.prop = "some value"; // add a property onto the object
console.log( doSomeInstancing );
/*
{
    prop: "some value",
    __proto__: {
        foo: "bar",
        constructor: ƒ doSomething(),
        __proto__: {
            constructor: ƒ Object(),
            hasOwnProperty: ƒ hasOwnProperty(),
            isPrototypeOf: ƒ isPrototypeOf(),
            propertyIsEnumerable: ƒ propertyIsEnumerable(),
            toLocaleString: ƒ toLocaleString(),
            toString: ƒ toString(),
            valueOf: ƒ valueOf()
        }
    }
}
*/
```

其实`doSomeInstancing` 的 `__proto__` 属性就是`doSomething.prototype`

```javascript
doSomeInstancing.__proto__ === doSomething.prototype
//true
```

当你访问 `doSomeInstancing` 的一个属性, 浏览器首先查找 `doSomeInstancing` 是否有这个属性. 如果 `doSomeInstancing` 没有这个属性, 然后浏览器就会在 `doSomeInstancing` 的 `__proto__` 中查找这个属性(也就是 doSomething.prototype). 如果 doSomeInstancing 的 `__proto__` 有这个属性, 那么 doSomeInstancing 的 `__proto__`上的这个属性就会被使用. 否则, 如果 doSomeInstancing 的 `__proto__` 没有这个属性, 浏览器就会去查找 doSomeInstancing 的 `__proto__` 的 `__proto__` ，看它是否有这个属性. 默认情况下, 所有函数的原型属性的 `__proto__` 就是 `window.Object.prototype`.注意`window.Object.prototype.__proto__`是不存在的。

在console界面输入`person.`可以看到`person`这个对象的可用的成员名称,除了我们定义在`Person()`构造器中的成员之外还有一些`watch`,`valueOf`等成员，这些成员定义在 `Person()` 构造器的原型对象、即 `Object` 之上。

```
person1 ----inherit----> Person.prototype----inherit---->Object.prototype 
```

注意**：必须重申，原型链中的方法和属性**没有**被复制到其他对象——它们被访问需要通过前面所说的“原型链”的方式。**

#### prototype 属性：继承成员被定义的地方

如果你查看 `Object` 参考页，会发现左侧列出许多属性和方法——大大超过我们在 `person1` 对象中看到的继承成员的数量。某些属性或方法被继承了，而另一些没有——为什么呢？

继承的属性和方法是定义在 `prototype` 属性之上的（你可以称之为子命名空间 (sub namespace) ）——那些以 `Object.prototype.` 开头的属性，而非仅仅以 `Object.` 开头的属性。`prototype` 属性的值是一个对象，我们希望被原型链下游的对象继承的属性和方法，都被储存在其中。

```javascript
person1.valueOf === Object.prototype.valueOf 
//true
```

这里可能有些疑惑，构造器本身就是函数，你怎么可能在构造器这个函数中定义一个方法呢？其实函数也是一个对象类型，你可以查阅 `Function()` 构造器的参考文档以确认这一点。

每一个函数对象（`Function`）都有一个`prototype`属性，并且*只有*函数对象有`prototype`属性，因为`prototype`本身就是定义在`Function`对象下的属性。当我们输入类似`var person1=new Person(...)`来构造对象时，JavaScript实际上参考的是`Person.prototype`指向的对象来生成`person1`。另一方面，`Person()`函数是`Person.prototype`的构造函数，也就是说`Person===Person.prototype.constructor`。

看到了，就大概明白了定义在 `prototype` 上的方法和定义在 `构造函数` 里的方法有啥区别了，例如如下代码：

```javascript

function Person(name) {
  this.name = name;
  this.greeting = function() {
    alert('Hi! I\'m ' + this.name + '.');
  };
}
```

这样写的结果是，当我们新创建一个`Person`对象的时候，`this.greeting = function() { ... }` 就会执行一次，这样 `greeting` 方法其实是绑定在对象上的，而不是绑定在`Person`上的,也就是每个实例都有自己的`greeting` 他们不会相互干扰。

```javascript
> person1 = new Person(); 
< Person {name: undefined, greeting: ƒ}
> person2 = new Person();
< Person {name: undefined, greeting: ƒ}
> person1.greeting == person2.greeting
< false
```

因为`greeting`方法没有定义在`prototype`,所以`greeting`方法也不会被继承。

但是我们考虑下面的写法：

```javascript

function Person(name) {
  this.name = name;
}

Person.prototype.greeting = function() {
    alert('Hi! I\'m ' + this.name + '.');
  };
```

```javascript
> person1 = new Person(); 
< Person {name: undefined}
> person2 = new Person();
< Person {name: undefined}
> person1.greeting == person2.greeting
< true

```

我们看到，两个实例共享了同一个方法。但是思考一个问题，如果我们改了`person1.greeting`那是不是`person2.greeting`也会被改变了呢，做个试验：

```javascript
> person1.greeting = 'test'
< "test"
> person2.greeting
< ƒ () {
    alert('Hi! I\'m ' + this.name + '.');
  }
```
哈哈想多了哈，这样操作的结果只会是让`person1`多一个`greeting`属性：

![http://pic.wonderkun.cc/uploads/2019/07/2019-07-18-20-36-48.png](http://pic.wonderkun.cc/uploads/2019/07/2019-07-18-20-36-48.png)

因为优先级的关系，这里覆盖掉了原型中的`greeting`方法。

如果真的想改，那就是原型链污染的问题了，可以如下操作：

```javascript
> person1.__proto__.greeting = 'test'
< "test"
> person2.greeting
< "test"
```

#### create()

曾经讲过如何用 `Object.create()` 方法创建新的对象实例。

```javascript
var person2 = Object.create(person1);
//create() 实际做的是从指定原型对象创建一个新的对象。这里以 person1 为原型对象创建了 person2 对象。在控制台输入：
person2.__proto__ === person1
// true
```

#### constructor属性

每个实例对象都从原型中继承了一个constructor属性，该属性指向了用于构造此实例对象的构造函数。

```javascript
person1.constructor === Person
// true
```

一个小技巧是，你可以在 `constructor` 属性的末尾添加一对圆括号（括号中包含所需的参数），从而用这个构造器创建另一个对象实例。毕竟构造器是一个函数，故可以通过圆括号调用；只需在前面添加 `new` 关键字，便能将此函数作为构造器使用。

```
person2 = new person1.constructor("person2");
```

#### 修改原型

可以通过修改原型，来更新整个继承链。

```javascript
//给Person动态添加一个方法
Person.prototype.farewell = function() {
  alert(this.name.first + ' has left the building. Bye for now!');
}
```

然后由Person构造器创建的对象都有了这个方法，可以直接调用：

```javascript
person1.farewell();
```

这种继承模型下，上游对象的方法不会复制到下游的对象实例中；下游对象本身虽然没有定义这些方法，但浏览器会通过上溯原型链、从上游对象中找到它们。这种继承模型提供了一个强大而可扩展的功能系统。

依次类推，也可以在`prototype`上定义可以被直接继承的属性，但是一般这样的属性都是常属性，如果常属性和构造函数中的属性重名，构造函数中的属性就会屏蔽掉`prototype`上定义的属性，但是可以通过`person1.__proto__.`的方式获取。

但是你不可以按照下面的方式写代码,因为本例中 `this` 引用全局范围，而非函数范围:

```javascript
Person.prototype.fullName = this.name.first + ' ' + this.name.last;
```

因此，一种极其常见的对象定义模式是，在构造器（函数体）中定义属性、在 `prototype`属性上定义方法。

### 0x5 原型式的继承

关于继承，这篇文章讲的很好了[https://juejin.im/entry/58dfbe0361ff4b006b166388](https://juejin.im/entry/58dfbe0361ff4b006b166388)，经常翻翻看，可以增强对继承的理解。

#### 实现属性的继承

到目前为止我们已经了解了一些关于原型链的实现方式以及成员变量是如何通过它来实现继承，那么我们如何创建一个继承自另一对象的JavaScript对象呢？

不同于其他的面向对象语言，JavaScript使用了另一套实现方式，继承的对象函数并不是通过复制而来，而是通过原型链继承（通常被称为 **原型式继承 ——** **prototypal inheritance）**。

```javascript
function Person(first, last, age, gender, interests) {
  this.name = {
    first,
    last
  };
  this.age = age;
  this.gender = gender;
  this.interests = interests;
};

//所有的方法都定义在构造器的原型上
Person.prototype.greeting = function() {
  alert('Hi! I\'m ' + this.name.first + '.');
};

```

创建一个Teacher类，继承于Person类：

```javascript
function Teacher(first, last, age, gender, interests, subject) {
  Person.call(this, first, last, age, gender, interests);
  this.subject = subject;
}
```

`call`这个函数允许您调用一个在这个文件里别处定义的函数。第一个参数指明了在您运行这个函数时想对此函数中原本的`this`指定的值，也就是说，您可以重新指定您调用的函数里所有“`this`”指向的对象。这里指定了`Person`中的`this`其实是`Teacher`的示例.

所以在这个例子里，我们很有效的在`Teacher()`构造函数里运行了`Person()`构造函数,在`Teacher()`里定义的一样的属性，但是用的是传送给`Teacher()`，而不是`Person()`的值（这里使用的类似于值传递的方式实现的，跟我们在其他语言中理解的继承不一样）。

#### 设置 Teacher() 的原型和构造器引用

到目前为止一切看起来都还行，但是我们遇到问题了。我们已经定义了一个新的构造器，这个构造器默认有一个空的原型属性。
所以`Teacher()`并没有`Person()`的 `greeting` 方法，所以我们需要让`Teacher()`从`Person()`的原型对象里继承方法。

```javascript
Teacher.prototype = Object.create(Person.prototype);

Teacher.prototype === Person.prototype
//false
Teacher.prototype.__proto__ === Person.prototype
//true
```

我们用`create`函数来创建一个和`Person.prototype`一样的新的原型属性值（这个属性指向一个包括属性和方法的对象），然后将其作为`Teacher.prototype`的属性值。这意味着`Teacher.prototype`现在会继承`Person.prototype`的所有属性和方法。

现在`Teacher()`的`prototype`的`constructor`属性指向的是`Person()`, 这是由我们生成`Teacher()`的方式决定的（这篇 [Stack Overflow post](https://stackoverflow.com/questions/8453887/why-is-it-necessary-to-set-the-prototype-constructor) 文章会告诉您详细的原理)，我们需要做一个修改：

```javascript
Teacher.prototype.constructor
// Person
Teacher.prototype.constructor = Teacher;
```

任何您想要被继承的方法都应该定义在构造函数的`prototype`对象里，并且*永远*使用父类的`prototype`来创造子类的`prototype`，这样才不会打乱类继承结构。

向`Teacher()`中添加新的`greeting()`函数：

```javascript
Teacher.prototype.greeting = function(){
    consol.log('greeting');
}
```

### 0x6 原型链污染一般存在的两种paylod

根据上面的基础知识我们知道，如果`person`是`Person`的实例，那么必然存在两个等式成立

```
person.constructor == Person
person.__proto__ == Person.prototype
```

所以就有两种利用 `person` 获取到 `Object` 的`prototype`的方法

```
1. person.__proto__.__proto__ == Object.prototype
2. person.constructor.prototype.__proto__ == Object.prototype
```

但是如果`person`不是由构建函数产生的，是直接定义的对象：

```javascript
person = {
  "name":'hello'
}
```

此时 `person` 的原型直接就是 `Object` 了,他的构造器也是`Object`，所以下面两个等式成立：

```
1. person.__proto__ == Object.prototype
2. person.constructor.prototype == Object.prototype
```

#### 会造成原型链污染的例子

https://www.leavesongs.com/PENETRATION/javascript-prototype-pollution-attack.html

在文章中说的比较明白: 

```javascript
function merge(target, source) {
    for (let key in source) {
        if (key in source && key in target) {
            merge(target[key], source[key])
        } else {
            target[key] = source[key]
        }
    }
}
```

下面不会造成原型链污染：

```javascript

let o1 = {}
let o2 = {a: 1, "__proto__": {b: 2}}

// let o2 = {a: 1, __proto__: {b: 2}}
merge(o1, o2)
console.log(o1.a, o1.b)

o3 = {}
console.log(o3.b)

```

这是因为，我们用JavaScript创建o2的过程`（let o2 = {a: 1, "__proto__": {b: 2}}）`中，`__proto__`已经代表o2的原型了，此时遍历o2的所有键名，你拿到的是`[a, b]`，`__proto__`并不是一个key，自然也不会修改Object的原型。


但是下面这样就会造成原型链污染了：

```javascript

let o1 = {}
let o2 = JSON.parse('{"a": 1, "__proto__": {"b": 2}}')
merge(o1, o2)
console.log(o1.a, o1.b)

o3 = {}
console.log(o3.b)
```

参考链接：

[https://developer.mozilla.org/zh-CN/docs/Learn/JavaScript/Objects/Basics](https://developer.mozilla.org/zh-CN/docs/Learn/JavaScript/Objects/Basics)

[https://developer.mozilla.org/zh-CN/docs/Learn/JavaScript/Objects/Object-oriented_JS](https://developer.mozilla.org/zh-CN/docs/Learn/JavaScript/Objects/Object-oriented_JS)

[https://developer.mozilla.org/zh-CN/docs/Learn/JavaScript/Objects/Object_prototypes](https://developer.mozilla.org/zh-CN/docs/Learn/JavaScript/Objects/Object_prototypes)

[https://developer.mozilla.org/zh-CN/docs/Web/JavaScript/Inheritance_and_the_prototype_chain](https://developer.mozilla.org/zh-CN/docs/Web/JavaScript/Inheritance_and_the_prototype_chain)

[https://developer.mozilla.org/zh-CN/docs/Web/JavaScript/Inheritance_and_the_prototype_chain](https://developer.mozilla.org/zh-CN/docs/Web/JavaScript/Inheritance_and_the_prototype_chain)

[https://www.cnblogs.com/shuiyi/p/5305435.html](https://www.cnblogs.com/shuiyi/p/5305435.html)

[https://juejin.im/entry/58dfbe0361ff4b006b166388](https://juejin.im/entry/58dfbe0361ff4b006b166388)

[https://www.leavesongs.com/PENETRATION/javascript-prototype-pollution-attack.html](https://www.leavesongs.com/PENETRATION/javascript-prototype-pollution-attack.html)

