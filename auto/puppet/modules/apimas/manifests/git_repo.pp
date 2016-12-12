define apimas::git_repo ($user, $group, $path, $remote, $commit, $ssh_identity) {
    $identity_path = "${path}.identity"
    $git_ssh_path = "${path}.git_ssh"

    $now = generate('/bin/date', '-Iseconds')

    exec { "move-git-${path}":
        command => "/bin/mv -f ${path} ${path}-${now}",
        cwd => '/',
        onlyif => "/usr/bin/test -e '${path}'",
        umask => "0222",
    }

    file { $path:
        ensure => directory,
        purge => true,
        force => true,
        owner => $user,
        group => $group,
        mode => '0750',
        require => Exec["move-git-${path}"],
    }

    file { $identity_path:
        ensure => file,
        purge => true,
        force => true,
        owner => $user,
        group => $group,
        mode => '0600',
        content => $ssh_identity,
    }

    file { $git_ssh_path:
        ensure => file,
        purge => true,
        force => true,
        owner => $user,
        group => $group,
        mode => '0500',
        require => File[$identity_path],
        content => "#!/bin/sh\n/usr/bin/ssh -i \"${identity_path}\" \"$@\"\n",
    }

    exec { "git_repo_clone-${path}":
        command => "/usr/bin/git clone ${remote} ${path}",
        cwd => '/',
        creates => "${path}/.git",
        require => [Package['git'], File[$git_ssh_path]],
        environment => ["GIT_SSH=${git_ssh_path}"],
        umask => "0222",
    }

    exec { "git_repo_fetch-${path}":
        command => "/usr/bin/git fetch origin",
        cwd => $path,
        require => Exec["git_repo_clone-${path}"],
        environment => ["GIT_SSH=${git_ssh_path}"],
        umask => "0222",
    }

    exec { "git_repo_checkout-${path}":
        command => "/usr/bin/git checkout ${commit}",
        cwd => $path,
        umask => "0222",
        require => Exec["git_repo_fetch-${path}"],
        notify => Exec["git_repo_chown-${path}"],
    }

    exec { "git_repo_chown-${path}":
        command => "/bin/chown -R ${user} ${path}",
        notify => Exec["git_repo_chgrp-${path}"],
    }

    exec { "git_repo_chgrp-${path}":
        command => "/bin/chgrp -R ${group} ${path}",
        notify => Exec["git_repo_chmod-${path}"],
    }

    exec { "git_repo_chmod-${path}":
        command => "/bin/chmod u=rX,g=rX,o=rX -R ${path}",
    }
}
