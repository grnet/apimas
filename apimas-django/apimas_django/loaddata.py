from apimas.components import BaseProcessor
from apimas.errors import ValidationError
from apimas_django.handlers import Nothing, _django_base_construction


def check_flags(name, spec, value, full, instance, toplevel=False):
    flags = spec.get('flags', [])
    default = spec.get('default', Nothing)

    if 'readonly' in flags and not toplevel:
        if value is not Nothing:
            raise ValidationError("'%s': Field is readonly" % name)
        return Nothing

    if full and value is Nothing:
        value = Nothing if default is Nothing else default()

    if full and value is Nothing:
        raise ValidationError("'%s': Field is required" % name)

    if value is None and 'nullable' not in flags:
        raise ValidationError("'%s': Field is not nullable" % name)

    if value is not Nothing and 'writeonce' in flags and instance is not None:
        source = spec['source']
        stored_value = getattr(instance, source)
        if value != stored_value:
            raise ValidationError("'%s': Field is writeonce" % name)

    return value


def load_data_fields(subspecs, data, full, instance):
    loaded = {}
    for field_name, field_spec in subspecs.iteritems():
        value = data.get(field_name, Nothing)
        value = check_flags(field_name, field_spec, value, full, instance)
        source = field_spec['source']
        if value is not Nothing:
            loaded[source] = value

    return loaded


def load_data_subcollections(spec, data, full, instance):
    loaded = {}
    for subname, subspec in spec['subcollections'].iteritems():
        subsource = subspec['source']
        subdata = data.get(subname, Nothing)
        if subdata is Nothing:
            continue
        loaded[subsource] = [load_data(subname, subspec, elem, full, instance)
                             for elem in subdata]
    return loaded


def load_data_substructs(spec, data, full, instance):
    loaded = {}
    for subname, subspec in spec['substructs'].iteritems():
        subsource = subspec['source']
        subdata = data.get(subname, Nothing)
        loaded_substruct = load_data(subname, subspec, subdata, full, instance)
        if loaded_substruct is not Nothing:
            loaded[subsource] = loaded_substruct
    return loaded


def load_data(name, spec, data, full, instance, toplevel=False):
    data = check_flags(name, spec, data, full, instance, toplevel=toplevel)
    if data is Nothing:
        return Nothing

    if data is None:
        return None

    subfields = load_data_fields(spec['subfields'], data, full, instance)
    substructs = load_data_substructs(spec, data, full, instance)
    subcollections = load_data_subcollections(spec, data, full, instance)
    loaded = {}
    loaded.update(subfields)
    loaded.update(substructs)
    loaded.update(subcollections)
    return loaded


class LoadDataProcessor(BaseProcessor):
    READ_KEYS = {
        'imported_content': 'imported/content',
        'instance': 'backend/instance',
    }

    WRITE_KEYS = (
        'backend/input',
    )

    def __init__(self, collection_loc, action_name, spec, loaddata_full):
        self.collection_loc = collection_loc
        self.collection_name = collection_loc[-1]
        self.spec = spec
        self.full = loaddata_full is None or loaddata_full

    def execute(self, context_data):
        data = context_data['imported_content']
        instance = context_data['instance']
        loaded = load_data(
            self.collection_name, self.spec, data, self.full, instance,
            toplevel=True)
        return (loaded,)


LoadData = _django_base_construction(LoadDataProcessor)
