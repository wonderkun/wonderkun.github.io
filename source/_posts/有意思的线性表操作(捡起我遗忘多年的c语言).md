---
title: 有意思的线性表操作(捡起我遗忘多年的c语言)
url: 577.html
id: 577
categories:
  - 代码控
date: 2017-03-02 17:48:35
tags:
  - code
  - c
---

线性表是数据结构这门课程最开始讲的内容,也是平常写程序中最常用到得数据结构.下面就写一下一些有意思的线性表操作.

<!--more-->

### 线性表的定义 
在操作线性表之前,我先定义一下线性表的结构,方便之后看一些操作,阅读代码:
#### 线性表的数据结构定义
```c
typedef struct{
    int *data;
    int length ;
 }List,*ListPoint;
```
#### 线性表的基本操作
初始化一个线性表
```c
void initList(List &list){
    //初始化线性表
    int i;
    list.data = new int[MAX_LENGTH];
    srand(int(time(0)));
    for(i=0;i<10;i++){
        list.data[i]=random(10);
    }
    list.length = i;
}
```
打印一个线性表中的元素
```c
void printList(List &list){
     /*
        打印自身 
     */
     int i=0; 
     cout<<"the length of the list:"<<list.length<<endl;
     cout<<"the num of the list:";
     for(i=0;i<list.length;i++){
         cout<<list.data[i]<<" ";
     }
     cout<<endl;
}
```
对线性表元素从小到大进行排序
```c
void sortList(List &list){
   /*
      利用冒泡法对元素进行排序 
      从小到达排列 
   */
   int i,j;
   for(i=list.length-1;i>0;i--){
       for(j=0;j<i;j++){
         if(list.data[j]>list.data[j+1]){
             list.data[j] = list.data[j+1]^list.data[j];
             list.data[j+1] = list.data[j+1]^list.data[j];
             list.data[j] = list.data[j+1]^list.data[j];
         }
       }
   }
}
```

###  具体的操作要求

#### 用空间复杂度为O(1),和时间复杂度为O(n)的算法,实现线性表的倒置
其实就是第一个与最后一个交换位置,第二个和倒数第二个交换位置:
```c
bool reverseList(List &list){
      /*
         用空间复杂度为1的算法,实现list 倒置   
      */
     if(list.length==0) return false ;
     
     int i=0 ;
     for(i=0;i<list.length/2;i++){
        /*
          list.data[i] 与 list.data[list.length-1-i] 交换
        */
         list.data[i] = list.data[i]^list.data[list.length-1-i];
         list.data[list.length-1-i] = list.data[i]^list.data[list.length-1-i];
         list.data[i] = list.data[i]^list.data[list.length-1-i]; 
 
     }
     return true;
} 
```
#### 用空复杂度为O(1)和时间复杂度为O(n)的算法,删除线性表所以值为x的元素 
从头开始遍历线性表,用pos记录当前的线性表的长度,如果当前扫描的元素值不是x,就将他加入到线性表中,并且pos+1,如果是x,就什么也不做.
```c
bool deleteList(List &list,int x){

    /*
       在线性表中删除所有值为  x 的元素
       要求空间复杂度为 o(1) , 时间复杂度为 o(n)
    */

    if(list.length==0) return false ;
    int pos=0,i=0;
    for(i=0;i<list.length;i++){
       if(list.data[i]!=x){
           list.data[pos]=list.data[i];
           pos++;
       }
    }
    list.length = pos;  //更新一下线性表的长度
    return true ;
}
```

####   要求算法时间复杂度   O(n) 空间复杂度 O(1)的算法删除有序的线性表中值位于 s 和 t之间的元素.包含s和t
注意这里讲的是有序的表,那么值位于s和t之间的元素肯定是连在一起的
所以我们只需要找到第一个该删的元素,和最后一个该删的元素,就可以了 
```c
bool deleteListSection(List &list,int s,int t){
    /*
       删除 有序表 list中 处于 s和t之间的元素,包含 s和t 
    */
    if(s>=t || list.length==0) return false ;
    sortList(list); //先进行排序,然后再操作 
    int i=0,j=list.length-1;
    while( (i<list.length) && list.data[i]<s ) i++; // 找到第一个需要删除的 
    while( j>-1 && list.data[j]>t) j--; //找到最后一个要删除的元素
    for(j=j+1;j<list.length;j++,i++){
        list.data[i] = list.data[j];
    }
   list.length = i;
   return true ;
}
```

#### 要求算法时间复杂度   O(n) 空间复杂度 O(1)的算法删除无序的线性表值位于s和t之间的元素,包含s和t
 
从头开始扫描顺序表,用 k 记录下在s 与 t 之间的个数(初始值 k=0) ,对于当前要扫描的元素 如果值不在 s和t之间,则前移 k 个位置 ,如果在 s和t之间 ,就 k++.
```c
bool deleteListSectionNoSort(List &list,int s,int t){
     /*
       删除顺序表中(无序的)  处于 s和t之间的元素  
       要求算法时间复杂度   O(n) 空间复杂度 O(1)
     */
     if(s>=t || list.length==0) return false ;
     /*
        从头开始扫描顺序表,用 k 记录下在s 与 t 之间的个数(初始值 k=0) ,对于当前要扫描的元素 
        如果值不在 s和t之间,则前移 k 个位置 ,如果在 s和t之间 ,就 k++ 
     */
     int i;
     int k=0;
     for(i=0;i<list.length;i++){
        if(list.data[i]>=s && list.data[i] <=t){
            k++;
        }else{
            list.data[i-k] = list.data[i];
        }

     }
     list.length = list.length - k;

     return true ;
}
```



