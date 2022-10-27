#!/bin/bash

FILE=~/.pylero

[ -f $FILE ] && exit 0

echo "[webservice]
url=https://polarion.example.com/polarion
svn_repo=https://polarion.example.com/repo
user=automation
password=fake_password
default_project=RHELBASEOS
" > $FILE
