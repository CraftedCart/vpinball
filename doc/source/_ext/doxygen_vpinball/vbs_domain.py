from doxygen_vpinball import doxygen
from doxygen_vpinball.doxygen import ParamDir
from sphinx import addnodes
from sphinx.locale import get_translation
from sphinx.directives import ObjectDescription
from sphinx.domains import Domain, Index, ObjType
from sphinx.roles import XRefRole
from sphinx.util.nodes import make_refnode
from docutils.parsers.rst import directives
from docutils import nodes
from collections import defaultdict, namedtuple
from typing import Dict


# _ is a function used for translatable strings
MESSAGE_CATALOG_NAME = "doxygen_vpinball"
_ = get_translation(MESSAGE_CATALOG_NAME)


# Sphinx needs objects to be represented as tuples with many items
# but it gets unweildly quickly, so let's assign names to each item
DomainObj = namedtuple("DomainObj", "name dispname type docname anchor priority")
IndexObj = namedtuple("IndexObj", "name subtype docname anchor extra qualifier description")


def _each_property(xml_root):
    """Yields fields given the root element of a Doxygen XML file"""

    for compound in xml_root.findall("./compounddef/sectiondef/memberdef"):
        if compound.attrib["kind"] == "property":
            yield compound


def _each_function(xml_root):
    """Yields functions given the root element of a Doxygen XML file"""

    for compound in xml_root.findall("./compounddef/sectiondef/memberdef"):
        if compound.attrib["kind"] == "function":
            yield compound


def _add_property_summary_table(node, class_name, xml_root):
    """Adds a table near the top of a class's API documentation with summaries of each property"""

    properties = list(_each_property(xml_root))
    if len(properties) == 0:
        return

    table = nodes.table()
    node += table

    # Create a table group and set column width proportions
    table_group = nodes.tgroup(
        "",  # Empty source
        nodes.colspec(colwidth=30),
        nodes.colspec(colwidth=70),
        cols=2
    )
    table += table_group

    # Add heading row
    table_heading = nodes.thead(
        "",  # Empty source
        nodes.row(
            "",  # Empty source
            nodes.entry("", nodes.paragraph(text=_("Property"))),
            nodes.entry("", nodes.paragraph(text=_("Description")))
        )
    )
    table_group += table_heading

    # Add body rows
    table_body = nodes.tbody()
    table_group += table_body

    for compound in properties:
        name = compound.find("./name").text

        xref = addnodes.pending_xref(
            "",
            nodes.Text(name),
            refdomain="vbs",
            reftarget=f"vbs.{class_name}.{name}",
            reftype="property"
        )
        xref_parent = addnodes.desc_name()
        xref_parent += xref

        description_node = nodes.entry()
        description_node.extend(doxygen.docutils_nodes_for_description(compound.find("./briefdescription")))

        table_body += nodes.row(
            "",  # Empty source
            nodes.entry("", xref_parent),  # Property column
            description_node,  # Description column
        )


def _add_function_summary_table(node, class_name, xml_root, title):
    """Adds a table near the top of a class's API documentation with summaries of each function"""

    functions = list(_each_function(xml_root))
    if len(functions) == 0:
        return

    table = nodes.table()
    node += table

    # Create a table group and set column width proportions
    table_group = nodes.tgroup(
        "",  # Empty source
        nodes.colspec(colwidth=30),
        nodes.colspec(colwidth=70),
        cols=2
    )
    table += table_group

    # Add heading row
    table_heading = nodes.thead(
        "",  # Empty source
        nodes.row(
            "",  # Empty source
            nodes.entry("", nodes.paragraph(text=title)),
            nodes.entry("", nodes.paragraph(text=_("Description")))
        )
    )
    table_group += table_heading

    # Add body rows
    table_body = nodes.tbody()
    table_group += table_body

    for compound in functions:
        name = compound.find("./name").text

        xref = addnodes.pending_xref(
            "",
            nodes.Text(name),
            refdomain="vbs",
            reftarget=f"vbs.{class_name}.{name}",
            reftype="method"
        )
        xref_parent = addnodes.desc_name()
        xref_parent += xref

        description_node = nodes.entry()
        description_node.extend(doxygen.docutils_nodes_for_description(compound.find("./briefdescription")))

        table_body += nodes.row(
            "",  # Empty source
            nodes.entry("", xref_parent),  # Method column
            description_node,  # Description column
        )


