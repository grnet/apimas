define apimas::virtualenv_pip ($venv, $requirements) {
    exec { "${venv}/install/${requirements}": 
        command => "${venv}/bin/pip install --no-deps -r ${requirements}",
        require => Apimas::Virtualenv["${venv}"],
        umask => "0222",
    }
}
