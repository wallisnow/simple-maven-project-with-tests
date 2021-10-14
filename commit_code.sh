#!/bin/bash

git add .
git commit -m "update code $(date)"
git pull --rebase
git push

echo "Done for pushing code"