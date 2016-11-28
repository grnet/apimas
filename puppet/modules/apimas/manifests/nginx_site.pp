define apimas::nginx_site (
    $server_name,
    $ssl_cert,
    $ssl_key,
    $nginx_root = "/etc/nginx",
) {
    file { "${nginx_root}/apimas-locations":
        ensure => directory,
        owner => "root",
        group => "root",
        mode => "0755",
    }

    file { "${nginx_root}/apimas-upstreams":
        ensure => directory,
        owner => "root",
        group => "root",
        mode => "0755",
    }

    file { "${nginx_root}/sites-available/apimas":
        ensure => file,
        owner => "root",
        group => "root",
        mode => "0755",
        content => template('apimas/nginx_site.erb'),
    }

    file { "${nginx_root}/sites-enabled/apimas":
        ensure => link,
        target => "../sites-available/apimas",
        notify => Service['nginx'],
    }

    file { "/etc/ssl/certs/${server_name}.pem":
        ensure => file,
        owner => "root",
        group => "root",
        mode => "0644",
        content => $ssl_cert,
        notify => Service['nginx'],
    }

    file { "/etc/ssl/private/${server_name}.key":
        ensure => file,
        owner => "root",
        group => "root",
        mode => "0600",
        content => $ssl_key,
        notify => Service['nginx'],
    }
}
