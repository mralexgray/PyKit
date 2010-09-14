import WebKit

def cocoa_dom_property(name):
    def getter(self):
        value = getattr(self._w, name)()
        if isinstance(value, WebKit.DOMNode):
            value = DomNodeWrapper(value)
        return value

    def setter(self, value):
        if isinstance(value, DomNodeWrapper):
            value = value._w
        method_name = 'set' + name[0].upper() + name[1:] + '_'
        getattr(self._w, method_name)(value)

    getter.func_name = name
    setter.func_name = name
    return property(getter, setter)

class DomNodeWrapper(object):
    def __init__(self, wrapped):
        assert isinstance(wrapped, WebKit.DOMNode)
        self._w = wrapped

for name in ['firstChild', 'nextSibling', 'innerHTML', 'innerText',
             'nodeName']:
    setattr(DomNodeWrapper, name, cocoa_dom_property(name))


class ScriptWrapper(object):
    def __init__(self, script):
        assert isinstance(script, WebKit.WebScriptObject)
        self._s = script

    def __call__(self, javascript_src):
        value = self._s.evaluateWebScript_(javascript_src)
        if isinstance(value, WebKit.WebScriptObject):
            value = ScriptWrapper(value)
        return value

    def __getitem__(self, key):
        value = self._s.valueForKey_(key)
        if isinstance(value, WebKit.WebScriptObject):
            value = ScriptWrapper(value)
        return value
