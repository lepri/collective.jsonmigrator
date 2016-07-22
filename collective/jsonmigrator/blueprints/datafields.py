# -*- coding: utf-8 -*-
from collective.transmogrifier.interfaces import ISection
from collective.transmogrifier.interfaces import ISectionBlueprint
from collective.transmogrifier.utils import resolvePackageReferenceOrFile
from zope.interface import classProvides
from zope.interface import implements

import base64
import os

from plone.dexterity.utils import iterSchemata
from zope.schema import getFieldsInOrder

try:
    from Products.Archetypes.interfaces import IBaseObject
except ImportError:
    IBaseObject = None

try:
    from plone.dexterity.interfaces import IDexterityContent
    dexterity_available = True
except:
    dexterity_available = False


class DataFields(object):

    """
    """

    classProvides(ISectionBlueprint)
    implements(ISection)

    def __init__(self, transmogrifier, name, options, previous):
        self.previous = previous
        self.options = options
        self.context = transmogrifier.context
        self.datafield_prefix = options.get('datafield-prefix', '_datafield_')
        self.root_path_length = len(self.context.getPhysicalPath())

    def __iter__(self):
        for item in self.previous:
            # not enough info
            if '_path' not in item:
                yield item
                continue

            obj = self.context.unrestrictedTraverse(
                str(item['_path'].lstrip('/')), None)

            # path doesn't exist
            if obj is None:
                yield item
                continue

            # do nothing if we got a wrong object through acquisition
            path = item['_path']
            if path.startswith('/'):
                path = path[1:]
            if '/'.join(obj.getPhysicalPath()[self.root_path_length:]) != path:
                yield item
                continue

            if IBaseObject.providedBy(obj):
                for key in item.keys():
                    if not key.startswith(self.datafield_prefix):
                        continue

                    fieldname = key[len(self.datafield_prefix):]
                    field = obj.getField(fieldname)
                    if field is None:
                        continue

                    # get the full path of the files
                    file_path = resolvePackageReferenceOrFile(
                        self.options['path']) + item[key]
                    if not os.path.exists(file_path):
                        continue
                    f = open(file_path)
                    value = f.read()
                    f.close()

                    # XXX: handle other data field implementations
                    field_value = field.get(obj)
                    if not hasattr(field_value, 'data') or (
                            value != field_value.data):
                        field.set(obj, value)
                        obj.setFilename(item[key]['filename'], fieldname)
                        obj.setContentType(
                            item[key]['content_type'], fieldname)

            if dexterity_available and IDexterityContent.providedBy(obj):
                for key in item.keys():
                    if not key.startswith(self.datafield_prefix):
                        continue

                    fieldname = key[len(self.datafield_prefix):]

                    # get the full path of the files
                    file_path = resolvePackageReferenceOrFile(
                        self.options['path']) + item[key]
                    if not os.path.exists(file_path):
                        continue
                    f = open(file_path)
                    value = f.read()
                    f.close()

                    filename = item['id'].decode('utf-8')
                    contenttype = ''

                    # get all fields for this obj
                    for schemata in iterSchemata(obj):
                        for name, field in getFieldsInOrder(schemata):
                            if field.__name__ == fieldname:
                                # create a blob instance
                                instance = field._type(
                                    data=value,
                                    filename=filename,
                                    contentType=contenttype,
                                )
                                # set it
                                field.set(field.interface(obj), instance)
                                continue

            yield item
