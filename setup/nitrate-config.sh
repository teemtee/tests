#!/bin/bash

FILE=~/.nitrate

[ -f $FILE ] && exit 0

echo "[nitrate]
url = https://nitrate.server/xmlrpc/
" > $FILE
