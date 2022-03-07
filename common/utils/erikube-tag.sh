#!/bin/bash
#REPO_DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )/../../" && pwd -P )
#VERSION_INVENTORY="${REPO_DIR}/build/container-list.json"
## shellcheck disable=SC2002
#ERIKUBE_VERSION="$(cat "${VERSION_INVENTORY}" | jq -r '.erikube_version')"
#commit_changed_erikube_version=$(git blame "${VERSION_INVENTORY}" |grep "\"erikube_version\": \"$ERIKUBE_VERSION\""|awk '{print $1}')
#if [[ "${commit_changed_erikube_version}"x == x ]] || ! git log "${commit_changed_erikube_version}" -1 > /dev/null;then
#  echo "Cannot evaluate the Commit which changed erikube version!"
#  exit 1
#fi
#number_of_commits_since_version_change=$(git log "${commit_changed_erikube_version}".. --pretty=oneline | wc -l | xargs printf %.6d)
#short_git_hash=$(git rev-parse --short=8 HEAD)
#ERIKUBE_TAG="${ERIKUBE_VERSION}-${number_of_commits_since_version_change}-${short_git_hash}"
#export ERIKUBE_TAG

ERIKUBE_TAG="TEST_ERIKUBE_TAG"
export ERIKUBE_TAG


