#!/bin/sh

set -e
set -x

BASE="${HOME}"
mkdir -p "${BASE}/workspace" || true
mkdir -p "${BASE}/build" || true

export PATH="${BASE}/bin:${PATH}"

if ! [ -d "${BASE}/workspace/sources" ]; then
    if [ -d "${BASE}/sources" ]; then
        cp -r "${BASE}/sources" "${BASE}/workspace/"
    else
        mkdir "${BASE}/workspace/sources"
    fi
fi

cmd () {
    echo "$@" 1>&2
    "$@"
}

name="$1"
remote="$2"
commit="$3"
release_tag="$4"

if [ -n "${remote}" ]; then
    export BUILD_SOURCE_${name}="${remote} ${commit} ${release_tag}"
fi

source_vars=$(set | grep '^BUILD_SOURCE_' | sed -ne 's/^BUILD_SOURCE_\([^=]*\)=\(.*\)$/\1/p')

if [ -z "${source_vars}" ]; then
    echo "No build sources to build."
    exit 1
fi

for source_name in "${source_vars}"; do
    source=$(eval echo ${source_name} \$BUILD_SOURCE_${source_name})

    name=
    name_opt=
    remote=
    remote_opt=
    commit=
    commit_opt=
    release_tag=
    release_tag_opt=

    for var in ${source}; do
        if [ -z "${name}" ]; then
            name="${BASE}/workspace/sources/${var}"
            name_opt="-p ${name}"
        elif [ -z "${remote}" ]; then
            remote="${var}"
            remote_opt="-r ${remote}"
        elif [ -z "${commit}" ]; then
            commit="${var}"
            commit_opt="-c ${commit}"
        elif [ -z "${release_tag}" ]; then
            release_tag="${var}"
            if [ -n "${release_tag}" ]; then
                if [ "${release_tag}" = "%now" ]; then
                    release_tag=$(date --utc -Imin | cut -d+ -f 1 | sed -e 's/[^0-9]/./g')
                fi
                release_tag_opt="-r ${release_tag}"
            fi
        fi
    done

    if [ -d "${name}" ]; then
        if [ "${remote}" = "local+fetch" ]; then
            (cmd cd "${name}"; for git_remote in $(git remote); do cmd git fetch "${git_remote}"; done)
        elif [ "${remote}" != "local" ]; then
            echo "${name} exists yet remote is not either 'local' or 'local+fetch'"
            exit 2
        fi
        (cmd cd "${name}"; cmd git checkout "${commit}")
    else
        cmd git_repo.sh ${remote_opt} ${commit_opt} ${name_opt}
    fi
    (cmd cd "${name}"; cmd mkdeb ${release_tag_opt} -o "${BASE}/build")
done
