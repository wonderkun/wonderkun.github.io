---
title: 010editor 模板编写笔记
url: 761.html
id: 761
categories:
  - 学习记录
date: 2024-11-12 16:16:34
tags:
  - binary
  - blue & red
---


# 010editor 模板编写

参考文档：
https://www.sweetscape.com/010editor/manual/IntroTemplates.htm

https://bbs.pediy.com/thread-257797.htm

https://lyana-nullptr.github.io/2024/07/27/try-the-template-of-010editor/

## 变量

模板文件的开头会有如下信息：
```
//      File: 
//   Authors: 
//   Version: 
//   Purpose: 
//  Category: WeChat
// File Mask: *.wxapkg
//  ID Bytes: BE, 56 31 4D 4D 57 58
//   History: 
```
程序会优先用File Mask匹配文件扩展名，再用ID Bytes匹配魔术数，匹配成功的话就会自动加载模板文件。

<!-- more -->
默认情况下，所有变量都会显示在模板窗口中。比如：
```c
struct test{
   int x;
   int y;    
};

int x <bgcolor=0x0000FF,format=hex>;

test a <bgcolor=0x00FFFF>;
```
![](https://pic.wonderkun.cc//uploads/note/202411141132637.png)

可以通过local关键字定义变量，这样的变量默认不会显示在模板窗口中，不过用户任然可以在窗口中点击右键菜单中的Show Local Variables来显示局部变量。

```
// 该模板中定义了变量 a, b, c, d, e, f, g
// 枚举的变量类型为 “enum ENUM1 { COMP_1 = 1, COMP_2 = 2, COMP_3 = 3 }” 整体，结构体同理
int a;
float b;
double c;
string d;
int e[4];
enum ENUM1 { COMP_1 = 1, COMP_2 = 2, COMP_3 = 3 } f;
struct STRUCT1 { int x; int y; int z; } g;
```
重复定义同名的变量将被视作定义一个数组变量，也可以通过循环语句和定义变量语句组合实现。如：
```
// 方法 1，显示为：
// Name    Value   Start   Size    Type    Color   Comment
// a[0]    ...     0h      4h      int
// a[1]    ...     4h      4h      int
// a[2]    ...     8h      4h      int
int a[3]

// 方法 2，效果相同
int a;
int a;
int a;

// 方法 3，效果相同
local int i;
for (i = 0; i < 4; i++)
{
  int a;
}
```

变量属性

```c
  < format=hex|decimal|octal|binary,
     fgcolor=<color>|<function>|(<expression>),
     bgcolor=<color>|<function>|(<expression>),
     style=<style_name>,
     comment="<string>"|<function>|(<expression>),
     name="<string>"|<function>|(<expression>),
     open=true|false|suppress,
     hidden=true|false,
     read=<function>|(<expression>),
     write=<function>|(<expression>),
     size=<number>|<function>|(<expression>),
     optimize=true|false,
     disasm=<constant>|<function>|(<expression>) >
```

format: 以某种进制格式显示，默认为十进制，显示在 Vlaue 栏
fgcolor: 设置字体色
bgcolor: 设置背景色
comment: 添加注释，显示在 Comment 栏
name: 替换显示的字符，默认为结构体中的变量名，显示在 Name 栏
open: 设置树形图是否展开，默认不展开
hidden: 设置是否隐藏，默认为不隐藏
read: 读回调，返回字符串并显示在 Vlaue 栏
write: 写回调，将读回调返回的字符写入结构体某个字段中
size: 按需执行，可节约系统内存

一些颜色值 ：

```
cBlack - 0x000000
cRed - 0x0000ff
cDkRed - 0x000080
cLtRed - 0x8080ff
cGreen - 0x00ff00
cDkGreen - 0x008000
cLtGreen - 0x80ff80
cBlue - 0xff0000
cDkBlue - 0x800000
cLtBlue - 0xff8080
cPurple - 0xff00ff
cDkPurple - 0x800080
cLtPurple - 0xffe0ff
cAqua - 0xffff00
cDkAqua - 0x808000
cLtAqua - 0xffffe0
cYellow - 0x00ffff
cDkYellow - 0x008080
cLtYellow - 0x80ffff
cDkGray - 0x404040
cGray - 0x808080,
cSilver - 0xc0c0c0,
cLtGray - 0xe0e0e0
cWhite - 0xffffff
cNone - 0xffffffff
```


帮助大伙更好的理解以上这几个特殊的属性，图 1 中的 1 处是 name 属性显示的字符，如果不指定 name 属性默认就是结构体中的变量名。2 处是 format 属性，默认是十进制，这里指定为 16 进制。3 处是背景颜色和字体颜色缩影，这里没设置颜色所以显示为空。4 处就是 comment 属性显示的位置。

![](https://pic.wonderkun.cc//uploads/note/202411141241455.png)


## 数据类型

8字节 char byte CHAR BYTE uchar ubyte UCHAR UBYTE
16字节 short int16 SHORT INT16 ushort uint16 USHORT UINT16 WORD
32字节 int int32 long INT INT32 LONG uint uint32 ulong UINT UINT32 ULONG DWORD
64字节 int64 quad QUAD INT64 __int64 uint64 uquad UQUAD UINT64 __uint64 QWORD
浮点 float FLOAT double DOUBLE hfloat HFLOAT
其他 DOSDATE DOSTIME FILETIME OLETIME time_t


使用:

```
enum MYENUM { COMP_1, COMP_2 = 5, COMP_3 } var1;
enum <ushort> MYENUM { COMP_1, COMP_2 = 5, COMP_3 } var1;

int myArray[15];
int myArray[ FileSize() - myInt * 0x10 + (17 << 5) ];//大小可以是变量

char str[15] = "First";  
string s = "Second";  
string r1 = str + s;  
string r2 = str;  
r2 += s;  
return (r1 == r2);  


// 宽字符

wchar_t str1[15] = L"How now";  
wstring str2 = "brown cow";  
wstring str3 = str1 + L' ' + str2 + L'?'

```

### 控制语句和函数

支持 for,if,while,switch

函数参数可以通过值或引用传递，010editor脚本不支持指针，但是可以用[]表示数组
程序中不需要main函数，代码从第一行开始执行
 
### 关键字

sizeof
startof 用于计算变量起始地址
```
         SetCursorPos( startof( lines[0] ) );
```
exists 检查某变量是否声明

```
    int i;  
    string s;  
    while( exists( file[i] ) )  
    {  
    s = file[i].frFileName;  
    Printf( "%s\n", s );  
    i++;  
    }  
```
function_exists 检查函数是否定义

```
    if( function_exists(CopyStringToClipboard) )  
    {  
    ...  
    }  
```

this 引用当前结构体

```
    void PrintHeader( struct HEADER &h )  
    {  
    Printf( "ID1 = %d\n", h.ID1 );  
    Printf( "ID2 = %d\n", h.ID2 );  
    }  
    struct HEADER  
    {  
    int ID1;  
    int ID2;  
    PrintHeader( this );  
    } h1;  
```

parentof 访问包含变量的结构和union

```
    void PrintHeader( struct HEADER &h )  
    {  
    Printf( "ID1 = %d\n", h.ID1 );  
    Printf( "ID2 = %d\n", h.ID2 );  
    }  
    struct HEADER  
    {  
    int ID1;  
    int ID2;  
    struct SUBITEM  
    {  
    int data1;  
    int data2;  
    PrintHeader( parentof(this) );  
    } item1;  
    PrintHeader( parentof(item1) );  
    } h1;  
```



## 大小端以及其他设置

默认随系统，比如在 Windows 下是按照小端模式，通过BigEndian和LittleEndian来调整读取方式。

```
BigEndian();    // 转换为大端模式
int x;
LittleEndian(); // 转换为小端模式
```

- color设置

```
    int id <fgcolor=cBlack, bgcolor=0x0000FF>;  
    SetForeColor( cRed );  
    int first; // will be colored red  
    int second; // will be colored red  
    SetForeColor( cNone );  
    int third; // will not be colored  
```


## 脚本终止

如果在执行过程中发现脚本结构不对时可以提前结束，使用return语句即可，我们把整个脚本文件看作是一个C函数，用return就可以提前退出函数。
```
local string magic = ReadString(0, 5);
if (magic == "Hello") {
  Printf("无法解析加密文件");
  return;
}
```

## 结构体扩展

### 结构体构造函数

```
typedef struct (uint offset) {
  uint x;
} FILE;
```
使用方法：
```
FILE f(123);
```

### 结构体表达式

有时候结构体不是固定长度，而是根据字段的值来决定的
```
typedef struct {
  FILE_NAME fileName;
  uint offset;
  uint size;
  
  if (size > 0) {
    local int64 pos = FTell();
    FSeek(offset);
    uchar data[size];
    FSeek(pos);
  }
} FILE_INFO <comment=fileName.fileName>;
```

甚至可以直接按照下面写法：

```
typedef struct {
    unsigned char length;       // 读取长度字段（4 字节）
    local unsigned int c = length +1;
    char data[c];   // 读取长度为 length 的字符串
} MyData;

// 实例化结构，以便解析文件
MyData myData;
```

## 当前地址

当前地址是下一个被定义变量的起始地址，初始为 0h，每定义一个变量，当前地址将会后移该变量的大小（通常用十六进制表示）

FTell() 函数用于获取当前地址，FSeek() 函数用于修改当前地址，FSkip() 函数用于移动当前地址，使用这些函数的组合
可以实现不按序读取数据。

使用 ReadInt()、ReadByte() 等读取函数配合 FTell() 等函数可以从当前地址开始读取一段符合类型的值,这几个函数不会影响当前地址，常在条件语句中
用作判断，例如：

```
// 从当前地址开始读取一段 int 值，且这个值为 1 时，将会定义结构体变量 opt1，类型为 OPTION1
// 否则将会定义结构体变量 opt2，类型为 OPTION2
struct OPTION1 { int tag; uchar data[8]; };
struct OPTION2 { int tag; uint64 data; };
if( ReadInt( FTell() ) == 1 )
    struct OPTION1 opt1;
else
    struct OPTION2 opt2;
```

## 常用api

```
void BigEndian()
void LittleEndian()
char ReadByte(int64 pos=FTell())
uchar ReadUByte(int64 pos=FTell())
short ReadShort(int64 pos=FTell())
ushort ReadUShort(int64 pos=FTell())
int ReadInt(int64 pos=FTell())
uint ReadUInt(int64 pos=FTell())
int64 ReadInt64(int64 pos=FTell())
uint64 ReadUInt64(int64 pos=FTell())
void ReadBytes(uchar buffer[], int64 pos, int n)
char[] ReadString(int64 pos, int maxLen=-1)
int ReadStringLength(int64 pos, int maxLen=-1)
wstring ReadWString(int64 pos, int maxLen=-1)
int ReadWStringLength(int64 pos, int maxLen=-1)
void WriteByte(int64 pos, char value)
int FSeek(int64 pos)
int FSkip(int64 offset)
int64 FTell()
int FEof()
void Strcpy(char dest[], const char src[])
void Strcat(char dest[], const char src[])
int Strchr(const char s[], char c)
int Strcmp(const char s1[], const char s2[])
int Printf(const char format[] [, argument, ... ])
int SScanf(char str[], char format[], ...)
int SPrintf(char buffer[], const char format[] [, argument, ... ])
```

io函数

```
 void BigEndian()//设置大小头端  
int IsBigEndian()  
int IsLittleEndian()  
void LittleEndian()  
  
double ConvertBytesToDouble( uchar byteArray[] ) //数据转换  
float ConvertBytesToFloat( uchar byteArray[] )   
hfloat ConvertBytesToHFloat( uchar byteArray[] )  
int ConvertDataToBytes( data_type value, uchar byteArray[] )  
void DeleteBytes( int64 start, int64 size )//删除数据  
void InsertBytes( int64 start, int64 size, uchar value=0 )//插入数据  
void OverwriteBytes( int64 start, int64 size, uchar value=0 )  
  
char ReadByte( int64 pos=FTell() ) //读取数据  
double ReadDouble( int64 pos=FTell() )   
float ReadFloat( int64 pos=FTell() )   
hfloat ReadHFloat( int64 pos=FTell() )   
int ReadInt( int64 pos=FTell() )   
int64 ReadInt64( int64 pos=FTell() )   
int64 ReadQuad( int64 pos=FTell() )   
short ReadShort( int64 pos=FTell() )  
uchar ReadUByte( int64 pos=FTell() )   
uint ReadUInt( int64 pos=FTell() )   
uint64 ReadUInt64( int64 pos=FTell() )   
uint64 ReadUQuad( int64 pos=FTell() )   
ushort ReadUShort( int64 pos=FTell() )  
void ReadBytes( uchar buffer[], int64 pos, int n )  
char[] ReadString( int64 pos, int maxLen=-1 )  
int ReadStringLength( int64 pos, int maxLen=-1 )  
wstring ReadWString( int64 pos, int maxLen=-1 )  
int ReadWStringLength( int64 pos, int maxLen=-1 )  
wstring ReadWLine( int64 pos, int maxLen=-1 )  
char[] ReadLine( int64 pos, int maxLen=-1, int includeLinefeeds=true )  
  
void WriteByte( int64 pos, char value ) //写入数据  
void WriteDouble( int64 pos, double value )   
void WriteFloat( int64 pos, float value )   
void WriteHFloat( int64 pos, float value )   
void WriteInt( int64 pos, int value )   
void WriteInt64( int64 pos, int64 value )   
void WriteQuad( int64 pos, int64 value )   
void WriteShort( int64 pos, short value )   
void WriteUByte( int64 pos, uchar value )   
void WriteUInt( int64 pos, uint value )   
void WriteUInt64( int64 pos, uint64 value )   
void WriteUQuad( int64 pos, uint64 value )   
void WriteUShort( int64 pos, ushort value )  
void WriteBytes( const uchar buffer[], int64 pos, int n )  
void WriteString( int64 pos, const char value[] )  
void WriteWString( int64 pos, const wstring value )  
  
int DirectoryExists( string dir )  
int MakeDir( string dir )  
int FEof()  
int64 FileSize()  
TFileList FindFiles( string dir, string filter )  
    TFileList fl = FindFiles( "C:\\temp\\", "*.zip" );  
    int i;  
    Printf( "Num files = %d\n", fl.filecount );  
    for( i = 0; i < fl.filecount; i++ )  
    {  
    Printf( " %s\n", fl.file[i].filename );  
    }  
    Printf( "\n" );  
    Printf( "Num dirs = %d\n", fl.dircount );  
    for( i = 0; i < fl.dircount; i++ )  
    {  
    Printf( " %s\n", fl.dir[i].dirname );  
    }  
int FPrintf( int fileNum, char format[], ... )  
int FSeek( int64 pos )  
int FSkip( int64 offset )  
int64 FTell()  
  
int64 TextAddressToLine( int64 address )  
int TextAddressToColumn( int64 address )  
int64 TextColumnToAddress( int64 line, int column )  
int64 TextGetNumLines()  
int TextGetLineSize( int64 line, int includeLinefeeds=true )  
int64 TextLineToAddress( int64 line )  
int TextReadLine( char buffer[], int64 line, int maxsize, int includeLinefeeds=true )  
int TextReadLineW( wchar_t buffer[], int64 line, int maxsize, int includeLinefeeds=true )  
void TextWriteLineW( const wchar_t buffer[], int64 line, int includeLinefeeds=true )  
void TextWriteLine( const char buffer[], int64 line, int includeLinefeeds=true ) 

```

其他函数

```
    //书签  
    void AddBookmark( int64 pos, string name, string typename, int arraySize=-1, int forecolor=cNone, int backcolor=0xffffc4, int moveWithCursor=false )  
    AddBookmark( GetCursorPos(), "endmarker","ZIPENDLOCATOR", -1, cRed );  
    int GetBookmarkArraySize( int index )  
    int GetBookmarkBackColor( int index )  
    int GetBookmarkForeColor( int index )  
    int GetBookmarkMoveWithCursor( int index )  
    string GetBookmarkName( int index )  
    int64 GetBookmarkPos( int index )  
    string GetBookmarkType( int index )  
    int GetNumBookmarks()  
    void RemoveBookmark( int index )  
    //断言  
    void Assert( int value, const char msg[] = "" )  
    Assert( numRecords > 10,"numRecords should be more than 10." );  
    //剪贴板  
    void ClearClipboard()  
    void CopyBytesToClipboard( uchar buffer[], int size, int charset=CHARSET_ANSI, int bigendian=false )  
    void CopyStringToClipboard( const char str[], int charset=CHARSET_ANSI )  
    void CopyToClipboard()  
    void CutToClipboard()  
    int GetClipboardBytes( uchar buffer[], int maxBytes )  
    int GetClipboardIndex()  
    string GetClipboardString()  
    void PasteFromClipboard()  
    int SetClipboardIndex( int index )  
      
    文件  
    int DeleteFile( char filename[] )    //删除文件，文件不能在编辑器中打开  
    void FileClose()//关闭当前文件  
    int FileCount()//获取editor打开的文件数  
    int FileExists( const char filename[] )//检测文件存在  
    int FileNew( char interface[]="", int makeActive=true )//创建爱你文件  
    int FileOpen( const char filename[], int runTemplate=false, char interface[]="", int openDuplicate=false )//打开文件  
    int FileSave()   
    int FileSave( const char filename[] )   
    int FileSave( const wchar_t filename[] )   
    int FileSaveRange( const char filename[], int64 start, int64 size )   
    int FileSaveRange( const wchar_t filename[], int64 start, int64 size )//保存文件  
    void FileSelect( int index )//选择读写的文件  
    int FindOpenFile( const char path[] )   
    int FindOpenFileW( const wchar_t path[] )//查找并打开文件  
    int GetFileAttributesUnix()  
    int GetFileAttributesWin()  
    int SetFileAttributesUnix( int attributes )  
    int SetFileAttributesWin( int attributes )  
    int GetFileCharSet()  
    char[] GetFileInterface()  
    int SetFileInterface( const char name[] )  
    char[] GetFileName()  
    wchar_t[] GetFileNameW()  
    int GetFileNum()  
    int GetReadOnly()  
    int SetReadOnly( int readonly )  
    string GetTempDirectory()  
    char[] GetTempFileName()  
    char[] GetTemplateName()   
    wchar_t[] GetTemplateNameW()  
    char[] GetTemplateFileName()   
    wchar_t[] GetTemplateFileNameW()  
    char[] GetScriptName()   
    wchar_t[] GetScriptNameW()  
    char[] GetScriptFileName()   
    wchar_t[] GetScriptFileNameW()  
    char[] GetWorkingDirectory()   
    wchar_t[] GetWorkingDirectoryW()  
    int RenameFile( const char originalname[], const char newname[] )  
    void RequiresFile()  
    void RequiresVersion( int majorVer, int minorVer=0, int revision=0 )  
    void RunTemplate( const char filename[]="", int clearOutput=false )  
    int SetWorkingDirectory( const char dir[] )   
    int SetWorkingDirectoryW( const wchar_t dir[] )  
      
    //输入  
    char[] InputDirectory( const char title[], const char defaultDir[]="" )  
    double InputFloat( const char title[], const char caption[], const char defaultValue[] )  
    int InputNumber( const char title[], const char caption[], const char defaultValue[] )  
    char[] InputOpenFileName( char title[], char filter[]="All files (*.*)", char filename[]="" )  
    TOpenFileNames InputOpenFileNames( char title[], char filter[]="All files (*.*)", char filename[]="" )  
        int i;  
        TOpenFileNames f = InputOpenFileNames(  
        "Open File Test",  
        "C Files (*.c *.cpp)|All Files (*.*)" );  
        for( i = 0; i < f.count; i++ )  
        Printf( "%s\n", f.file[i].filename );  
    int InputRadioButtonBox( const char title[], const char caption[], int defaultIndex, const char str1[], const char str2[], const char str3[]="", const char str4[]="", const char str5[]="", const char str6[]="", const char str7[]="", const char str8[]="", const char str9[]="", const char str10[]="", const char str11[]="", const char str12[]="", const char str13[]="", const char str14[]="", const char str15[]="" )  
    char[] InputSaveFileName( char title[], char filter[]="All files (*.*)", char filename[]="", char extension[]="" )  
    char[] InputString( const char title[], const char caption[], const char defaultValue[] )  
    wstring InputWString( const char title[], const char caption[], const wstring defaultValue )  
    int InsertFile( const char filename[], int64 position )  
    int IsEditorFocused()  
    int IsModified()  
    int IsNoUIMode()  
    int MessageBox( int mask, const char title[], const char format[] [, argument, ... ] )  
    void OutputPaneClear()  
    int OutputPaneSave( const char filename[] )  
    void OutputPaneCopy()  
    int Printf( const char format[] [, argument, ... ] )  
        Printf( "Num = %d, Float = %lf, Str = '%s'\n", 15, 5, "Test" );  
    void StatusMessage( const char format[] [, argument, ... ] )  
      
      
    int64 GetSelSize()  
    int64 GetSelStart()  
    void SetSelection( int64 start, int64 size )  
      
    //颜色  
    int GetForeColor()  
    int GetBackColor()  
    void SetBackColor( int color )   
    void SetColor( int forecolor, int backcolor )   
    void SetForeColor( int color )  
      
    int GetBytesPerLine()//获取显示列数  
      
    //时间  
    string GetCurrentTime( char format[] = "hh:mm:ss" )  
    string GetCurrentDate( char format[] = "MM/dd/yyyy" )  
    string GetCurrentDateTime( char format[] = "MM/dd/yyyy hh:mm:ss" )  
      
    void DisableUndo()//禁止undo  
    void EnableUndo()//允许undo  
      
    //设置显示值  
    void DisplayFormatBinary()   
    void DisplayFormatDecimal()   
    void DisplayFormatHex()   
    void DisplayFormatOctal()  
      
    int Exec( const char program[], const char arguments[], int wait=false ) int Exec( const char program[], const char arguments[], int wait, int &errorCode )  
    void Exit( int errorcode )  
    void Warning( const char format[] [, argument, ... ] )  
    void Terminate( int force=true )  
    char[] GetArg( int index ) wchar_t[] GetArgW( int index )//获取传递给脚本的命令  
    char[] GetEnv( const char str[] )//获取环境变量  
    int SetEnv( const char str[], const char value[] )  
    int GetNumArgs()  
      
    void ExpandAll()//展开节点  
    void ExportCSV( const char filename[] )//导出  
    void ExportXML( const char filename[] )//导出  
      
    int64 GetCursorPos()//获取当前指针  
    void SetCursorPos( int64 pos )  
    void Sleep( int milliseconds )  
```

字符串函数

```
 //类型转换  
double Atof( const char s[] )  
int Atoi( const char s[] )  
int64 BinaryStrToInt( const char s[] )  
    return BinaryStrToInt( "01001101" );  
char[] ConvertString( const char src[], int srcCharSet, int destCharSet )  
    CHARSET_ASCII CHARSET_ANSI CHARSET_OEM CHARSET_EBCDIC CHARSET_UNICODE CHARSET_MAC CHARSET_ARABIC CHARSET_BALTIC CHARSET_CHINESE_S CHARSET_CHINESE_T CHARSET_CYRILLIC CHARSET_EASTEUROPE CHARSET_GREEK CHARSET_HEBREW CHARSET_JAPANESE CHARSET_KOREAN_J CHARSET_KOREAN_W CHARSET_THAI CHARSET_TURKISH CHARSET_VIETNAMESE CHARSET_UTF8  
string DosDateToString( DOSDATE d, char format[] = "MM/dd/yyyy" )  
string DosTimeToString( DOSTIME t, char format[] = "hh:mm:ss" )  
string EnumToString( enum e )  
string FileTimeToString( FILETIME ft, char format[] = "MM/dd/yyyy hh:mm:ss" )  
    int hour, minute, second, day, month, year;  
    string s = FileTimeToString( ft );  
    SScanf( s, "%02d/%02d/%04d %02d:%02d:%02d",  
    month, day, year, hour, minute, second );  
    year++;  
    SPrintf( s, "%02d/%02d/%04d %02d:%02d:%02d",  
    month, day, year, hour, minute, second );  
int StringToDosDate( string s, DOSDATE &d, char format[] = "MM/dd/yyyy" )  
int StringToDosTime( string s, DOSTIME &t, char format[] = "hh:mm:ss" )  
int StringToFileTime( string s, FILETIME &ft, char format[] = "MM/dd/yyyy hh:mm:ss" )  
int StringToOleTime( string s, OLETIME &ot, char format[] = "MM/dd/yyyy hh:mm:ss" )  
int StringToTimeT( string s, time_t &t, char format[] = "MM/dd/yyyy hh:mm:ss" )  
char[] StringToUTF8( const char src[], int srcCharSet=CHARSET_ANSI )  
wstring StringToWString( const char str[], int srcCharSet=CHARSET_ANSI )  
  
//内存操作  
int Memcmp( const uchar s1[], const uchar s2[], int n )  
void Memcpy( uchar dest[], const uchar src[], int n, int destOffset=0, int srcOffset=0 )  
void Memset( uchar s[], int c, int n )  
string OleTimeToString( OLETIME ot, char format[] = "MM/dd/yyyy hh:mm:ss" )  
int RegExMatch( string str, string regex ); //正则匹配  
int RegExMatchW( wstring str, wstring regex );  
int RegExSearch( string str, string regex, int &matchSize, int startPos=0 );   
int RegExSearchW( wstring str, wstring regex, int &matchSize, int startPos=0 );  
    if( RegExMatch( "test@test.ca",  
    "\\b[A-Za-z0-9.%_+\\-]+@[A-Za-z0-9.\\-]+\\.[A-Za-z]{2,4}\\b" )  
    == false )  
    {  
    Warning( "Invalid email address" );  
    return -1;  
    }  
    int result, size;  
    result = RegExSearch(  
    "12:03:23 AM - 192.168.0.10 : www.sweetscape.com/",  
    "\\d{1,3}\\.\\d{1,3}.\\d{1,3}.\\d{1,3}", size );  
    Printf( "Match at pos %d of size %d\n", result, size );  
void Strcat( char dest[], const char src[] )  
int Strchr( const char s[], char c )  
int Strcmp( const char s1[], const char s2[] )   
void Strcpy( char dest[], const char src[] )  
char[] StrDel( const char str[], int start, int count )   
int Stricmp( const char s1[], const char s2[] )  
int Strlen( const char s[] )  
int Strncmp( const char s1[], const char s2[], int n )  
void Strncpy( char dest[], const char src[], int n )   
int Strnicmp( const char s1[], const char s2[], int n )  
int Strstr( const char s1[], const char s2[] )  
char[] SubStr( const char str[], int start, int count=-1 )  
string TimeTToString( time_t t, char format[] = "MM/dd/yyyy hh:mm:ss" )  
char ToLower( char c ) wchar_t ToLowerW( wchar_t c )  
char ToUpper( char c ) wchar_t ToUpperW( wchar_t c )  
void WMemcmp( const wchar_t s1[], const wchar_t s2[], int n )  
void WMemcpy( wchar_t dest[], const wchar_t src[], int n, int destOffset=0, int srcOffset=0 )  
void WMemset( wchar_t s[], int c, int n )  
void WStrcat( wchar_t dest[], const wchar_t src[] )  
int WStrchr( const wchar_t s[], wchar_t c )  
int WStrcmp( const wchar_t s1[], const wchar_t s2[] )  
void WStrcpy( wchar_t dest[], const wchar_t src[] )  
wchar_t[] WStrDel( const whar_t str[], int start, int count )   
int WStricmp( const wchar_t s1[], const wchar_t s2[] )  
char[] WStringToString( const wchar_t str[], int destCharSet=CHARSET_ANSI )  
char[] WStringToUTF8( const wchar_t str[] )  
int WStrlen( const wchar_t s[] )  
int WStrncmp( const wchar_t s1[], const wchar_t s2[], int n )  
void WStrncpy( wchar_t dest[], const wchar_t src[], int n )  
int WStrnicmp( const wchar_t s1[], const wchar_t s2[], int n )   
int WStrstr( const wchar_t s1[], const wchar_t s2[] )  
wchar_t[] WSubStr( const wchar_t str[], int start, int count=-1 )  
  
char[] FileNameGetBase( const char path[], int includeExtension=true ) //获取文件名  
wchar_t[] FileNameGetBaseW( const wchar_t path[], int includeExtension=true )  
char[] FileNameGetExtension( const char path[] )   
wchar_t[] FileNameGetExtensionW( const wchar_t path[] )  
char[] FileNameGetPath( const char path[], int includeSlash=true )   
wchar_t[] FileNameGetPathW( const wchar_t path[], int includeSlash=true )  
char[] FileNameSetExtension( const char path[], const char extension[] )   
wchar_t[] FileNameSetExtensionW( const wchar_t path[], const wchar_t extension[] )   
  
//格式化字符串  
int SPrintf( char buffer[], const char format[] [, argument, ... ] )  
int SScanf( char str[], char format[], ... ) 
```

工具函数

```
    //计算校验和  
    int64 Checksum( int algorithm, int64 start=0, int64 size=0, int64 crcPolynomial=-1, int64 crcInitValue=-1 )  
        CHECKSUM_BYTE CHECKSUM_SHORT_LE CHECKSUM_SHORT_BE CHECKSUM_INT_LE CHECKSUM_INT_BE CHECKSUM_INT64_LE CHECKSUM_INT64_BE CHECKSUM_SUM8 CHECKSUM_SUM16 CHECKSUM_SUM32 CHECKSUM_SUM64 CHECKSUM_CRC16 CHECKSUM_CRCCCITT CHECKSUM_CRC32 CHECKSUM_ADLER32  
    int ChecksumAlgArrayStr( int algorithm, char result[], uchar *buffer, int64 size, char ignore[]="", int64 crcPolynomial=-1, int64 crcInitValue=-1 )  
    int ChecksumAlgArrayBytes( int algorithm, uchar result[], uchar *buffer, int64 size, char ignore[]="", int64 crcPolynomial=-1, int64 crcInitValue=-1 )  
    int ChecksumAlgStr( int algorithm, char result[], int64 start=0, int64 size=0, char ignore[]="", int64 crcPolynomial=-1, int64 crcInitValue=-1 )  
    int ChecksumAlgBytes( int algorithm, uchar result[], int64 start=0, int64 size=0, char ignore[]="", int64 crcPolynomial=-1, int64 crcInitValue=-1 )  
      
    //查找比较  
    TCompareResults Compare( int type, int fileNumA, int fileNumB, int64 startA=0, int64 sizeA=0, int64 startB=0, int64 sizeB=0, int matchcase=true, int64 maxlookahead=10000, int64 minmatchlength=8, int64 quickmatch=512 )  
        int i, f1, f2;  
        FileOpen( "C:\\temp\\test1" );  
        f1 = GetFileNum();  
        FileOpen( "C:\\temp\\test2" );  
        f2 = GetFileNum();  
        TCompareResults r = Compare( COMPARE_SYNCHRONIZE, f1, f2 );  
        for( i = 0; i < r.count; i++ )  
        {  
        Printf( "%d %Ld %Ld %Ld %Ld\n",  
        r.record[i].type,  
        r.record[i].startA,  
        r.record[i].sizeA,  
        r.record[i].startB,  
        r.record[i].sizeB );  
        }  
    TFindResults FindAll( <datatype> data, int matchcase=true, int wholeword=false, int method=0, double tolerance=0.0, int dir=1, int64 start=0, int64 size=0, int wildcardMatchLength=24 )  
        int i;  
        TFindResults r = FindAll( "Test" );  
        Printf( "%d\n", r.count );  
        for( i = 0; i < r.count; i++ )  
        Printf( "%Ld %Ld\n", r.start[i], r.size[i] );  
    int64 FindFirst( <datatype> data, int matchcase=true, int wholeword=false, int method=0, double tolerance=0.0, int dir=1, int64 start=0, int64 size=0, int wildcardMatchLength=24 )  
    TFindInFilesResults FindInFiles( <datatype> data, char dir[], char mask[], int subdirs=true, int openfiles=false, int matchcase=true, int wholeword=false, int method=0, double tolerance=0.0, int wildcardMatchLength=24 )  
        int i, j;  
        TFindInFilesResults r = FindInFiles( "PK",  
        "C:\\temp", "*.zip" );  
        Printf( "%d\n", r.count );  
        for( i = 0; i < r.count; i++ )  
        {  
        Printf( " %s\n", r.file[i].filename );  
        Printf( " %d\n", r.file[i].count );  
        for( j = 0; j < r.file[i].count; j++ )  
        Printf( " %Ld %Ld\n",  
        r.file[i].start[j],  
        r.file[i].size[j] );  
        }  
    int64 FindNext( int dir=1 )  
    TFindStringsResults FindStrings( int minStringLength, int type, int matchingCharTypes, wstring customChars="", int64 start=0, int64 size=0, int requireNull=false )  
        TFindStringsResults r = FindStrings( 5, FINDSTRING_ASCII,  
        FINDSTRING_LETTERS | FINDSTRING_CUSTOM, "$&" );  
        Printf( "%d\n", r.count );  
        for( i = 0; i < r.count; i++ )  
        Printf( "%Ld %Ld %d\n", r.start[i], r.size[i], r.type[i] );  
          
    //类型转换  
    char ConvertASCIIToEBCDIC( char ascii )  
    void ConvertASCIIToUNICODE( int len, const char ascii[], ubyte unicode[], int bigendian=false )  
    void ConvertASCIIToUNICODEW( int len, const char ascii[], ushort unicode[] )   
    char ConvertEBCDICToASCII( char ebcdic )  
    void ConvertUNICODEToASCII( int len, const ubyte unicode[], char ascii[], int bigendian=false )  
    void ConvertUNICODEToASCIIW( int len, const ushort unicode[], char ascii[] )  
      
    int ExportFile( int type, char filename[], int64 start=0, int64 size=0, int64 startaddress=0,int bytesperrow=16, int wordaddresses=0 )  
    int ImportFile( int type, char filename[], int wordaddresses=false, int defaultByteValue=-1 )  
    int GetSectorSize()   
    int HexOperation( int operation, int64 start, int64 size, operand, step=0, int64 skip=0 )  
    int64 Histogram( int64 start, int64 size, int64 result[256] )  
    int IsDrive()  
    int IsLogicalDrive()  
    int IsPhysicalDrive()  
    int IsProcess()  
    int OpenLogicalDrive( char driveletter )  
    int OpenPhysicalDrive( int physicalID )  
    int OpenProcessById( int processID, int openwriteable=true )  
    int OpenProcessByName( char processname[], int openwriteable=true )  
    int ReplaceAll( <datatype> finddata, <datatype> replacedata, int matchcase=true, int wholeword=false, int method=0, double tolerance=0.0, int dir=1, int64 start=0, int64 size=0, int padwithzeros=false, int wildcardMatchLength=24 )  

```

特别需要注意的是以下几个函数，对于解析偏移后的动态数据它们是不可或缺的：

FEof 判断当前读取位置是否在文件末尾
FTell 返回文件的当前读取位置
FSeek 将当前读取位置设置为指定地址
FSkip 将当前读取位置向前移动多个字节