####  删除有序的顺序表中重复的元素,使剩下来的元素都不相同

```c
void  deleteRepeate(List &list){
     /*
         在有序表中删除重复的元素,使剩下的元素都不相同 
         注意是有序表  
     */
     int i ;
     int k=0 ;
     for(i=0;i<list.length-1;i++){
         
         if(list.data[i]==list.data[i+1])
         {
              k++;
         } 
         else{
              list.data[i-k] = list.data[i];
         }
     }
   list.length = list.length - k ;
}
```
第二种思路
```c
void deleteRepeate_2(List &list){
    /*
      删除有序表重复元素的第二种算法 
    */
    int i,j;
    for(i=0,j=1;j<list.length;j++){
        if(list.data[i]!=list.data[j]) {
            list.data[++i] = list.data[j] ; // 注意是 先加再拷贝 
        }
    }
    list.length = i+1;
}
```

#### 合并两个有序的顺序表到一个有序的顺序表中去
经典算法,应该都会
```c
bool mergeList(List &lista,List &listb,List &list){
       /*
         合并两个有序的 顺序表到一个顺序表中.
       */
       if(lista.length+listb.length>MAX_LENGTH) return false ;
       int i=0,j=0,k=0 ;
       while(i<lista.length&&j<listb.length){
          if(lista.data[i]<listb.data[j])
             list.data[k++]=lista.data[i++];
          else 
             list.data[k++] = listb.data[j++];
       }
     
     while(i<lista.length)
         list.data[k++] = lista.data[i++];
     while(j<listb.length)
         list.data[k++] = listb.data[j++];
   
   list.length = lista.length+ listb.length ;
   return true;
}
```
#### 在 一个 顺序表 A[m+n]中存放着两个线性表 (a1,a2,a3,...,am) 和 (b1,b2,b3,....bn) 这里将 顺序表的前后位置互换 ,变为  (b1,b2,b3,....bn)和 (a1,a2,a3,...,am)

参照前面 reverseList 的方法 ,先把 (a1,a2,a3...am)变为 (am,am-1,am-2,...a3,a2,a1) ,对b也进行这样的处理 , 顺序表就变为(am,am-1,...,a3,a2,a1)(bn,bn-1,bn-2,...,b3,b2,b1),  然后在对整体做一个倒置,就变为 (b1,b2,b3,...,bn)(a1,a2,a3,...,an)
```c
	bool  reverseListScope(List &list, int left ,int right){
    /*
      这里的left right 都是顺序表的下标 

      实现把  (left,left+1,left+2...right) 变为 (right,...,left+2,left+1,left)  
    */
    if(left>=right || right >=list.length)  return false ;
    int mid = (left+right+1)/2;
    int i;
    for(i=left;i<mid;i++){
        /*
          交换  list.data[i] 和 list.data[right-i+left]
        */
        list.data[i] = list.data[i]^list.data[right-i+left];
        list.data[right-i+left] =  list.data[i]^list.data[right-i+left];
        list.data[i] = list.data[i]^list.data[right-i+left];
    }
    return true;
}
```

```c
void exchangeList(List &list,int m ,int n){

  reverseListScope(list,0,m-1);
  reverseListScope(list,m,m+n-1);
  reverseListScope(list,0,m+n-1);  
}
```

#### 用最短的时间在有序的顺序表中找到元素x,如果找到 ,就让其与与他后面的那个元素交换位置,如果没有找到,就把他插入到合适位置,保持顺序表递增有序

```c
void searchExchangeInsert(List &list,int x){

    int low=0,high = list.length-1,mid; 
    while(low<=high){
     mid = (low+high)/2;
     if(list.data[mid]==x) break;
     if(list.data[mid]<x) low =  mid+1;
     if(list.data[mid]>x) high = mid-1; 
    }
    
    /*
     如果存在 ,且不是 最后一个 ,则与他后面一个位置互换
    */
    if(list.data[mid]==x && mid!= list.length-1){
        //  list.data[mid] 和 list.mid[i+1] 互换 
        list.data[mid] = list.data[mid]^list.data[mid+1];
        list.data[mid+1] = list.data[mid]^list.data[mid+1];
        list.data[mid] = list.data[mid]^list.data[mid+1];
    }
    int i;

    if(low>high){
        for(i=list.length-1;i>high;i--){
            list.data[i+1]=list.data[i];
        }
        list.data[i+1] = x; 
        list.length++;
    }
}
```
#### 用空间和时间复杂度最低的算法,实现顺序表循环左移 n 位
例如 1234 循环左移2位,其实就是 3412,其实前面已经写过了,只是参数不太一样 
我们可以将 12 变为 逆序变为 21,然后 34 逆序变为43,再把整体 2143 逆序,就变为 3412 了

```c
void shiftLeft(List &list,int n){
     
     /*
        将顺序表循环左移 n 位 
        例如 1234 循环左移2位,其实就是 3412 
        其实前面已经写过了 
        我们可以将 12 变为 逆序变为 21,然后 34 逆序变为43,再把整体 2143 逆序,就变为 3412 了  
     */
    //  跟exchangeList 实现的功能一样 
  reverseListScope(list,0,n-1);
  reverseListScope(list,n,list.length-1);
  reverseListScope(list,0,list.length-1);

}
```