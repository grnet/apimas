define apimas::app_endpoint (
    $api_name,
    $git_list_of_name_remote_commit,
    $git_ssh_identity,
    $app_address,
    $app_settings,
    $wsgi_app,
    $app_workers,
    $srv_root = "/srv",
    $nginx_root = "/etc/nginx",
) {

    group { "$api_name":
        ensure => present,
    }

    user { "$api_name":
        ensure => present,
        gid => $api_name,
        home => "${srv_root}/${api_name}-data",
        password => "",
    }

    file { "${srv_root}/${api_name}-server":
        ensure => directory,
        owner => "${api_name}",
        group => "www-data",
        mode => "0750",
    }

    file { "${srv_root}/${api_name}-data":
        ensure => directory,
        owner => "${api_name}",
        group => "www-data",
        mode => "0750",
    }

    file { "${srv_root}/${api_name}-server/sources":
        ensure => directory,
        owner => "${api_name}",
        group => "${api_name}",
        mode => "0550",
        require => File["${srv_root}/${api_name}-server"],
    }


    file { "${srv_root}/${api_name}-server/puppet":
        ensure => directory,
        owner => root,
        group => root,
        mode => '0550',
        require => File["${srv_root}/${api_name}-server"],
    }

    apimas::virtualenv { "${srv_root}/${api_name}-server/venv":
        path => "${srv_root}/${api_name}-server/venv",
    }

    $app_venv = "${srv_root}/${api_name}-server/venv"

    $git_list_of_name_remote_commit.each |$source| {
        $source_name = $source[0]
        $git_remote = $source[1]
        $git_commit = $source[2]
        $source_path = "${srv_root}/${api_name}-server/sources/${source_name}"

        apimas::git_repo { "${source_path}":
            user => root,
            group => $api_name,
            path => "${source_path}",
            remote => $git_remote,
            commit => $git_commit,
            ssh_identity => $git_ssh_identity,
            require => Apimas::Virtualenv["${app_venv}"],
        }

        apimas::virtualenv_pip { "${app_venv}/install/${source_path}/pip_requirements_debian.txt":
            venv => "${app_venv}",
            requirements => "${source_path}/pip_requirements_debian.txt",
            require => Apimas::Git_repo["${source_path}"],
            before => File["${srv_root}/${api_name}-data/settings.conf"],
        }

        apimas::virtualenv_install { "${app_venv}/install/${source_path}":
            venv => "${app_venv}",
            source => "${source_path}",
            require => Apimas::Virtualenv_pip["${app_venv}/install/${source_path}/pip_requirements_debian.txt"],
            before => File["${srv_root}/${api_name}-data/settings.conf"],
        }

        file { "${source_path}/get_package_requirements_debian":
            owner => root,
            group => root,
            mode => "0750",
            require => [
                Apimas::Git_repo["${source_path}"],
            ],
            content => template('apimas/get_package_requirements_debian.erb'),
            before => File["${srv_root}/${api_name}-data/settings.conf"],
        }

        $packages_manifest = "${srv_root}/${api_name}-server/puppet/packages_${source_name}.pp"
        exec { $packages_manifest:
            command => "${source_path}/get_package_requirements_debian > ${packages_manifest}",
            cwd => "/",
            require => [
                File["${source_path}/get_package_requirements_debian"],
                File["${srv_root}/${api_name}-server/puppet"],
            ],
            before => File["${srv_root}/${api_name}-data/settings.conf"],
        }
    }

    file { "${srv_root}/${api_name}-data/settings.conf":
        ensure => file,
        owner => root,
        group => "${api_name}",
        mode => "0640",
        content => $app_settings,
    }

    file { "/etc/gunicorn.d/${api_name}":
        ensure => file,
        owner => "root",
        group => "root",
        mode => "0644",
        content => template('apimas/gunicorn.conf.erb'),
        require => File["${srv_root}/${api_name}-data/settings.conf"],
        notify => Service["gunicorn"],
    }
}
