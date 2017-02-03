endpoint_spec = {
    '.endpoint': {},
    'version': {
        '.string': {},
    },
    'meta': {
        '*': {},
    },
    'api': {
        '*': {
            '.collection': {},
            'action-*': {
                '.action': {},
            },
            'id-*': {
                '.resource': {},
                'action-*': {
                    '.action': {},
                },
                'data-*': {
                    '.field': {},
                },
            },
        },
    },
}
