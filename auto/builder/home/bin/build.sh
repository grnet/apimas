#!/bin/sh

set -e

cd /root
mkdir workspace
mkdir build
cd workspace

#if [ "$(id -u)" = "0" ]; then
#    exec su - builder -c "$0 $*"
#fi

export PATH="$(pwd):${PATH}"

if ! [ -d sources ]; then
    mkdir sources
fi

cmd () {
    echo "$@" 1>&2
    "$@"
}

name="$1"
remote="$2"
commit="$3"

if [ -n "${remote}" ]; then
    export BUILD_SOURCE_${name}="${remote} ${commit}"
fi

source_vars=$(set | grep '^BUILD_SOURCE_' | sed -ne 's/^BUILD_SOURCE_\([^=]*\)=\(.*\)$/\1/p')

if [ -z "${source_vars}" ]; then
    echo "No build sources to build."
    exit 1
fi

for source_name in "${source_vars}"; do
    source=$(eval echo ${source_name} \$BUILD_SOURCE_${source_name})

    name=
    remote=
    commit=

    for var in ${source}; do
        if [ -z "${name}" ]; then
            name="sources/${var}"
            name_opt="-p ${name}"
        elif [ -z "${remote}" ]; then
            remote="${var}"
            remote_opt="-r ${remote}"
        elif [ -z "${commit}" ]; then
            commit="${var}"
            commit_opt="-c ${commit}"
        fi
    done

    cmd git_repo.sh ${remote_opt} ${commit_opt} ${name_opt}
    (cmd cd ${name}; cmd mkdeb -b production; cmd cp deb_dist/*deb ../../../build)
done
