define apimas::virtualenv_install ($venv, $source) {
    exec { "${venv}/install/${source}": 
        command => "${venv}/bin/pip install --no-deps .",
        require => Apimas::Virtualenv["${venv}"],
        cwd => "${source}",
        environment => ["PYTHONHOME=${venv}"],
        umask => "0222",
        logoutput => "on_failure",
    }
}
