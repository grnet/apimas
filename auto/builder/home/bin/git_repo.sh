#!/bin/sh
set -x

help () {
    echo "Usage: $0 [options]"
    echo ''
    echo 'Options:'
    echo '  -h, --help'
    echo '      Print this help message.'
    echo ''
    echo '  -u, --user <user_name_or_id>'
    echo '      Change ownership of all files to this user.'
    echo ''
    echo '  -g, --group <group_name_or_id>'
    echo '      Change ownership of all files to this group.'
    echo ''
    echo '  -p, --path <path_to_clone_repo_at>'
    echo '      Clone repository at this local path.'
    echo ''
    echo '  -r, --remote'
    echo '      Clone this remote repository.'
    echo '      If it is a git+ssh remote -i must also be given.'
    echo ''
    echo '  -c, --commit <commit_or_ref>'
    echo '      After cloning, checkout this commit.'
    echo ''
    echo '  -i, --identity <path_to_ssh_id_file>'
    echo '      Use file at this path as ssh identity key for git+ssh'
    echo ''
}

repo_user=
repo_group=
repo_path=
repo_remote=
repo_commit=
repo_identity=

set -e

while [ -n "$1" ]; do
    opt="$1"
    shift
    case "$opt" in
    -h|--help)
        help; exit 1
    ;;
    -u|--user)
        repo_user="$1"; shift
    ;;
    -g|--group)
        repo_group="$1"; shift
    ;;
    -p|--path)
        repo_path="$1"; shift
    ;;
    -r|--remote)
        repo_remote="$1"; shift
    ;;
    -c|--commit)
        repo_commit="$1"; shift
    ;;
    -i|--identity)
        repo_identity="$1"; shift
    ;;
    *)
        echo "Unexpected argument '${opt}'"
        exit 2
    ;;
    esac
done


if [ -z "${repo_path}" ] || [ -z "${repo_remote}" ]; then
    echo '  -p and -r are both necessary parameters. Try -h.'
    exit 4
fi

now="$(/bin/date -Iseconds)"

set -e

if [ -e "${repo_path}" ]; then
    mv -f "${repo_path}" "${repo_path}-${now}"
fi

if [ -n "${repo_identity}" ]; then
    git_ssh_temp="$(mktemp -p /tmp git-ssh-XXXXXXXX)"
    chmod 700 "${git_ssh_temp}"
    git_ssh_temp_identity="-i '${repo_identity}'"

    cat << EOF > "${git_ssh_temp}"
#!/bin/sh
exec ssh -i '${repo_identity}' "\$@"
EOF
    export GIT_SSH="${git_ssh_temp}"
else
    export GIT_SSH="/usr/bin/ssh"
fi

git clone "${repo_remote}" "${repo_path}"
if [ -n "${repo_identity}" ]; then
    rm "${git_ssh_temp}"
fi

if [ -n "${repo_commit}" ]; then
    (cd "${repo_path}"; git checkout "${repo_commit}")
fi

if [ -n "${repo_user}" ]; then
    chown_group=
    if [ -n "${repo_group}" ]; then
        chown_group=":${repo_group}"
    fi
    chown -R "${repo_user}${chown_group}" "${repo_path}"
    chmod u=rwX,g=wXs,o= -R "${path}"
fi
