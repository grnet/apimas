Basic Architecture
==================

APIMAS assumes applications are set up like this:

1. There is a REST API at a location ``/<prefix>/api/*``
   with any static files available at ``/<prefix>/static/*``

   This API includes multiple collections of REST resources.

   Each resource is defined as a collection of objects of the same type.
   The object type is defined as a set of fields with a name and
   type, including field types that refer to fields of other resources.

   For each resource collection there are built in operations that accept
   and return JSON data.

   - ``POST /<prefix>/api/<resource>/  data: {key:val...} -> <url>``

     Creates a new resource in the collection. Its identifier is
     returned in the form:

     ``/<prefix>/api/<resource>/<id>``

     The resource is initialized to the fields provided.

   - ``GET /<prefix>/api/<resource>/  filter: {}``

     .. there is not enough documentation about filtering, ordering,
        and pagination input

     List the resource collection according to filters, ordering,
     and pagination input.

   - ``PUT /<prefix>/api/<resource/<id>  data: {key:val...}``

     Update (or create) resource with fields from input.

   - ``GET /<prefix>/api/<resource>/<id> -> data: {key:val...}``

     Retrieve a ``data: {key:val...}`` representation of the resource.

   - ``DELETE /<prefix>/api/<resource>/<id>``

     Remove the identified resource from the collection.

   - ``GET /<prefix>/api/<resource>/<id>/fields/<field> -> val``

     Resource fields are accessible recursively by their name
     under ``fields/<field>``.
     The value when retrieving is the same
     that would be retrieved from the parent resource
     under the corresponding field key
     ``({<field>:<value>})``

   - ``PUT /<prefix>/api/<resource>/<id>/fields/<field> val``

     Update a field of a resource with a new value.
     This value is identical to the one that would be provided
     by a PUT on the parent resource under the field key
     ``{<field>:<val>}``

   - ``[Collection] /<prefix>/api/<resource>/<id>/fields/<field>/*``

     If a resource field is a collection then all above operations are
     optionally available recursively.

     Resource fields that are themselves collections are not equivalent
     to top-level resources. They are embedded on their parent resource
     and are retrieved and set along with the parent.
     Designers of APIs that need their collections to scale should make
     them top-level. Nested collections are supported to help data
     organization and convenience.

Built-in operations can be overridden for customization.
The application may also create new named actions:

   - ``POST /<prefix>/api/<resource>/<id>/actions/<action>  data:{key:val...}``

     Execute application-provided actions with input.


2. Each top-level REST resource corresponds to a Data View that connects
   the API with the data store.

   The data view modelling completely defines the REST behaviour of the
   API locations. The data view may be linked and triggered in various
   interfaces (e.g. ``GET /search/by-name/<name>/`` being equivalent to
   ``GET /resource/<some-id>``). Moreover, the underlying data may have
   arbitrary representation in actual storage. The data view is
   responsible for connecting the two layers.


3. The Data Storage layer models the actual representation of data in
   storage. There should be no native way to store data. The Data View
   layer should support adapting various storage layers for exposition
   to the REST API locations. For example, Django models may be one way
   to model actual storage representation.


4. The primary responsibility of the application is to hook at the Data
   View layer and provide storage and business logic. This logic must
   implement the hooks corresponding to all actions defined in 1.


5. However, the framework should provide various data store-to-view
   adapters (e.g. for Django, mongodb, S3). These adapters should
   themselves automatically hook to all actions defined in 1 and provide
   further contextualized hooks to applications.

   The store-to-view adapter must at least provide these hooks for
   modelling:

   a. To expose arbitrary store-level fields to the REST API as-is
   b. To create REST-level fields that do not directly correspond to
      store-level fields, but may be a function or transformation
      of one or multiple of them.

   and these hooks for business logic:

   c. A hook immediately after validation of REST input that can affect
      the communication with the backend store.
   d. A hook after communication with the backend store that can affect
      the response.
