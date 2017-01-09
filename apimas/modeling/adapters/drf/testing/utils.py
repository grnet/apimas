from copy import deepcopy
import random
from collections import Iterable
from datetime import datetime
from django.db import models
from django.conf import settings
from django.core.urlresolvers import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from faker import Factory
from pytz import timezone
from apimas.modeling.core import documents as doc
from apimas.modeling.adapters.drf.django_rest import DjangoRestAdapter


fake = Factory.create()


class Generator(object):
    def __call__(self, api=False):
        raise NotImplementedError('__call__() must be implemented.')


class StringGenerator(Generator):
    def __init__(self, n=10):
        self.n = n

    def __call__(self, api=False):
        return fake.pystr(max_chars=self.n)


class NumberGenerator(Generator):
    def __init__(self, upper=10, negative=False, isfloat=False):
        self.upper = upper
        self.negative = negative
        self.isfloat = isfloat

    def __call__(self, api=False):
        lower = -self.upper if self.negative else 0
        return random.randint(lower, self.upper) if not self.isfloat\
            else random.uniform(lower, self.upper)


class DateGenerator(Generator):
    FORMATS = {
        True: '%Y-%m-%d',
        False: '%Y-%m-%dT%H:%M:%S'
    }

    def __init__(self, isdate=False):
        self.isdate = isdate

    def __call__(self, api=False, date_format=None):
        use_tz = getattr(settings, 'USE_TZ', False)
        tzinfo = timezone(fake.timezone()) if use_tz else None
        date_obj = fake.date_object() if self.isdate else fake.date_time(
            tzinfo=tzinfo)
        if api:
            date_format = date_format or self.FORMATS[self.isdate]
            return datetime.strftime(date_obj, date_format)
        return date_obj


def generate_random_email(api=False):
    return fake.email()


def file_generator(api=False):
    content = str(fake.text())
    mime_type = fake.mime_type()
    file_name = fake.file_name()
    return SimpleUploadedFile(file_name, content, content_type=mime_type)


def generate_random_boolean(api=False):
    return random.choice([True, False])


RANDOM_GENERATORS = {
    'string': StringGenerator(n=10),
    'email': generate_random_email,
    'integer': NumberGenerator(),
    'biginteger': NumberGenerator(),
    'float': NumberGenerator(isfloat=True),
    'datetime': DateGenerator(isdate=False),
    'date': DateGenerator(isdate=True),
    'boolean': generate_random_boolean,
    'file': file_generator
}


def reverse_mapping():
    mapping = {}
    for k, v in DjangoRestAdapter.TYPE_MAPPING.iteritems():
        if isinstance(v, Iterable):
            mapping.update({a: k for a in v})
        else:
            mapping[v] = k
    return mapping

FIELD_TYPE_MAPPING = reverse_mapping()


def get_structural_element(spec):
    filter_func = lambda x: not x.startswith('.')
    structural_elements = filter(filter_func, spec.keys())
    assert len(structural_elements) == 1
    return structural_elements[0]


def action_exists(spec, collection, action):
    structural_element = get_structural_element(spec)
    loc = (structural_element, collection, 'actions')
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


def get_fields(spec, collection, excluded=None, included=None):
    structural_element = get_structural_element(spec)
    loc = (structural_element, collection, '*')
    field_schema = doc.doc_get(spec, loc)
    return filter_field_schema(field_schema, excluded, included)


def get_required_fields(spec, collection):
    structural_element = get_structural_element(spec)
    loc = (structural_element, collection, '*')
    field_schema = doc.doc_get(spec, loc)
    return filter_field_schema(field_schema, included=['.required'])


def isrelational(field_type):
    return field_type in ['.ref', '.struct', '.structarray']


def generate_ref_url(spec, instances):
    ref = spec.get('to')
    ref_instances = instances.get(ref)
    random_instance = random.choice(ref_instances)
    url = reverse(ref + '-detail', args=[random_instance.pk])
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
            refs.append(ref)
            refs.extend(get_ref_collections(spec, ref))
        elif '.struct' in field_spec:
            refs.extend(get_refs(field_spec.get('.struct'), spec))
        elif '.structarray' in field_spec:
            refs.extend(get_refs(field_spec.get('.structarray'), spec))
    return refs


def get_ref_collections(spec, collection):
    structural_element = get_structural_element(spec)
    loc = (structural_element, collection, '*')
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


def populate_request(field_schema, instances, all_fields=True):
    adapter = DjangoRestAdapter()
    kwargs = {}
    if not all_fields:
        field_schema = get_sample_field_schema(field_schema)
    for field_name, spec in field_schema.iteritems():
        if '.readonly' in spec or '.identity' in spec or '.serial' in spec:
            continue
        predicate_type = adapter.extract_type(spec)
        if isrelational(predicate_type):
            predicate_kwargs = spec.get(predicate_type)
            kwargs[field_name] = RELATIONAL_CONSTRUCTORS[predicate_type](
                predicate_kwargs, instances)
        else:
            kwargs[field_name] = RANDOM_GENERATORS[predicate_type[1:]](
                api=True)
    return kwargs


def generate_field_value(model_field, instances):
    if model_field.related_model is None:
        field_type = FIELD_TYPE_MAPPING[type(model_field)]
        return RANDOM_GENERATORS[field_type](), False
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
