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
    apimas::pin {'nginx':
        version => "1.6.*",
    }

    package { 'nginx':
        ensure => installed,
        require => Apimas::Pin['nginx']
    }

    apimas::pin {'gunicorn':
        version => "19.6.*",
    }

    package { 'gunicorn':
        ensure => installed,
        require => Apimas::Pin['gunicorn']
    }

    apimas::pin {'postgresql':
        version => "9.4*",
    }

    package { 'postgresql':
        ensure => installed,
        require => Apimas::Pin['postgresql']
    }

    package { 'git':
        ensure => installed,
    }

    package { 'virtualenv':
        ensure => installed,
    }

    apimas::nginx_site { $server_name:
        server_name => $server_name,
        ssl_cert => $ssl_cert,
        ssl_key => $ssl_key,
        notify => Service['nginx'],
    }

    service { 'postgresql':
        ensure => running,
        require => Package['postgresql'],
    }

    service { 'gunicorn':
        ensure => running,
        require => Package['gunicorn'],
    }

    service { 'nginx':
        ensure => running,
        require => Package['nginx'],
    }

    file {'/etc/nginx/sites-enabled/default':
        ensure => absent,
        notify => Service['nginx'],
    }
}
