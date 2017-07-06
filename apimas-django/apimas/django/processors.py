from django.core.exceptions import FieldDoesNotExist
from django.db.models  import Model
from django.db.models.query import QuerySet
from apimas import documents as doc
from apimas.errors import InvalidInput
from apimas.components import BaseProcessor


REF = '.ref'
STRUCT = '.struct='
ARRAY_OF = '.array of='


class InstanceToDict(BaseProcessor):
    name = 'apimas.django.processors.InstanceToDict'

    READ_KEYS = {
        'instance': 'response/content',
        'model': 'store/orm_model'
    }

    WRITE_KEYS = (
        'response/content',
    )

    def _extract_many(self, instance, field_name):
        """
        Extracts the value of a many to many or one to many django model
        relation.
        """
        try:
            return getattr(instance, field_name).all()
        except AttributeError:
            return getattr(instance, field_name + '_set').all()

    def _extract_rel_id(self, instance, field_name):
        """
        Extracts the id of a one to one or many to one django model
        relation.
        """
        try:
            return getattr(instance, field_name + '_id')
        except AttributeError:
            return getattr(instance, field_name)

    def _extract_rel(self, orm_model, instance, field, field_spec):
        """
        Helper function to get the python native format of a django
        related field.
        """
        many = field.many_to_many or field.one_to_many
        source = doc.doc_get(
            field_spec, ('.field', 'source')) or field.name
        if many:
            value = self._extract_many(instance, source)
            if REF in field_spec[ARRAY_OF]:
                return [getattr(v, 'pk') for v in value]
            return [
                self.to_dict(
                    field.related_model, v,
                    field_spec[ARRAY_OF][STRUCT]
                ) for v in value
            ]
        if not hasattr(instance, field.name):
            return None
        if REF in field_spec:
            return self._extract_rel_id(instance, field.name)
        return self.to_dict(field.related_model, getattr(instance, source),
                            field_spec['.struct='])

    def to_dict(self, orm_model, instance, spec=None):
        """
        Constructs a given model instance a python dict.

        Only the model attributes which are declared on specification are
        included in the returned dictionary.

        Args:
            orm_model: Django model associated with the instance.
            instance: Model instance to be converted into a python dict.
            spec (dict): Specification of collection.

        Returns:
            dict: Dictionary format of a model instance.
        """
        if instance is None:
            return None
        spec_properties = spec or self.spec.get('*')
        data = {}
        for k, v in spec_properties.iteritems():
            # Ignore predicates.
            if k.startswith('.'):
                continue
            source = doc.doc_get(v, ('.meta', 'source')) or k
            try:
                field = orm_model._meta.get_field(source)
                if field.related_model is None:
                    value = getattr(instance, field.name)
                else:
                    value = self._extract_rel(orm_model, instance, field,
                                              v)
            except FieldDoesNotExist:
                # If instance does not have any field with that name, then
                # check if there is any property-like.
                value = getattr(instance, source)
            data[source] = value
        return data

    def process(self, collection, url, action, context):
        """
        A processor which is responsible for converting a
        `django.db.models.Model` or a `django.db.models.query.QuerySet`
        instance into a python dict.

        This dict holds only the information specified by the spec.
        """
        processor_data = self.read(context)
        instance = processor_data['instance']
        if instance is None:
            self.write(None, context)
            return

        if instance and (not isinstance(instance, Model) and not
                       isinstance(instance, QuerySet)):
            msg = 'A model instance or a queryset is expected. {!r} found.'
            raise InvalidInput(msg.format(type(instance)))
        model = processor_data['model']
        if isinstance(instance, QuerySet):
            instance = [self.to_dict(model, inst) for inst in instance]
        else:
            instance = None if instance is None else self.to_dict(
                model, instance)
        self.write((instance,), context)
