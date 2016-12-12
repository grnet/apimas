define apimas::virtualenv ($path) {
    exec { "${path}":
        command => "/usr/bin/virtualenv --system-site-packages ${path}",
        cwd => '/',
        creates => "${path}/bin/python",
        require => Package['virtualenv'],
    }
}
