# == Class: apimas
#
# Full description of class apimas here.
#
# === Parameters
#
# Document parameters here.
#
# [*sample_parameter*]
#   Explanation of what this parameter affects and what it defaults to.
#   e.g. "Specify one or more upstream ntp servers as an array."
#
# === Variables
#
# Here you should define a list of variables that this module would require.
#
# [*sample_variable*]
#   Explanation of how this variable affects the funtion of this class and if
#   it has a default. e.g. "The parameter enc_ntp_servers must be set by the
#   External Node Classifier as a comma separated list of hostnames." (Note,
#   global variables should be avoided in favor of class parameters as
#   of Puppet 2.6.)
#
# === Examples
#
#  class { 'apimas':
#    servers => [ 'pool.ntp.org', 'ntp.local.company.com' ],
#  }
#
# === Authors
#
# Author Name <author@domain.com>
#
# === Copyright
#
# Copyright 2016 GRNET
#

class apimas (
    $server_name = $fqdn,
    $ssl_cert,
    $ssl_key,
) {
    package { 'python-django':
        ensure => installed,
        before => Apimas::Apache_site["${server_name}"],
        install_options => ['-t', 'jessie-backports'],
    }

    package { 'python-psycopg2':
        ensure => installed,
        before => Apimas::Apache_site["${server_name}"],
    }

    package { 'apache2':
        ensure => installed,
        before => Apimas::Apache_site["${server_name}"],
    }

    package { 'gunicorn':
        ensure => installed,
        before => Apimas::Apache_site["${server_name}"],
        install_options => ['-t', 'jessie'],
    }

    package { 'postgresql':
        ensure => installed,
        before => Apimas::Apache_site["${server_name}"],
    }

    apimas::apache_site { $server_name:
        server_name => $server_name,
        ssl_cert => $ssl_cert,
        ssl_key => $ssl_key,
        notify => Service['apache2'],
    }

    service { 'postgresql':
        ensure => running,
        require => Package['postgresql'],
    }

    service { 'gunicorn':
        ensure => running,
        require => Package['gunicorn'],
    }

    #service { 'nginx':
    #    ensure => running,
    #    require => Package['nginx'],
    #}

    service { 'apache2':
        ensure => running,
        require => Package['apache2'],
    }
}
