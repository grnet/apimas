from django.db import models as dmodels
from apimas.utils import generators as gen
from apimas.django.generators import generate_file

# Dictionary of generators per model field.
FIELD_TYPE_MAPPING = {
    dmodels.TextField: gen.generate_string,
    dmodels.CharField: gen.generate_string,
    dmodels.EmailField: gen.generate_email,
    dmodels.IntegerField: gen.generate_integer,
    dmodels.BigIntegerField: gen.generate_integer,
    dmodels.FloatField: gen.generate_float,
    dmodels.DateTimeField: gen.DateTimeGenerator(native=True),
    dmodels.DateField: gen.DateGenerator(native=True),
    dmodels.BooleanField: gen.generate_boolean,
    dmodels.FileField: generate_file,
}


def _extra_model_kwargs(model_field):
    if type(model_field) is dmodels.CharField:
        return {'max_length': model_field.max_length}
    return {}


def _generate_field_value(model_field, instances):
    model_kwargs = _extra_model_kwargs(model_field)
    if model_field.related_model is None:
        generator = FIELD_TYPE_MAPPING[type(model_field)]
        return generator(**model_kwargs), False
    ref_instance = instances.get(
        model_field.related_model)
    if model_field.one_to_one or model_field.many_to_one:
        return ref_instance, False
    else:
        return ref_instance, True


def _save(model, kwargs, outstanding):
    instance = model.objects.create(**kwargs)
    for k, v in outstanding.iteritems():
        model_field = getattr(instance, k)
        model_field.add(v)
    return instance


def get_models_to_create(models):
    """
    Creates a dictionary of lists with all the related models per Model class.
    Only one-way relations are taken into account, i.e. relations derived from
    a django model Field.

    Args:
        models (list): List of models classses to take their relations.

    Returns:
        Dictionary of related models per model.
    """
    schema = {model: [] for model in models}
    for model in models:
        model_fields = filter(
            (lambda x: isinstance(x, dmodels.Field) and
                x.related_model is not None), model._meta.get_fields())
        for model_field in model_fields:
            if model_field.related_model not in models:
                schema.update(
                    get_models_to_create([model_field.related_model]))
            schema[model].append(model_field.related_model)
    return schema


def populate_random_model(model, instances, save=True):
    """
    Creates a new instance of a model using random data.

    Args:
        model: Model class from which instance is created.
        instances (dict): Dictionary of lists which contains the existing
            model instances per Model class. It is used to retrieve any
            required modele that instance requires in order to be created.
        save (bool): (optional) `True` if istance is saved to db; `False`
            otherwise.

    Returns:
        Created model instance with random data.
    """
    model_fields = filter(lambda x: isinstance(x, dmodels.Field),
                          model._meta.get_fields())
    kwargs = {}
    # Outstanding instances in case of Many-to-Many relations.
    outstanding = {}
    for model_field in model_fields:
        if isinstance(model_field, dmodels.AutoField):
            continue
        field_value, isoutstanding = _generate_field_value(
            model_field, instances)
        if isoutstanding:
            outstanding[model_field.name] = field_value
        else:
            kwargs[model_field.name] = field_value
    if not save:
        return kwargs
    return _save(model, kwargs, outstanding)
