define apimas::nginx_endpoint (
    $api_name,
    $app_endpoints,
    $nginx_root = "/etc/nginx",
    $lib_root = "/usr/lib",
) {
    file { "${nginx_root}/apimas-locations/${api_name}.conf":
        ensure => file,
        owner => "root",
        group => "root",
        mode => "0755",
        content => template('apimas/nginx_apimas_location.conf.erb'),
        notify => Service['nginx'],
    }

    file { "${nginx_root}/apimas-upstreams/${api_name}.conf":
        ensure => file,
        owner => "root",
        group => "root",
        mode => "0755",
        content => template('apimas/nginx_apimas_upstream.conf.erb'),
        notify => Service['nginx'],
    }
}
