"""\
XRC code generator

Generates the xml code for the app in XRC format.
Calls the appropriate ``writers'' of the various objects. These functions
return an instance of XrcObject

@copyright: 2002-2007 Alberto Griggio
@copyright: 2012-2016 Carsten Grohmann
@license: MIT (see LICENSE.txt) - THIS PROGRAM COMES WITH NO WARRANTY
"""

from xml.sax.saxutils import escape, quoteattr
from codegen import BaseLangCodeWriter
from collections import OrderedDict
import common, compat, errors
import new_properties as np
import wcodegen


class XrcObject(wcodegen.XrcWidgetCodeWriter):
    "Class to produce the XRC code for a given widget. This is a base class which does nothing"

    def __init__(self, klass=None):
        wcodegen.XrcWidgetCodeWriter.__init__(self, klass)
        self.properties = {}
        self.children = []  # sub-objects

    def write_child_prologue(self, child, output, ntabs):
        pass

    def write_child_epilogue(self, child, output, ntabs):
        pass

    def write_property(self, name, val, outfile, ntabs):
        pass

    def write(self, output, ntabs, properties=None):
        pass

    def warning(self, msg):
        "Show a warning message"
        self._logger.warning(msg)



class SizerItemXrcObject(XrcObject):
    "XrcObject to handle sizer items"

    def __init__(self, obj, proportion, flag, border):
        XrcObject.__init__(self)
        self.obj = obj  # the XrcObject representing the widget
        self.proportion = proportion
        self.flag = flag
        self.border = border

    def write(self, output, ntabs, properties=None):
        tabs = self.tabs(ntabs)
        tabs1 = self.tabs(ntabs + 1)
        output.append(tabs + '<object class="sizeritem">\n')
        if self.proportion != '0':
            output.append(tabs1 + '<option>%s</option>\n' % self.proportion)
        if self.flag and self.flag != '0':
            output.append(tabs1 + '<flag>%s</flag>\n' % self.cn_f(self.flag))
        if self.border != '0':
            output.append(tabs1 + '<border>%s</border>\n' % self.border)
        # write the widget
        self.obj.write(output, ntabs + 1)
        output.append(tabs + '</object>\n')



class SpacerXrcObject(XrcObject):
    "XrcObject to handle widgets"

    def __init__(self, size_str, option, flag, border):
        XrcObject.__init__(self)
        self.size_str = size_str
        self.proportion = option
        self.flag = flag
        self.border = border

    def write(self, output, ntabs):
        tabs = self.tabs(ntabs)
        tabs1 = self.tabs(ntabs + 1)
        output.append(tabs + '<object class="spacer">\n')
        output.append(tabs1 + '<size>%s</size>\n' % self.size_str.strip())
        if self.proportion != '0':
            output.append(tabs1 + '<option>%s</option>\n' % self.proportion)
        if self.flag and self.flag != '0':
            output.append(tabs1 + '<flag>%s</flag>\n' % self.cn_f(self.flag))
        if self.border != '0':
            output.append(tabs1 + '<border>%s</border>\n' % self.border)
        output.append(tabs + '</object>\n')



