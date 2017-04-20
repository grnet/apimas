Request Pipeline
================

Each request is described by a bunch of data (describing a resource)
and an action performed on this resource. For example, in the
context of HTTP, an action is denoted by a HTTP method and a
url path.

Example:

```
POST api/collection/  data {} 
```
where `data` is the body of the request.

Each request also consists of various stages until the final response
is served. For instance, imagine the case of a typical REST create
action.

1. Data de-serialization
2. Authentication
3. Permissions
4. Data validation
5. Creation of a new resource
6. Data serialization

Such stages are met almost in every web application. Therefore, APIMAS
should encourage the creation of generic and reusable components which
implement different stages of the request pipeline included but not
limited to the above.

In this context, we could classify these components into three
categories.

- `Request Processors`: Components which take the request as input
and change its context, (e.g. an authentication component may take the
headers of the request and creates a user object in its context).
- `Handlers`: Handlers which take a request and produce a response.
Typically, handlers denote the business logic of the action (e.g.
creation of a new resource).
- `Response Processors`: Like the request processors but they
interact with the response (e.g. data serialization).

Therefore, developers should be able to easily:

- form request pipelines which consists of multiple processors,
one handler, and multiple response processors.
- combine these components with whatever way the like, e.g. first
do validation, and do authentication afterwards.
- use these components to different applications and frameworks (ideally).

Therefore an action in specification could be described as follows:

```yaml
api:
    .endpoint: {}
    mycollection:
        .collection: {}
        *:
            name:
                .string: {}
            age:
                .integer: {}
        .actions:
            bar:
                method: POST
                url: /bar
                pre:
                    - apimas.processors.serialization
                    - apimas.processors.authenticator
                    - apimas.processors.permissions
                    - apimas.processors.validator
                handler: myapp.mymodule.myhandler
                post:
                    - apimas.processors.serialzation
```

Overall, the basic outline is:

- Create a pipeline of request processors, handler, response processors,
  much like django middlewares.
- Request processors receive the request context and may read and write data on
  it
- The handler receives the request context and produces a response context
- Response processors receive the response context and may read and write data
  on it
- Request and response objects are general and apimas-specified.
  The adapter (the apimas driver) must adapt the native requests and responses
  to the apimas contexts.
- Reusable components can be expressed as:
  - Processors at the pipeline operating on the APIMAS (and not the native)
  context
  - Factories to automatically generate processors and handlers operating at
  the native context
- At any point, developers may insert processors to observe, or alter any
  automatically installed behaviour
- How to actually achieve component reusability is a different software
  layer and requires a different design and implementation task
