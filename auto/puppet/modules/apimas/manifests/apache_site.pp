define apimas::apache_site (
    $server_name,
    $ssl_cert,
    $ssl_key,
    $apache_root = "/etc/apache2",
    $srv_root = "/var/www",
) {
    exec { "${apache_root}/sites-available/apimas.conf-a2enmod-alias":
        command => "/usr/sbin/a2enmod alias",
        before => File["${apache_root}/sites-available/apimas.conf"],
    }

    exec { "${apache_root}/sites-available/apimas.conf-a2enmod-rewrite":
        command => "/usr/sbin/a2enmod rewrite",
        before => File["${apache_root}/sites-available/apimas.conf"],
    }

    exec { "${apache_root}/sites-available/apimas.conf-a2enmod-ssl":
        command => "/usr/sbin/a2enmod ssl",
        before => File["${apache_root}/sites-available/apimas.conf"],
    }

    exec { "${apache_root}/sites-available/apimas.conf-a2enmod-proxy":
        command => "/usr/sbin/a2enmod proxy",
        before => File["${apache_root}/sites-available/apimas.conf"],
    }

    exec { "${apache_root}/sites-available/apimas.conf-a2enmod-proxy_http":
        command => "/usr/sbin/a2enmod proxy_http",
        before => File["${apache_root}/sites-available/apimas.conf"],
    }

    exec { "${apache_root}/sites-available/apimas.conf-a2enmod-proxy_balancer":
        command => "/usr/sbin/a2enmod proxy_balancer",
        before => File["${apache_root}/sites-available/apimas.conf"],
    }

    exec { "${apache_root}/sites-available/apimas.conf-a2enmod-headers":
        command => "/usr/sbin/a2enmod headers",
        before => File["${apache_root}/sites-available/apimas.conf"],
    }

    file { "${srv_root}/${server_name}":
        ensure => directory,
        owner => "root",
        group => "root",
        mode => "0755",
    }

    file { "${apache_root}/apimas-locations":
        ensure => directory,
        owner => "root",
        group => "root",
        mode => "0755",
    }

    file { "${apache_root}/sites-available/apimas.conf":
        ensure => file,
        owner => "root",
        group => "root",
        mode => "0755",
        content => template('apimas/apache_site.erb'),
    }

    file { "${apache_root}/sites-enabled/apimas.conf":
        ensure => link,
        target => "../sites-available/apimas.conf",
        notify => Service['apache2'],
    }

    file { '/etc/apache2/sites-enabled/000-default.conf':
        ensure => absent,
        notify => Service['apache2'],
    }

    file { "/etc/ssl/certs/apimas-${server_name}.pem":
        ensure => file,
        owner => "root",
        group => "root",
        mode => "0644",
        content => $ssl_cert,
        notify => Service['apache2'],
    }

    file { "/etc/ssl/private/apimas-${server_name}.key":
        ensure => file,
        owner => "root",
        group => "root",
        mode => "0600",
        content => $ssl_key,
        notify => Service['apache2'],
    }
}
