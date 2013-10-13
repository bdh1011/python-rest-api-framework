from base import DataStore
from rest_api_framework.models import PkField
from werkzeug.exceptions import NotFound
import sqlite3


class SQLiteDataStore(DataStore):
    """
    Define a sqlite datastore for your ressource.  you have to give
    __init__ a data parameter containing the information to connect to
    the database and to the table.

    example:

    .. code-block:: python

       data={"table": "tweets",
             "name": "test.db"}
       model = ApiModel
       datastore = SQLiteDataStore(data, **options)

    SQLiteDataStore implement a naive wrapper to convert Field
    types into database type.

    * int will be saved in the database as INTEGER
    * float will be saved in the database as REAL
    * basestring will be saved in the database as TEXT
    * if the Field type is PKField, is a will be saved as
      PRIMARY KEY AUTOINCREMENT

    As soon as the datastore is instanciated, the database is create
    if it does not exists and table is created too

    .. note::

       - Constrains are not supported for now
       - It is not possible to use :memory database either.
         The connection is closed after each operations
    """

    wrapper = {int: "integer",
               float: "real",
               basestring: "text"
               }

    def __init__(self, ressource_config, model, **options):
        self.table = ressource_config["name"]
        conn = sqlite3.connect(ressource_config["name"])
        c = conn.cursor()
        table = ressource_config["table"]
        super(SQLiteDataStore, self).__init__({"conn": conn, "table": table},
                                              model,
                                              **options)
        statement = []
        for field in self.model.get_fields():
            query = "{0} {1}".format(field.name, self.wrapper[field.base_type])
            if isinstance(field, PkField):
                query += " primary key autoincrement"
            statement.append(query)
        fields = ", ".join(statement)

        sql = 'create table if not exists {0} ({1})'.format(table, fields)
        c.execute(sql)
        conn.commit()
        conn.close()

    def get_connector(self):
        """
        return a sqlite3 connection to communicate with the table
        define in self.table
        """
        conn = sqlite3.connect(self.table)
        return conn

    def filter(self, **kwargs):
        """
        Change kwargs["query"] with "WHERE X=Y statements".  The
        filtering will be done with the actual evaluation of the query
        in :meth:`~.SQLiteDataStore.paginate` the sql can then be lazy
        """
        kwargs['query'] += ' FROM {0}'
        return kwargs

    def paginate(self, data, **kwargs):
        """
        paginate the result of filter using ids limits.  Obviously, to
        work properly, you have to set the start to the last ids you
        receive from the last call on this method. The max number of
        row this method can give back depend on the paginate_by option.
        """
        args = []
        where_query = []
        print kwargs
        limit = kwargs.get("end", None)
        if kwargs.get("start", None):
            where_query.append(" id >=?")
            args.append(kwargs['start'])
        if len(where_query) > 0:
            data["query"] += " WHERE"
        data["query"] += " AND".join(where_query)

        # a hook for ordering
        data["query"] += " ORDER BY id ASC"

        if limit:
            data["query"] += " LIMIT {0}".format(limit)

        print data["query"], tuple(args)
        c = self.get_connector().cursor()
        c.execute(data["query"].format(self.ressource_config['table']),
                  tuple(args)
                  )
        objs = []
        for elem in c.fetchall():
            fields = self.model.get_fields_name()
            objs.append(dict(zip(fields, elem)))
        return objs

    def get_list(self, **kwargs):
        """
        return all the objects, paginated if needed, fitered if
        filters have been set.
        """
        fields = ", ".join(self.model.get_fields_name())
        kwargs["query"] = 'SELECT {0}'.format(fields)
        start = kwargs.pop("offset", None)
        end = kwargs.pop("count", None)
        data = self.filter(**kwargs)
        return self.paginate(data, start=start, end=end)

    def get(self, identifier):
        """
        Return a single row or raise NotFound
        """
        fields = ",".join(self.model.get_fields_name())
        query = "select {0} from {1} where id=?".format(
            fields,
            self.ressource_config["table"])
        c = self.get_connector().cursor()
        c.execute(query, (identifier,))
        obj = c.fetchone()
        if obj:
            fields = self.model.get_fields_name()
            return dict(zip(fields, obj))
        else:
            raise NotFound
        self.data['conn'].commit()

    def create(self, data):
        """
        Validate the data with :meth:`.base.DataStore.validate`
        And, if data is valid, create the row in database and return it.
        """
        self.validate(data)
        fields = []
        values = []
        for k, v in data.iteritems():
            if k in self.model.get_fields_name():
                fields.append(str(k))
                values.append(unicode(v))

        conn = self.get_connector()
        c = conn.cursor()

        query = "insert into {0} {1} values ({2})".format(
            self.ressource_config["table"],
            tuple(fields),
            ",".join(["?" for i in range(len(fields))])
            )
        c.execute(query, tuple(values))
        conn.commit()
        conn.close()
        return c.lastrowid

    def update(self, obj, data):
        """
        Retreive the object to be updated
        (:meth:`~.SQLiteDataStore.get` will raise a NotFound error if
        the row does not exist)

        Validate the fields to be updated and return the updated row
        """
        self.get(obj['id'])
        self.validate_fields(data)
        fields = []
        values = []
        for k, v in data.iteritems():
            if k in self.model.get_fields_name():
                fields.append(k)
                values.append(v)
        conn = self.get_connector()
        c = conn.cursor()
        update = " ".join(["{0}='{1}'".format(f, v) for f, v in zip(fields,
                                                                    values)])
        query = "update {0} set {1}".format(
            self.ressource_config["table"],
            update
            )
        c.execute(query)
        conn.commit()
        conn.close()
        return self.get(obj['id'])

    def delete(self, identifier):
        """
        Retreive the object to be updated
        (:meth:`~.SQLiteDataStore.get` will raise a NotFound error if
        the row does not exist)

        Return None
        """
        self.get(identifier)
        conn = self.get_connector()
        c = conn.cursor()

        query = "delete from {0} where id={1}".format(
            self.ressource_config["table"],
            identifier)
        c.execute(query)
        conn.commit()
        conn.close()