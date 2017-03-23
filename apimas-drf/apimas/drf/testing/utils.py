from copy import deepcopy
import random
from datetime import datetime
from django.db import models
from django.conf import settings
from django.core.urlresolvers import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from faker import Factory
from pytz import timezone
from apimas import documents as doc
from apimas.drf.django_rest import DjangoRestAdapter


fake = Factory.create()


class Generator(object):
    def __call__(self, api=False):
        raise NotImplementedError('__call__() must be implemented.')


class NumberGenerator(Generator):
    def __init__(self, upper=10, lower=0, isfloat=False):
        self.upper = upper
        self.lower = lower
        self.isfloat = isfloat

    def __call__(self, api=False):
        return random.randint(self.lower, self.upper) if not self.isfloat\
            else random.uniform(self.lower, self.upper)


class DateGenerator(Generator):
    FORMATS = {
        True: ['%Y-%m-%d'],
        False: ['%Y-%m-%dT%H:%M:%S']
    }

    def __init__(self, isdate=False):
        self.isdate = isdate

    def __call__(self, api=False, date_formats=None):
        use_tz = getattr(settings, 'USE_TZ', False)
        tzinfo = timezone(fake.timezone()) if use_tz else None
        date_obj = fake.date_object() if self.isdate else fake.date_time(
            tzinfo=tzinfo)
        if api:
            date_formats = date_formats or self.FORMATS[self.isdate]
            return datetime.strftime(date_obj, random.choice(date_formats))
        return date_obj


def generate_random_string(api=False, max_length=None):
    max_length = max_length or 255
    size = random.randint(1, max_length)
    return fake.pystr(max_chars=size)


def generate_random_email(api=False):
    return fake.email()


def generate_choices_field(api=False, choices=None):
    return random.choice(choices or [])


def generate_random_file(api=False):
    content = str(fake.text())
    mime_type = fake.mime_type()
    file_name = fake.file_name()
    return SimpleUploadedFile(file_name, content, content_type=mime_type)


def generate_random_boolean(api=False):
    return random.choice([True, False])


RANDOM_GENERATORS = {
    'string': generate_random_string,
    'text': generate_random_string,
    'email': generate_random_email,
    'integer': NumberGenerator(),
    'biginteger': NumberGenerator(),
    'float': NumberGenerator(isfloat=True),
    'datetime': DateGenerator(isdate=False),
    'date': DateGenerator(isdate=True),
    'boolean': generate_random_boolean,
    'file': generate_random_file,
    'choices': generate_choices_field,
}

FIELD_TYPE_MAPPING = {
    models.AutoField: 'serial',
    models.TextField: 'text',
    models.CharField: 'string',
    models.EmailField: 'email',
    models.IntegerField: 'integer',
    models.BigIntegerField: 'biginteger',
    models.FloatField: 'float',
    models.DateTimeField: 'datetime',
    models.DateField: 'date',
    models.BooleanField: 'boolean',
    models.FileField: 'file',
}


def action_exists(spec, endpoint, collection, action):
    loc = (endpoint, collection, '.actions')
    actions = doc.doc_get(spec, loc) or {}
    return action in actions


def _get_filtered_keys(field_schema, excluded, included):
    filtered_keys = []
    for k, v in field_schema.iteritems():
        properties = set(v.keys())
        included_properties = properties.intersection(
            included or properties)
        excluded_properties = properties.intersection(excluded or [])
        if included_properties and not excluded_properties:
            filtered_keys.append(k)
    return filtered_keys


def filter_field_schema(field_schema, excluded=None, included=None):
    filtered_keys = _get_filtered_keys(field_schema, excluded, included)
    filtered = {}
    for k in filtered_keys:
        spec = deepcopy(field_schema[k])
        if '.struct' in spec:
            spec['.struct'] = filter_field_schema(
                spec.get('.struct'), excluded, included)
        elif '.structarray' in spec:
            spec['.structarray'] = filter_field_schema(
                spec.get('.structarray'), excluded, included)
        filtered[k] = spec

    return filtered


def get_fields(spec, endpoint, collection, excluded=None, included=None):
    loc = (endpoint, collection, '*')
    field_schema = doc.doc_get(spec, loc)
    return filter_field_schema(field_schema, excluded, included)


def get_required_fields(spec, endpoint, collection):
    loc = (endpoint, collection, '*')
    field_schema = doc.doc_get(spec, loc)
    return filter_field_schema(field_schema, included=['.required'])


def isrelational(field_type):
    return field_type in ['.ref', '.struct', '.structarray']


def generate_ref_url(spec, instances):
    ref = spec.get('to')
    endpoint, collection = tuple(ref.split('/'))
    ref_instances = instances.get(ref)
    random_instance = random.choice(ref_instances)
    url = reverse(endpoint + '_' + collection + '-detail',
                  args=[random_instance.pk])
    return [url] if spec.get('many') else url


def generate_struct_data(spec, instances):
    return populate_request(spec, instances)


def generate_structarray_data(spec, instances):
    return [populate_request(spec, instances)]