class DefaultXrcObject(XrcObject):
    "Standard XrcObject for every widget, used if no specific XrcObject is available"

    def __init__(self, widget):
        XrcObject.__init__(self, widget.klass)
        self.widget = widget
        self.name = widget.name
        self.klass = widget.base  # custom classes aren't allowed in XRC
        self.subclass = widget.klass

    def write_property(self, name, val, output, ntabs):
        if not val:
            return

        if isinstance(val, np.BitmapProperty):
            # rename: no '..._bitmap' and some renames
            if name.endswith('_bitmap'):
                name = name[:-7]
            if   name=="pressed": name = "selected"
            elif name=="current": name = "hover"

            prop = self._format_bitmap_property(name, val.get_value(), ntabs)
        else:
            prop = common.format_xml_prop(name, val, ntabs)

        output.append(prop)

    def _format_bitmap_property(self, name, val, ntabs):
        "Return formatted bitmap/icon XRC property (as string)."

        if val.startswith('art:'):
            content = val[4:]
            elements = [item.strip() for item in content.split(',')]
            art_id = elements[0]
            art_client = elements[1]

            if art_client != 'wxART_OTHER':
                return common.format_xml_prop( name, '', ntabs, stock_id=art_id, stock_client=art_client )
            else:
                return common.format_xml_prop(name, u'', ntabs, stock_id=art_id)

        elif val.startswith('code:') or val.startswith('empty:') or val.startswith('var:'):
            self._logger.warn( _('XRC: Unsupported bitmap statement "%s" for %s "%s"'), val, self.klass, self.name )
            return None

        return common.format_xml_prop(name, val, ntabs)

    def write(self, output, ntabs, properties=None):
        if properties is None: properties = {}
        if "name" in properties:
            name = properties["name"]
            del properties["name"]
        else:
            name = self.name
        if self.widget.is_sizer:
            output.append(self.tabs(ntabs) + '<object class=%s>\n' % quoteattr(self.klass))
        else:
            if self.subclass and self.subclass != self.klass:
                output.append(self.tabs(ntabs) + '<object class=%s name=%s subclass=%s>\n' % (
                                                quoteattr(self.klass), quoteattr(name), quoteattr(self.subclass)) )
            else:
                output.append(self.tabs(ntabs) + '<object class=%s name=%s>\n' % (quoteattr(self.klass), quoteattr(name)))
        tab_str = self.tabs(ntabs + 1)
        # write the properties
        import edit_sizers
        active_properties = self.widget.get_properties(without=set(edit_sizers.SizerBase.MANAGED_PROPERTIES))

        font = None
        for prop in active_properties:
            if not prop.is_active(): continue
            if prop.value==prop.default_value: continue
            name = prop.name
            if name in properties: continue  # set already
            value = None
            if name=='foreground':
                value = prop.get_string_value()
                if not value.startswith('#'):
                    # XRC does not support colors from system settings
                    continue
                name = 'fg'
            elif name=='background':
                value = prop.get_string_value()
                if not value.startswith('#'):
                    # XRC does not support colors from system settings
                    continue
                name = "bg"
            elif name=='font':
                font = prop.value
                continue
            elif name=="style":
                if hasattr(prop, "value_set"):
                    if prop.value_set==prop.default_value: continue
                value = prop.get_string_value()
                if value: value = self.cn_f(value)
            elif name=='id':
                continue  # id has no meaning for XRC
            elif name=='events':
                for win_id, event, handler, event_type in self.get_event_handlers(self.widget):
                    output.append(tab_str + '<handler event=%s>%s</handler>\n' % (quoteattr(event), escape(handler)))
                continue
            elif name=='disabled':
                # 'disabled' property is actually 'enabled' for XRC
                if prop.get():
                    properties['enabled'] = '0'
                continue
            elif name=='custom_base' in self.properties:
                # custom base classes are ignored for XRC...
                continue
            elif name=='extraproperties':
                value = prop.get()
                if value:
                    properties.update(value)
                continue
            if isinstance(prop, np.BitmapProperty):
                value = prop
            else:
                if value is None: value = prop.get_string_value()
                if value is None: continue
            properties[name] = value

        for name in sorted( properties.keys() ):
            value = properties[name]
            if value is None: continue
            self.write_property( name, value, output, ntabs + 1)
        # write the font, if present
        if font:
            output.append(tab_str + '<font>\n')
            tab_str = self.tabs(ntabs + 2)

            data = sorted( zip(['size','family','style','weight','underlined','face'], font) )
            for key, val in data:
                if isinstance(val, int): val = str(val)
                if val:
                    output.append(tab_str + '<%s>%s</%s>\n' % (escape(key), escape(val), escape(key)))
            output.append(self.tabs(ntabs + 1) + '</font>\n')
        # write the children
        for c in self.children:
            self.write_child_prologue(c, output, ntabs + 1)
            c.write(output, ntabs + 1)
            self.write_child_epilogue(c, output, ntabs + 1)
        output.append(self.tabs(ntabs) + '</object>\n')



