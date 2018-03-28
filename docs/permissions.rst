APIMAS Permissions Framework
============================

For a given action on a collection and a give request user role, we need to
check if the action is allowed, and if so, restrict the accessible entries
of the collection and its accessible fields. Restrictions apply both to
reading are writing operations.

Restrictions on entries can be either expressible as a django queryset
filter or need to apply some more complicated logic.

It is preferable that restrictions on collections or single instances are
expressed in the same way, for example as a queryset filter.

Assume that a user has access only to the resources they own. We could write
a django filter::

  def check_owned(context):
    user = context.get('auth/user')
    return Q(user=user)

which can apply to all commands: list, retrieve, update, delete.


GET /positions/<id>?view=open
PATCH /positions/<id>?view=open