def _add_class_properties(node, class_name, xml_root):
    """Adds docutils nodes to ``node`` containing detailed descriptions for each property in a class"""

    for property_xml in _each_property(xml_root):
        def_list = nodes.definition_list()
        def_list.set_class("attribute")  # For styling with style.css
        node += def_list

        name = property_xml.find("./name").text
        com_type = property_xml.find("./type").text
        vbs_type = doxygen.vbs_typename_for_com(com_type)

        # Check if the property can be set/get
        settable = property_xml.attrib["settable"] == "yes"
        gettable = property_xml.attrib["gettable"] == "yes"

        term = nodes.term()
        def_list += term

        term += addnodes.desc_annotation(text="Property ")
        term += addnodes.desc_name(text=name)
        term += addnodes.desc_annotation(text=": ")
        term += addnodes.desc_type(text=vbs_type)

        # This ID must be the same as the anchor names generated by VbsDomain.add_class_member
        term["ids"].append("vbs-" + class_name + "-" + name)

        # Add a note if read-only/write-only
        if settable and not gettable:
            term += addnodes.desc_annotation(text=_(" (Write-only)"))
        elif gettable and not settable:
            term += addnodes.desc_annotation(text=_(" (Read-only)"))

        member_def = nodes.definition()
        def_list += member_def
        member_def.extend(doxygen.docutils_nodes_for_description(property_xml.find("./briefdescription")))
        member_def.extend(doxygen.docutils_nodes_for_description(property_xml.find("./detaileddescription")))


def _add_class_functions(node, class_name, xml_root):
    """Adds docutils nodes to ``node`` containing detailed descriptions for each function in a class"""

    for func_xml in _each_function(xml_root):
        func = doxygen.parse_function(func_xml)

        def_list = nodes.definition_list()
        def_list.set_class("method")  # For styling with style.css
        node += def_list

        term = nodes.term()
        def_list += term

        # Say if this is a Sub (returns void) or Function (returns a value)
        if func.returns is not None:
            term += addnodes.desc_annotation(text="Function ")
        else:
            term += addnodes.desc_annotation(text="Sub ")

        term += addnodes.desc_name(text=func.name)

        arg_list = addnodes.desc_parameterlist()
        term += arg_list

        # Add function arguments
        for arg in func.args:
            arg_node = addnodes.desc_parameter()
            arg_list += arg_node

            arg_node += addnodes.desc_sig_name(text=arg.name)
            arg_node += addnodes.desc_annotation(text=": ")
            arg_node += addnodes.desc_type(text=doxygen.vbs_typename_for_com(arg.type))

            # If this is an out param, mark it as such
            if arg.dir == ParamDir.OUT:
                arg_node += addnodes.desc_annotation(text=_(" (out)"))

            # If we have a default value, note it here too
            if arg.default_value is not None:
                arg_node += addnodes.desc_annotation(text=" = ")
                arg_node += addnodes.desc_sig_element(text=arg.default_value)

        # Add return type after an arrow if there is one
        # Looks a bit like `-> Integer`
        if func.returns is not None:
            term += addnodes.desc_returns()
            term += addnodes.desc_type(text=doxygen.vbs_typename_for_com(func.returns.type))

        # This ID must be the same as the anchor names generated by VbsDomain.add_class_member
        term["ids"].append("vbs-" + class_name + "-" + func.name)

        member_def = nodes.definition()
        def_list += member_def
        member_def.extend(doxygen.docutils_nodes_for_description(func_xml.find("./briefdescription")))
        member_def.extend(doxygen.docutils_nodes_for_description(func_xml.find("./detaileddescription")))


