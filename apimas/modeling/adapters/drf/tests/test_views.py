import mock
import unittest
from apimas.modeling.adapters.drf import views, utils


side_effect = lambda x: 'imported_' + x


class TestViews(unittest.TestCase):

    @mock.patch.object(views, 'get_filtering_options')
    @mock.patch.object(views, 'gen_apimas_permission_cls')
    @mock.patch.object(views, 'get_bases_classes')
    @mock.patch('apimas.modeling.adapters.drf.utils.import_object')
    def test_generate_view(self, mock_import, mock_bases,
                           mock_apimas_perm, mock_filtering):
        mock_import.side_effect = side_effect
        mock_objects = mock.Mock()
        mock_objects.all.return_value = 'queryset'
        mock_model = mock.Mock(objects=mock_objects)
        mock_serializer = mock.Mock()
        mock_filtering.return_value = {'foo': 'bar'}, {'bar': 'foo'}
        mock_apimas_perm.return_value = None
        mock_bases.return_value = (mock.MagicMock, mock.Mock,)
        view_class = views.generate_view('foo', mock_serializer, mock_model,
                                         permissions=['foo', 'bar'],
                                         authentication_classes=['foo'],
                                         permission_classes=['bar'],
                                         mixins=['a', 'b'],
                                         hook_class='module.class',
                                         filter_fields=('field1', 'field2'),
                                         ordering_fields=('ord_a', 'ord_b'),
                                         actions=(),
                                         search_fields=('search_a', 'search_b')
                                         )
        self.assertEqual(view_class.__bases__, (mock.MagicMock, mock.Mock,))
        self.assertEqual(view_class.__name__, 'foo')
        cls_dict = view_class.__dict__
        self.assertEqual(cls_dict['authentication_classes'], ['imported_foo'])
        self.assertEqual(cls_dict['permission_classes'], ['imported_bar'])
        self.assertEqual(cls_dict['serializer_class'], mock_serializer)
        self.assertEqual(cls_dict['queryset'], 'queryset')
        self.assertEqual(cls_dict['foo'], 'bar')
        self.assertEqual(cls_dict['bar'], 'foo')

        mock_filtering.assert_called_once_with(
            ('field1', 'field2'), ('ord_a', 'ord_b'), ('search_a', 'search_b'))
        mock_apimas_perm.assert_called_once_with(mock_model, ['foo', 'bar'])
        mock_bases.assert_called_once_with(['a', 'b'], 'module.class', ())

    @mock.patch.object(views, 'get_filter_backends',
                       return_value={'foo': 'bar'})
    def test_get_filtering_options(self, mock_filter_backends):
        search_fields = ('search_a', 'search_b')
        ordering_fields = ('ordering_a', 'ordering_b')
        filter_fields = ('filter_a', 'filter_b')
        filter_options, filter_backends = views.get_filtering_options(
            search_fields=search_fields, ordering_fields=ordering_fields,
            filter_fields=filter_fields)
        self.assertEqual(len(filter_options), 3)
        self.assertEqual(filter_options['search_fields'], search_fields)
        self.assertEqual(filter_options['ordering_fields'], ordering_fields)
        self.assertEqual(filter_options['filter_fields'], filter_fields)
        self.assertEqual(filter_backends, {'foo': 'bar'})
        mock_filter_backends.assert_called_once_with(filter_options)

    def test_get_filter_backends(self):
        searchable_fields = {
           'search_fields': ['a'],
           'ordering_fields': ['b'],
           'filter_fields': ['c'],
        }
        filter_backends = views.get_filter_backends(searchable_fields)
        self.assertEqual(len(filter_backends), 1)
        self.assertEqual(set(filter_backends['filter_backends']),
                         {views.filters.DjangoFilterBackend,
                          views.filters.SearchFilter,
                          views.filters.OrderingFilter})

    @mock.patch.object(utils, 'import_object')
    def test_get_bases_classes(self, mock_func):
        mock_func.side_effect = side_effect
        hook_class = 'hook'
        mixins = ('mixin_a', 'mixin_b')
        bases = views.get_bases_classes(mixins, hook_class, actions=())
        self.assertEqual(bases, ('imported_hook', 'imported_mixin_a',
                                 'imported_mixin_b',
                                 views.viewsets.GenericViewSet))

        bases = views.get_bases_classes(mixins, hook_class,
                                        actions=('list', 'retrieve'))
        self.assertEqual(bases, ('imported_hook', 'imported_mixin_a',
                                 'imported_mixin_b',
                                 views.MIXINS['list'],
                                 views.MIXINS['retrieve'],
                                 views.viewsets.GenericViewSet))