RELATIONAL_CONSTRUCTORS = {
    '.ref': generate_ref_url,
    '.struct': generate_struct_data,
    '.structarray': generate_structarray_data,
}


def get_models_to_create(collection_models):
    schema = {model: [] for model in collection_models}
    for model in collection_models:
        model_fields = filter(
            (lambda x: isinstance(x, models.Field) and
                x.related_model is not None), model._meta.get_fields())
        for model_field in model_fields:
            if model_field.related_model not in collection_models:
                schema.update(
                    get_models_to_create([model_field.related_model]))
            schema[model].append(model_field.related_model)
    return schema


def get_refs(field_schema, spec):
    refs = []
    for field, field_spec in field_schema.iteritems():
        if '.ref' in field_spec:
            ref = field_spec['.ref']['to']
            endpoint, collection = tuple(ref.split('/'))
            refs.append(ref)
            refs.extend(get_ref_collections(spec, endpoint, collection))
        elif '.struct' in field_spec:
            refs.extend(get_refs(field_spec.get('.struct'), spec))
        elif '.structarray' in field_spec:
            refs.extend(get_refs(field_spec.get('.structarray'), spec))
    return refs


def get_ref_collections(spec, endpoint, collection):
    loc = (endpoint, collection, '*')
    field_schema = doc.doc_get(spec, loc)
    refs = get_refs(field_schema, spec)
    return refs


def get_model_relations(collection_models):
    schema = {model: [] for model in collection_models}
    for model in collection_models:
        model_fields = filter(
            (lambda x: isinstance(x, models.Field) and
                x.related_model is not None), model._meta.get_fields())
        for model_field in model_fields:
            schema[model].append(model_field.related_model)
    return schema


def topological_sort(schema):

    visited = {k: False for k in schema}
    top_sort = []

    def dfs(schema, k):
        visited[k] = True
        for v in schema.get(k):
            if not visited[v]:
                dfs(schema, v)
        top_sort.append(k)

    for k, v in schema.iteritems():
        if not visited[k]:
            dfs(schema, k)
    return top_sort


def get_sample_field_schema(field_schema):
    size = len(field_schema)
    sample_size = random.randint(0, size)
    return dict(random.sample(field_schema.items(), sample_size))


EXTRA_API_PARAMS = {
    '.string': {
        'max_length': 'max_length',
    },
    '.choices': {
        'allowed': 'choices',
    },
    '.date': {
        'format': 'date_formats',
    },
    '.datetime': {
        'format': 'date_formats',
    }
}


def _get_extra_params(spec, predicate_type):
    params = spec.get(predicate_type, {})
    return {
        v: params.get(k)
        for k, v in EXTRA_API_PARAMS.get(predicate_type, {}).iteritems()
    }


def populate_request(field_schema, instances, all_fields=True):
    adapter = DjangoRestAdapter()
    kwargs = {}
    if not all_fields:
        field_schema = get_sample_field_schema(field_schema)
    for field_name, spec in field_schema.iteritems():
        if '.readonly' in spec or '.identity' in spec or '.serial' in spec:
            continue
        predicate_type = adapter.extract_type(spec)
        extra_params = _get_extra_params(spec, predicate_type)
        if isrelational(predicate_type):
            predicate_kwargs = spec.get(predicate_type)
            kwargs[field_name] = RELATIONAL_CONSTRUCTORS[predicate_type](
                predicate_kwargs, instances, **extra_params)
        else:
            kwargs[field_name] = RANDOM_GENERATORS[predicate_type[1:]](
                api=True, **extra_params)
    return kwargs


def generate_field_value(model_field, instances):
    model_kwargs = _extra_model_kwargs(model_field)
    if model_field.related_model is None:
        field_type = FIELD_TYPE_MAPPING[type(model_field)]
        return RANDOM_GENERATORS[field_type](**model_kwargs), False
    ref_instance = instances.get(
        model_field.related_model)
    if model_field.one_to_one or model_field.many_to_one:
        return ref_instance, False
    else:
        return ref_instance, True


def create_instance(model, kwargs, outstanding):
    instance = model.objects.create(**kwargs)
    for k, v in outstanding.iteritems():
        model_field = getattr(instance, k)
        model_field.add(v)
    return instance


def _extra_model_kwargs(model_field):
    if type(model_field) is models.CharField:
        return {'max_length': model_field.max_length}
    return {}


def populate_model(model, instances, create=True):
    model_fields = filter((lambda x: isinstance(x, models.Field)),
                          model._meta.get_fields())
    kwargs = {}
    # Outstanding instances in case of Many-to-Many relations.
    outstanding = {}
    for model_field in model_fields:
        if isinstance(model_field, models.AutoField):
            continue
        field_value, isoutstanding = generate_field_value(
            model_field, instances)
        if isoutstanding:
            outstanding[model_field.name] = field_value
        else:
            kwargs[model_field.name] = field_value
    if not create:
        return kwargs
    return create_instance(model, kwargs, outstanding)