def _add_class_events(node, class_name, xml_root):
    """Adds docutils nodes to ``node`` containing detailed descriptions for each event function in a class"""

    for func_xml in _each_function(xml_root):
        func = doxygen.parse_function(func_xml)

        def_list = nodes.definition_list()
        def_list.set_class("method")  # For styling with style.css
        node += def_list

        term = nodes.term()
        def_list += term

        term += addnodes.desc_annotation(text="Event ")
        term += addnodes.desc_addname(text="ObjectName_")
        term += addnodes.desc_name(text=func.name)

        arg_list = addnodes.desc_parameterlist()
        term += arg_list

        # Add function arguments
        for arg in func.args:
            arg_node = addnodes.desc_parameter()
            arg_list += arg_node

            arg_node += addnodes.desc_sig_name(text=arg.name)
            arg_node += addnodes.desc_annotation(text=": ")
            arg_node += addnodes.desc_type(text=doxygen.vbs_typename_for_com(arg.type))

            # If this is an out param, mark it as such
            if arg.dir == ParamDir.OUT:
                arg_node += addnodes.desc_annotation(text=_(" (out)"))

            # If we have a default value, note it here too
            if arg.default_value is not None:
                arg_node += addnodes.desc_annotation(text=" = ")
                arg_node += addnodes.desc_sig_element(text=arg.default_value)

        # Add return type after an arrow if there is one
        # Looks a bit like `-> Integer`
        if func.returns is not None:
            term += addnodes.desc_returns()
            term += addnodes.desc_type(text=doxygen.vbs_typename_for_com(func.returns.type))

        # This ID must be the same as the anchor names generated by VbsDomain.add_class_member
        term["ids"].append("vbs-" + class_name + "-" + func.name)

        member_def = nodes.definition()
        def_list += member_def
        member_def.extend(doxygen.docutils_nodes_for_description(func_xml.find("./briefdescription")))
        member_def.extend(doxygen.docutils_nodes_for_description(func_xml.find("./detaileddescription")))


def _add_class_members(app, node, class_name, interface_compound_name, events_compound_name):
    """
    Adds docutils nodes to ``node`` for summaries and detailed descriptions for all members of a class

    Summaries of all properties/functions are added in tables, before more detailed descriptions are added lower down
    the page. Documentation is pulled from generated Doxygen XML files.

    :param app: The Sphinx application
    :param node: The docutils node to append to
    :param interface_compound_name: The name of the interface to generate documentation for (Eg: ``VPinballLib::IBall``)
    :param events_compound_name: The name of the interface for object events (or None)
    """

    interface_root = doxygen.xml_for_compound(app, interface_compound_name)
    if events_compound_name is not None:
        events_root = doxygen.xml_for_compound(app, events_compound_name)

    # Add summary table for each item
    _add_property_summary_table(node, class_name, interface_root)
    _add_function_summary_table(node, class_name, interface_root, _("Method"))

    if events_compound_name is not None:
        _add_function_summary_table(node, class_name, events_root, _("Event"))

    class_def = nodes.definition()
    node += class_def

    _add_class_properties(class_def, class_name, interface_root)
    _add_class_functions(class_def, class_name, interface_root)

    if events_compound_name is not None:
        _add_class_events(class_def, class_name, events_root)



class ClassDirective(ObjectDescription):
    """
    A directive that describes a COM accessible class

    Requires an "interface" option with the name of the COM interface associated with the class

    Example:
    .. vbs:class:: Ball
       :interface: VPinballLib::IBall
    """

    has_content = True
    required_arguments = 1
    option_spec = {
        "interface": directives.unchanged_required,
        "events": directives.unchanged_required,
    }

    def handle_signature(self, sig, signode):
        signode += addnodes.desc_annotation(text="Class ")
        signode += addnodes.desc_name(text=sig)

        # Store this for later use in self.transform_content()
        self._class_name = sig

        return sig

    def add_target_and_index(self, name_cls, sig, signode):
        # This ID must be the same as the anchor names generated by VbsDomain.add_class
        signode["ids"].append("vbs-" + sig)

        domain = self.env.get_domain("vbs")
        domain.add_class(sig)

        # Add members of the class
        interface = self.options["interface"]
        interface_root = doxygen.xml_for_compound(self.env.app, interface)

        events = self.options.get("events")  # May be None
        if events is not None:
            events_root = doxygen.xml_for_compound(self.env.app, events)

        for compound in _each_property(interface_root):
            domain.add_class_member(sig, compound.find("./name").text, "property")
        for compound in _each_function(interface_root):
            domain.add_class_member(sig, compound.find("./name").text, "method")

        if events is not None:
            for compound in _each_function(events_root):
                domain.add_class_member(sig, compound.find("./name").text, "event")

    def transform_content(self, contentnode):
        super().transform_content(contentnode)

        interface = self.options["interface"]
        events = self.options.get("events")  # May be None
        _add_class_members(self.env.app, contentnode, self._class_name, interface, events)


