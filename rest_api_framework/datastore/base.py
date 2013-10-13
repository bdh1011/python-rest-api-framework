# -*- coding: utf-8 -*-
from abc import ABCMeta, abstractmethod
from werkzeug.exceptions import BadRequest


class DataStore(object):
    """
    define a source of data. Can be anything fron database to other
    api, files and so one
    """
    __metaclass__ = ABCMeta

    def __init__(self, ressource_config, model, **options):
        """
        Set the ressource datastore
        """
        self.ressource_config = ressource_config
        self.options = options
        self.model = model()

    @abstractmethod
    def get(self, identifier):
        """
        Should return a dictionnary representing the ressource matching the
        identifier or raise a NotFound exception.

        .. note::

           Not implemented by base DataStore class
        """
        raise NotImplemented

    @abstractmethod
    def create(self, data):
        """
        data is a dict containing the representation of the
        ressource. This method should call
        :meth:`~.DataStore.validate`,
        create the data in the datastore and return the ressource
        identifier

        .. note::

        Not implemented by base DataStore class
        """
        raise NotImplemented

    @abstractmethod
    def update(self, obj, data):
        """
        should be able to call :meth:`~.DataStore.get` to retreive the
        object to be updated, :meth:`~.DataStore.validate_fields` and
        return the updated object

        .. note::

           Not implemented by base DataStore class
        """
        raise NotImplemented

    @abstractmethod
    def delete(self, identifier):
        """
        should be able to validate the existence of the object in the
        ressource and remove it from the datastore

        .. note::

           Not implemented by base DataStore class
        """
        raise NotImplemented

    @abstractmethod
    def get_list(self, offset=None, count=None, **kwargs):
        """
        This method is called each time you want a set of data.
        Data could be paginated and filtered.
        Should call :meth:`~.DataStore.filter`
        and return :meth:`~.DataStore.paginate`

        .. note::

           Not implemented by base DataStore class
        """
        raise NotImplemented

    @abstractmethod
    def filter(self, **kwargs):
        """
        should return a way to filter the ressource according to
        kwargs.  It is not mandatory to actualy retreive the
        ressources as they will be paginated just after the filter
        call. If you retreive the wole filtered ressources you loose
        the pagination advantage. The point here is to prepare the
        filtering. Look at SQLiteDataStore.filter for an example.

        .. note::

           Not implemented by base DataStore class
        """
        raise NotImplemented

    def paginate(self, data, offset, count, **kwargs):
        """
        Paginate sould return all the object if no pagination options
        have been set or only a subset of the ressources if pagination
        options exists.
        """
        start = offset
        end = count
        if end:
            if "start" in kwargs:
                start = int(kwargs['start'])
                end = start + self.options['paginate_by']
            elif "end" in kwargs:
                end = int(kwargs['end'])
                start = end - int(kwargs['end'])

        return data[start:end]

    def validate(self, data):
        """
        Check if data send are valid for object creation. Validate
        Chek that each required fields are in data and check for their
        type too.

        Used to create new ressources
        """

        if not isinstance(data, dict):
            raise BadRequest()
        for field in self.model.fields:
            for validator in field.validators:
                if not validator.validate(data[field.name]):
                    raise BadRequest()

    def validate_fields(self, data):
        """
        Validate only some fields of the ressource.
        Used to update existing objects
        """
        if not isinstance(data, dict):
            raise BadRequest()
        for k, v in data.iteritems():
            if k not in self.model.get_fields_name():
                raise BadRequest()
            field = self.model.get_field(k)
            for validator in field.validators:
                if not validator.validate(v):
                    raise BadRequest()