class NotImplementedXrcObject(XrcObject):
    """XrcObject used when no code for the widget can be generated (for
    example, because XRC does not currently handle such widget)"""

    def __init__(self, code_obj):
        XrcObject.__init__(self)
        self.code_obj = code_obj

    def write(self, output, ntabs):
        msg = 'code generator for %s objects not available' % self.code_obj.base
        self.warning('%s' % msg)
        output.append( '%s%s\n' % (self.tabs(ntabs), self._format_comment(msg)) )



class XRCCodeWriter(BaseLangCodeWriter, wcodegen.XRCMixin):
    "Code writer class for writing XRC XML code out of the designed GUI elements"

    # dict of active XrcObject instances: during the code generation it stores all the non-sizer objects that have
    # children (i.e. frames, dialogs, panels, notebooks, etc.), while at the end of the code generation,
    # before finalize is called, it contains only the true toplevel objects (frames and dialogs), and is used to write
    # their XML code (see finalize). The other objects are deleted when add_object is called with their corresponding
    # code_object as argument (see add_object)
    xrc_objects = None

    property_writers = {}  # dict of dicts of property handlers specific for a widget; keys: class names of the widgets
    obj_builders = {}      # Dictionary of ``writers'' for the various objects

    tmpl_encoding = '<?xml version="1.0" encoding="%s"?>\n'
    tmpl_generated_by = '<!-- %(generated_by)s -->'

    use_names_for_binding_events = False

    # inject different XRC objects
    XrcObject = XrcObject
    SizerItemXrcObject = SizerItemXrcObject
    SpacerXrcObject = SpacerXrcObject
    DefaultXrcObject = DefaultXrcObject
    NotImplementedXrcObject = NotImplementedXrcObject

    def __init__(self):
        BaseLangCodeWriter.__init__(self)
        # Inject to all classed derived from WrcObject
        if not hasattr(XrcObject, 'tabs'):
            XrcObject.tabs = self.tabs
        if not hasattr(XrcObject, '_format_comment'):
            XrcObject._format_comment = self._format_comment

    def init_lang(self, app):
        # for now we handle only single-file code generation
        if self.multiple_files:
            raise errors.WxgXRCMultipleFilesNotSupported()

        # overwrite existing sources always
        self._overwrite = True

        self.output_file_name = app.output_path
        self.out_file = []
        self.out_file.append('\n<resource version="2.3.0.1">\n')
        self.curr_tab = 1
        self.xrc_objects = OrderedDict()

    def finalize(self):
        # write the code for every toplevel object
        for obj in self.xrc_objects.values():
            obj.write(self.out_file, 1)
        self.out_file.append('</resource>\n')
        # store the contents to file
        self.save_file( self.output_file_name, self.out_file )
        self.out_file = None

    def _clean_up_node(self, node):
        if hasattr(node.widget, "xrc"):
            del node.widget.xrc
        for c in node.children or []:
            self._clean_up_node(c)

    def clean_up(self, root):
        # root is a Tree node
        self._clean_up_node(root)

    def add_app(self, app, top_win_class):
        "In the case of XRC output, there's no wxApp code to generate"
        pass

    def add_object(self, sub_obj):
        "Adds the object sub_obj to the XRC tree. The first argument is unused."
        # what we need in XRC is not top_obj, but sub_obj's true parent we don't need the sizer, but the window
        top_obj = sub_obj.node.parent.widget
        while top_obj.is_sizer:
            top_obj = top_obj.node.parent.widget
        builder = self.obj_builders.get( sub_obj.base, DefaultXrcObject )
        try:
            # check whether we already created the xrc_obj
            xrc_obj = sub_obj.xrc
        except AttributeError:
            xrc_obj = builder(sub_obj)  # builder functions must return a subclass of XrcObject
            sub_obj.xrc = xrc_obj
        else:
            # if we found it, remove it from the self.xrc_objects dictionary
            # (if it was there, i.e. the object is not a sizer), because this isn't a true toplevel object
            if sub_obj in self.xrc_objects:
                del self.xrc_objects[sub_obj]
        # let's see if sub_obj's parent already has an XrcObject: if so, it's temporarily stored in self.xrc_objects
        if top_obj in self.xrc_objects:
            top_xrc = self.xrc_objects[top_obj]
        else:
            # ...otherwise, create it and store it in the self.xrc_objects dict
            top_xrc = self.obj_builders.get( top_obj.base, DefaultXrcObject )(top_obj)
            top_obj.xrc = top_xrc
            self.xrc_objects[top_obj] = top_xrc
        top_obj.xrc.children.append(xrc_obj)

    def add_sizeritem(self, unused, sizer, obj, option, flag, border):
        "Adds a sizeritem to the XRC tree. The first argument is unused."
        # what we need in XRC is not toplevel, but sub_obj's true parent
        toplevel = obj.node.parent.widget
        while toplevel.is_sizer:
            toplevel = toplevel.node.parent.widget

        top_xrc = toplevel.xrc
        obj_xrc = obj.xrc
        try:
            sizer_xrc = sizer.xrc
        except AttributeError:
            # if the sizer has not an XrcObject yet, create it now
            sizer_xrc = self.obj_builders.get( sizer.base, DefaultXrcObject )(sizer)
            sizer.xrc = sizer_xrc
        # we now have to move the children from 'toplevel' to 'sizer'
        index = top_xrc.children.index(obj_xrc)
        if obj.klass == 'spacer':
            w = obj.properties.get('width', '0')
            h = obj.properties.get('height', '0')
            obj_xrc = SpacerXrcObject( '%s, %s' % (w, h), str(option), str(flag), str(border) )
            sizer.xrc.children.append(obj_xrc)
        elif obj.klass == 'sizerslot':
            obj_xrc = SpacerXrcObject( '0, 0', '0', '0', '0' )
            sizer.xrc.children.append(obj_xrc)
        else:
            sizeritem_xrc = SizerItemXrcObject( obj_xrc, str(option), str(flag), str(border) )
            sizer.xrc.children.append(sizeritem_xrc)
        del top_xrc.children[index]

    def add_spacer(self, topl, sizer, obj=None, option=0, flag='0', border=0):
        if obj is not None:
            w = obj.width
            h = obj.height
        else:
            h = w = 0
        obj_xrc = SpacerXrcObject( '%s, %s' % (w,h), str(option), str(flag), str(border) )
        if not hasattr(sizer, "xrc"):  # if the sizer has not an XrcObject yet, create it now
            sizer.xrc = self.obj_builders.get( sizer.base, DefaultXrcObject )(sizer)
        sizer.xrc.children.append(obj_xrc)

    def add_class(self, code_obj):
        """Add class behaves very differently for XRC output than for other languages (i.e. python):
        since custom classes are not supported in XRC, this has effect only for true toplevel widgets, i.e. frames and
        dialogs. For other kinds of widgets, this is equivalent to add_object"""
        if not code_obj in self.xrc_objects:
            builder = self.obj_builders.get( code_obj.base, DefaultXrcObject )
            xrc_obj = builder(code_obj)
            code_obj.xrc = xrc_obj
            # add the xrc_obj to the dict of the toplevel ones
            self.xrc_objects[code_obj] = xrc_obj

    def generate_code_id(self, obj, id=None):
        return '', ''

    def _format_comment(self, msg):
        return '<!-- %s -->' % escape(msg.rstrip())

    def _quote_str(self, s):
        return s


writer = XRCCodeWriter()    # The code writer is an instance of XRCCodeWriter

language = writer.language  # Language generated by this code generator
