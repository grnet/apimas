define apimas::app_endpoint (
    $api_name,
    $app_address,
    $app_settings,
    $wsgi_app,
    $app_workers,
    $debug_level = "debug",
    $srv_root = "/var/lib",
    $etc_root = "/etc",
    $lib_root = "/usr/lib",
) {

    group { "$api_name":
        ensure => present,
        before => File["${etc_root}/${api_name}/settings.conf"],
    }

    user { "$api_name":
        ensure => present,
        gid => $api_name,
        home => "${srv_root}/${api_name}/data",
        password => "",
        before => File["${etc_root}/${api_name}/settings.conf"],
    }

    file { "${srv_root}/${api_name}":
        ensure => directory,
        owner => "${api_name}",
        group => "${api_name}",
        mode => "0750",
        before => File["${etc_root}/${api_name}/settings.conf"],
    }

    file { "${srv_root}/${api_name}/data":
        ensure => directory,
        owner => root,
        group => "${api_name}",
        mode => "u=rwx,g=rwxs,o=",
        before => File["${etc_root}/${api_name}/settings.conf"],
        require => File["${srv_root}/${api_name}"],
    }

    file { "${srv_root}/${api_name}/www":
        ensure => directory,
        owner => "${api_name}",
        group => "www-data",
        mode => "0750",
        before => File["${etc_root}/${api_name}/settings.conf"],
    }

    file { "${etc_root}/${api_name}":
        ensure => directory,
        owner => "root",
        group => "${api_name}",
        mode => "0750",
        before => File["${etc_root}/${api_name}/settings.conf"],
    }

    file { "${etc_root}/${api_name}/settings.conf":
        ensure => file,
        owner => root,
        group => "${api_name}",
        mode => "0640",
        content => $app_settings,
        require => File["${etc_root}/${api_name}"],
        notify => Service["gunicorn"],
    }

    file { "/etc/gunicorn.d/${api_name}":
        ensure => file,
        owner => "root",
        group => "root",
        mode => "0644",
        content => template('apimas/gunicorn.conf.erb'),
        require => File["${etc_root}/${api_name}/settings.conf"],
        notify => Service["gunicorn"],
    }
}