class GlobalDirective(ObjectDescription):
    """
    A directive that describes a COM accessible interface with globals

    Requires an "interface" option with the name of the COM interface

    Example:
    .. vbs:globals::
       :interface: VPinballLib::IBall
    """

    has_content = True
    required_arguments = 1
    option_spec = {
        "interface": directives.unchanged_required,
    }

    def handle_signature(self, sig, signode):
        signode += addnodes.desc_annotation(text=sig)

        # Store this for later use in self.transform_content()
        self._global_name = sig

        return sig

    def add_target_and_index(self, name_cls, sig, signode):
        # This ID must be the same as the anchor names generated by VbsDomain.add_class
        signode["ids"].append("vbs-" + sig)

        domain = self.env.get_domain("vbs")
        domain.add_class(sig)

        # Add members
        interface = self.options["interface"]
        interface_root = doxygen.xml_for_compound(self.env.app, interface)

        for compound in _each_property(interface_root):
            domain.add_class_member(sig, compound.find("./name").text, "property")
        for compound in _each_function(interface_root):
            domain.add_class_member(sig, compound.find("./name").text, "method")

    def transform_content(self, contentnode):
        super().transform_content(contentnode)

        interface = self.options["interface"]
        _add_class_members(self.env.app, contentnode, self._global_name, interface, None)


class ApiIndex(Index):
    """Provides the VBS API index"""

    name = "apiindex"
    localname = _("API Index")

    # Intentionally lowercase to match Sphinx's lowercase `index` button that shows up next to here
    shortname = _("api")

    def generate(self, docnames=None):
        content = defaultdict(list)

        # Sort the list of items in alphabetical order
        #  classes = filter(lambda obj: obj.type == "class", self.domain.get_objects())
        items = sorted(self.domain.get_objects(), key=lambda obj: obj.name)

        # Generate the expected output, shown below, from the above using the first letter of the item as a key to
        # group things
        for item in items:
            content[item.dispname[0].lower()].append(IndexObj(
                item.dispname,  # name
                0,  # subtype
                item.docname,  # docname
                item.anchor,  # anchor
                item.docname,  # extra
                "",  # qualifier
                item.type  # description
            ))

        # Convert the dict to the sorted list of tuples expected
        content = sorted(content.items())

        return content, True


class VbsDomain(Domain):
    name = "vbs"
    label = "Visual Basic Scripting Edition"

    # TODO: Figure out what the purpose of this is and how it relates to anything
    object_types: Dict[str, ObjType] = {
        "class": ObjType(_("class"), "class"),
        "method": ObjType(_("method"), "meth"),
    }

    roles = {
        "ref": XRefRole()
    }

    directives = {
        "class": ClassDirective,
        "global": GlobalDirective,
    }

    indices = {
        ApiIndex,
    }

    initial_data = {
        # Object list
        # Where an object is a DomainObj tuple (name, dispname, type, docname, anchor, priority)
        # Objects can be classes, functions, properties, etc.
        "objects": [],
    }

    def get_full_qualified_name(self, node):
        return "{}.{}".format("vbs", node.arguments[0])

    def get_objects(self):
        for obj in self.data["objects"]:
            yield(obj)


    def resolve_xref(self, env, fromdocname, builder, typ, target, node, contnode):
        match = [(docname, anchor) for name, dispname, typ, docname, anchor, prio in self.get_objects() if name == target]

        if len(match) > 0:
            todocname = match[0][0]
            targ = match[0][1]

            return make_refnode(builder, fromdocname, todocname, targ, contnode, targ)
        else:
            print("Awww, found nothing")
            return None

    def add_class(self, class_name):
        """Add a new class to the domain"""

        name = "vbs.{}".format(class_name)
        anchor = "vbs-{}".format(class_name)

        # name, dispname, type, docname, anchor, priority
        self.data["objects"].append(DomainObj(name, class_name, "class", self.env.docname, anchor, 0))

    def add_class_member(self, class_name, member_name, type):
        """
        Add a member (property or function) of a class to the domain

        Used for generating indices later
        """

        name = "vbs.{}.{}".format(class_name, member_name)
        anchor = "vbs-{}-{}".format(class_name, member_name)

        # name, dispname, type, docname, anchor, priority
        self.data["objects"].append(DomainObj(name, member_name, type, self.env.docname, anchor, 0))
