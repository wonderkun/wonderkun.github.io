#!/bin/bash 

npm install

hexo g

rm -rf .git

cd ./public

git config user.name 'wonderkun'
git config user.email 'dekunwang2014@gmail.com'

git init 
git add . 
git commit  -m "deploy by hand"
git push -f https://github.com/wonderkun/wonderkun.github.io.git master:master
