define apimas::pin (
    $package_name = $title,
    $version,
    $apt_preferences_d = "/etc/apt/preferences.d",
) {


    if $version {
        $pin_content = "Package: ${package_name}\nPin: version ${version}\nPin-priority: 1001\n"
    } else {
        $pin_content = ""
    }

    file { "${apt_preferences_d}/${package_name}":
        ensure => file,
        owner => root,
        group => root,
        mode => '0644',
        content => $pin_content,
    }
}
