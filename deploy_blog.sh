#!/usr/bin/env bash

# Exit on error
set -e

# $1 is the action: "c" or "d"
# $2 is the issue id

# Validate args
if [ "$#" -ne 2 ]; then
    echo "Usage: deploy_blog.sh <action> <issue_id>"
    exit 1
fi

# Validate action
if [ "$1" != "c" ] && [ "$1" != "d" ]; then
    echo "Invalid action: $1"
    exit 1
fi

# Validate issue id
if ! [[ "$2" =~ ^[0-9]+$ ]]; then
    echo "Invalid issue id: $2"
    exit 1
fi

# if .venv exists, activate it
if [ -f .venv/bin/activate ]; then
    source .venv/bin/activate
fi

# git clone blog repo
work_dir=$(pwd)
tmp_dir=$(mktemp -d -p ${work_dir})
cd $tmp_dir
git clone https://ferstar:${GITHUB_TOKEN}@github.com/ferstar/blog.git --depth 1
echo "Cloned blog repo to $tmp_dir"
cd blog
git config --local user.email "github-actions[bot]@users.noreply.github.com"
git config --local user.name "github-actions[bot]"

if [ "$1" == "c" ]; then
    echo "Creating blog post for issue $2"
    python3 ${work_dir}/convert_issue_to_md.py $2 content/post
    git add content/post/issue-$2.md
    git commit -m "[CI] create article: issue $2"
elif [ "$1" == "d" ]; then
    echo "Deleting blog post for issue $2"
    git rm content/post/issue-$2.md
    git commit -m "[CI] delete article: issue $2"
else
    echo "Invalid action: $1"
    exit 1
fi

git push
echo "Pushed changes to blog repo"
cd $work_dir
rm -rf $tmp_dir
echo "Deleted temp directory $tmp_dir"
