define apimas::apache_endpoint (
    $api_name,
    $app_endpoints,
    $apache_root = "/etc/apache2",
    $srv_root = "/var/lib",
    $lib_root = "/usr/lib",
) {
    file { "${apache_root}/apimas-locations/${api_name}.conf":
        ensure => file,
        owner => "root",
        group => "root",
        mode => "0755",
        content => template('apimas/apache_apimas_location.conf.erb'),
        notify => Service['apache2'],
    }
}
