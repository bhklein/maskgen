# =============================================================================
# Authors: PAR Government
# Organization: DARPA
#
# Copyright (c) 2016 PAR Government
# All rights reserved.
#==============================================================================

from os.path import expanduser
import new
from types import MethodType

class Proxy(object):
    def __init__(self, target):
        self._target = target

    def __getattr__(self, name):
        target = self._target
        f = getattr(target, name)
        if isinstance(f, MethodType):
            # Rebind the method to the target.
            return new.instancemethod(f.im_func, self, target.__class__)
        else:
            return f

def removeValue(obj, path):

    part = path
    splitpos = path.find(".")

    if splitpos > 0:
        part = path[0:splitpos]
        path = path[splitpos + 1:]
    else:
        path = None

    bpos = part.find('[')
    pos = 0
    if bpos > 0:
        pos = int(part[bpos + 1:-1])
        part = part[0:bpos]

    if part in obj:
        current_value = obj[part]
        if path is None:
            if type(current_value) is list or  type(current_value) is tuple :
                obj[part]  = tuple(list(current_value[:pos]) + list(current_value[pos+1:]))
                return current_value[pos]
            else:
                return obj.pop(part)
        else:
            if bpos > 0:
                current_value = current_value[pos]
            return removeValue(current_value,path)


def setPathValue(d, path, value):
    pos = path.find('.')
    lbracket = path.find('[')
    listpos = None
    nextpath = path[pos + 1:] if pos > 0 else None
    if lbracket > 0 and (pos < 0 or lbracket < pos):
        rbracket = path.find(']')
        listpos = int(path[lbracket + 1:rbracket])
        pos = lbracket
    if pos < 0:
        if listpos is not None:
            d[path][listpos] = value
        elif value is None:
            d.pop(path)
        else:
            d[path] = value
    elif listpos is not None:
        setPathValue(d[path[0:pos]][listpos], nextpath, value)
    else:
        if path[0:pos] not in d:
            d[path[0:pos]] = {}
        setPathValue(d[path[0:pos]], nextpath, value)

def getPathValues(d, path):
    """
    Given a nest structure,
    return all the values reference by the given path.
    Always returns a list.
    If the value is not found, the list is empty

    NOTE: Processing a list is its own recursion.
    """
    pos = path.find('.')
    currentpath = path[0:pos] if pos > 0 else path
    nextpath = path[pos + 1:] if pos > 0 else None
    lbracket = path.find('[')
    itemnum = None
    if lbracket >= 0 and (pos < 0 or lbracket < pos):
        rbracket = path.find(']')
        itemnum = int(path[lbracket + 1:rbracket])
        currentpath = path[0:lbracket]
        # keep the bracket for the next recurive depth
        nextpath = path[lbracket:] if lbracket > 0 else nextpath
    if type(d) is list:
        result = []
        if itemnum is not None:
            result.extend(getPathValues(d[itemnum], nextpath))
        else:
            for item in d:
                # still on the current path node
                result.extend(getPathValues(item, path))
        return result
    if pos < 0:
        if currentpath == '*':
            result = []
            for k, v in d.iteritems():
                result.append(v)
            return result
        return [d[currentpath]] if currentpath in d and d[currentpath] else []
    else:
        if currentpath == '*':
            result = []
            for k, v in d.iteritems():
                result.extend(getPathValues(v, nextpath))
            return result
        return getPathValues(d[currentpath], nextpath) if currentpath in d else []

def getValue(obj, path, defaultValue=None, convertFunction=None):
    """"Return the value as referenced by the path in the embedded set of dictionaries as referenced by an object
        obj is a node or edge
        path is a dictionary path: a.b.c
        convertFunction converts the value

        This function recurses
    """
    if not path:
        return convertFunction(obj) if convertFunction and obj is not None else (defaultValue if obj is None else obj)

    current = obj
    part = path
    splitpos = path.find(".")

    if splitpos > 0:
        part = path[0:splitpos]
        path = path[splitpos + 1:]
    else:
        path = None

    bpos = part.find('[')
    pos = 0
    if bpos > 0:
        pos = int(part[bpos + 1:-1])
        part = part[0:bpos]

    if part in current:
        current = current[part]
        if type(current) is list or type(current) is tuple:
            if bpos > 0:
                current = current[pos]
            else:
                result = []
                for item in current:
                    v = getValue(item, path, defaultValue=defaultValue, convertFunction=convertFunction)
                    if v:
                        result.append(v)
                return result
        return getValue(current, path, defaultValue=defaultValue, convertFunction=convertFunction)
    return defaultValue

class MaskgenThreadPool:

    def __init__(self,size):
        from multiprocessing.pool import ThreadPool
        if size > 1:
            self.thread_pool = ThreadPool(size)
        else:
            self.thread_pool = None

    def apply_async(self, func, args=(), kwds={}):
        if self.thread_pool is not None:
            return self.thread_pool.apply_async(func, args=args, kwds=kwds)
        else:
            from multiprocessing.pool import AsyncResult
            result = AsyncResult({},False)
            result._set(0,(True,func(*args, **kwds)))
            return result
