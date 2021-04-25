# -*- coding: utf-8 -*-
# flake8: noqa
from qiniu import Auth, put_file, etag, urlsafe_base64_encode
import qiniu.config
import sys
import os
import time
import subprocess

#-----------默认配置-----------
# accessKey和secretkey是七牛的秘钥
access_key = 'G12guvxXe9Kzy3ESSeAdSpiN23jNC-cVqzFzBA5h'
secret_key = 'QtCTewlRAva8NzdaIqzDfVi8e8zYCbs8lbtIVAeh'
# 存储空间
bucket_name = 'wonderkunpic'
# 域名
bucket_url = 'https://pic.wonderkun.cc/'

imageFileDir = "./source/uploads/"

q = Auth(access_key, secret_key)

#上传文件到七牛, 返回链接地址
def upload_data(filePath):

    key = filePath.replace("./source/","")

    # 生成上传 Token，可以指定过期时间等
    token = q.upload_token(bucket_name, key, 3600)
    ret, info = put_file(token, key, filePath)
    return bucket_url + key

def getfilename():
    for root,dirs,files in os.walk(imageFileDir,topdown=False):
        for name in files:
            yield os.path.join(root, name)
            # yield name

if __name__ == '__main__':

    for filePath in getfilename():
        info = upload_data(filePath)
        print("[+] upload file {} success!".format(info))
    