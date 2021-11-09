from docutils import nodes
from sphinx import addnodes
from sphinx.locale import get_translation
import xml.etree.ElementTree as ET
from enum import Enum
import subprocess
import re
import os


# _ is a function used for translatable strings
MESSAGE_CATALOG_NAME = "doxygen_vpinball"
_ = get_translation(MESSAGE_CATALOG_NAME)


#: Maps COM/C++/IDL type names -> Visual Basic type names
_TYPENAME_REMAP = {
    "int": "Integer",
    "long": "Long",
    "float": "Single",
    "double": "Double",
    "BSTR": "String",
    "VARIANT_BOOL": "Boolean",
    "VARIANT": "Variant",
    "IDispatch": "Variant",
}


def _parametername_to_docutils_nodes(xml):
    node = nodes.field_name()
    node += addnodes.desc_name(text=xml.text)
    return [node]


def _simplesect_to_docutils_nodes(xml):
    kind = xml.attrib.get("kind")

    if kind == "return":
        return [nodes.strong(text=_("Returns:")), nodes.inline()]
    elif kind == "since":
        return [nodes.strong(text=_("Since version:")), nodes.inline()]
    else:
        return [nodes.inline()]


def _x_term_to_docutils_nodes(xml):
    xref = addnodes.pending_xref(
        "",
        nodes.Text(xml.text),
        refdomain="std",
        reftarget=xml.text,
        reftype="term",
    )

    xref_parent = nodes.inline()
    xref_parent += xref

    return [xref_parent]


#: Maps Doxygen XML tag names to functions that take said XML tag and make a docutils node from the text it starts with
#: Eg: For <para>Hello, <computeroutput>world</computeroutput>!</para>
#:     This will make a docutils paragraph node with text ``Hello, ``.
_DOXYGEN_TAG_TO_DOCUTILS_NODE = {
    "computeroutput": lambda xml: [nodes.literal(text=xml.text) if xml.text is not None else nodes.literal()],  # Inline code
    "para": lambda xml: [nodes.paragraph(text=xml.text) if xml.text is not None else nodes.paragraph()],  # Paragraph
    "sp": lambda xml: [nodes.inline(text=" ")],  # Space
    "ref": lambda xml: [nodes.inline(text=xml.text) if xml.text is not None else nodes.inline()],  # Reference link (TODO: Support these)

    # Stuff for code blocks
    "programlisting": lambda xml: [nodes.literal_block()],
    "codeline": lambda xml: [nodes.inline()],
    "highlight": lambda xml: [nodes.inline(text=xml.text) if xml.text is not None else nodes.inline()],

    # Parameter lists
    "parameterlist": lambda xml: [nodes.strong(text=_("Parameters:")), nodes.field_list()],
    "parameteritem": lambda xml: [nodes.field()],
    # parameternamelist is ignored
    "parametername": _parametername_to_docutils_nodes,
    "parameterdescription": lambda xml: [nodes.field_body(text=xml.text) if xml.text is not None else nodes.field_body()],

    "simplesect": _simplesect_to_docutils_nodes,

    # Custom doxygen commands
    "x-term": _x_term_to_docutils_nodes,
}


def _xml_dir(app):
    """Returns the directory containing generated doxygen XML files"""

    return os.path.join(app.outdir, "..", "doxygen_xml")


def _refid_for_compound(app, compound_name):
    """
    Returns the doxygen refid given a compound name

    For example, passing `VPinballLib::IBall` returns something like `interfaceVPinballLib_1_1IBall`.
    The file `interfaceVPinballLib_1_1IBall.xml` can then be looked up in `_xml_dir` for more info on its members and
    what not.
    """

    xml_index_file = os.path.join(_xml_dir(app), "index.xml")
    root = ET.parse(xml_index_file)

    out_nodes = []
    for compound in root.findall("./compound"):
        name = compound.find("./name").text
        if name == compound_name:
            return compound.attrib["refid"]

    # Not found
    return None


def xml_for_compound(app, compound_name):
    """
    Opens the XML file for a compound and parses it

    For example, passing `VPinballLib::IBall` will open `interfaceVPinballLib_1_1IBall.xml` and parse it with
    ElementTree.
    """

    xml_file = os.path.join(_xml_dir(app), f"{_refid_for_compound(app, compound_name)}.xml")
    return ET.parse(xml_file)


class ParamDir(Enum):
    """
    The direction for a parameter in IDL

    In params are given to a function for it to use, out params are references provided by its caller that a function
    can set.
    """

    IN = 0
    OUT = 1


class DoxygenParam:
    """
    A parsed function parameter or return value from Doxygen XML

    Don't construct this directly, instead use the ``parse_function`` function.

    Attributes:
        name: The name of the parameter (Eg: ``newVal``)
        type: The C++/COM type of the parameter, with any pointer suffix stripped (Eg: ``BSTR``)
              This can be converted to a VBScript type with the ``vbs_typename_for_com`` function
        dir: The direction (in/out), as a value from the ``ParamDir`` enum
        default_value: Default value of the parameter as a string, or None if there is no default
        TODO: Default value
    """

    def __init__(self, name, type, dir, default_value):
        self.name = name
        self.type = type
        self.dir = dir
        self.default_value = default_value


class DoxygenFunc:
    """
    A parsed function from Doxygen XML

    Don't construct this directly, instead use the ``parse_function`` function.

    Attributes:
        xml: The <memberdef> ElementTree XML tag for the function, as generated from Doxygen
        name: Name of the function (Eg: ``GetCustomParam``)
        args: List of ``DoxygenParam`` objects describing the function's arguments
        returns: ``DoxygenParam`` object describing the return type, or ``None`` if the function does not return a value
    """

    def __init__(self, xml, name, args, returns):
        self.xml = xml
        self.name = name
        self.args = args
        self.returns = returns


def _try_remove_pointer(typename):
    """
    Given a typename like ``BSTR *``, remove the pointer from it, returning ``BSTR``

    In the case that a type is not a pointer (Eg: ``int``), it will not be modified and the same value ``int`` will be
    returned.
    """

    return typename.rstrip("* ")


#: Regex:
#: (
#:   .+        Match a sequence of characters (Eg: ``defaultvalue``)...
#: )           ...and capture it...
#: \(          ...that is followed by some parens...
#:   (
#:     .+      ...that contain a sequence of characters inside of it (Eg: ``1``)...
#:   )         ...and capture that too
#: \)
_ATTR_WITH_VALUE_REGEX = re.compile(r"(.+)\((.+)\)")


def _split_function_attributes(attr_str):
    """
    Splits an attribute string like [in, defaultvalue(1)] into a dict like
    {
        "in": None,
        "defaultvalue": "1",
    }
    """

    # Attrs should be surrounded with [square brackets]
    assert attr_str[0] == "["
    assert attr_str[-1] == "]"

    # Strip off the [square brackets]
    attr_str = attr_str[1:-1]

    # Split on , and trim off whitespace
    attrs_split = [x.strip() for x in attr_str.split(",")]

    attrs = {}
    for attr in attrs_split:
        # Check if the attribute has a value (Eg: ``defaultvalue(1)``) or not (Eg: ``out``)
        with_value_match = _ATTR_WITH_VALUE_REGEX.fullmatch(attr)
        if with_value_match is not None:
            # It does have a value
            attr_name = with_value_match.group(1).strip()
            attr_value = with_value_match.group(2).strip()

            attrs[attr_name] = attr_value
        else:
            # It does not have a value
            attrs[attr] = None

    return attrs


def parse_function(member_xml):
    """
    Function signatures in IDL need get transformed for VBScript docs.
    Eg: HRESULT GetCustomParam(long index, [out, retval] BSTR *param) in C++ is used as if it were like
        BSTR GetCustomParam([in] long index) in VBSscipt

    An instance of type ``DoxygenFunc`` is returned.
    """

    # Example Doxygen memberdef for reference
    #
    # <memberdef
    #         kind="function"
    #         id="interfaceVPinballLib_1_1IBall_1a7b73ea25757cf5a090910e05dd21f856"
    #         prot="public"
    #         static="no"
    #         const="no"
    #         explicit="no"
    #         inline="no"
    #         virt="non-virtual">
    #     <type>HRESULT</type>
    #     <definition>HRESULT VPinballLib::IBall::DestroyBall</definition>
    #     <argsstring>([out, retval] int *pVal)</argsstring>
    #     <name>DestroyBall</name>
    #     <param>
    #         <attributes>[out, retval]</attributes>
    #         <type>int *</type>
    #         <declname>pVal</declname>
    #     </param>
    #     <briefdescription><!-- snip --></briefdescription>
    #     <detaileddescription><!-- snip --></detaileddescription>
    #     <inbodydescription></inbodydescription>
    #     <location file="/path/to/vpinball/vpinball.idl" line="2530" column="27"/>
    # </memberdef>
    #
    # We loop over all child tags of the <memberdef> tag, looking for <param> tags to parse (which will contain
    # VBScript function args and the return parameter).
    #
    # We'll also grab the name while we're at it

    name = None
    args = []
    returns = None

    for node in member_xml.find("."):  # Loop over direct children
        if node.tag == "name":
            # Found the function name
            name = node.text

        elif node.tag == "param":
            # Found a function parameter
            # This could either correspond to a regular argument, or a return value (if the param has attribute
            # `retval`)

            param_name = node.find("./declname").text

            # TODO: Support refs in <type> tags
            # Eg: <type><ref refid="interfaceVPinballLib_1_1IBall" kindref="compound">IBall</ref></type>
            param_type = _try_remove_pointer(node.find("./type").text or "TODO TODO TODO")

            # Check if this param has any attributes (Eg: `[out, retval]``) and parse them if so
            param_attr_node = node.find("./attributes")
            if param_attr_node is not None:
                param_attrs = _split_function_attributes(param_attr_node.text)
            else:
                param_attrs = {}

            # Check if this is an in or out param
            if "out" in param_attrs:
                param_dir = ParamDir.OUT
            else:
                param_dir = ParamDir.IN

            # Do a little bit of light processing on default value if we have one
            default_value = param_attrs.get("defaultvalue")
            if default_value == "0" and param_type == "VARIANT_BOOL":
                default_value = "False"
            elif param_type == "VARIANT_BOOL":
                default_value = "True"

            param = DoxygenParam(param_name, param_type, param_dir, default_value)

            # Check if this is a return value or regular function argument
            if "retval" in param_attrs:
                assert returns == None, f"Found multiple parameters with the retval attribute in function {name}"
                returns = param
            else:
                args.append(param)

    # Fail if we didn't get a <name> tag
    if name == None:
        raise ValueError("parse_function recieved some XML that had no <name> tag")

    return DoxygenFunc(member_xml, name, args, returns)


def docutils_nodes_for_description(xml):
    """
    Returns a list of docutils nodes given a Doxygen XML descriptionType node

    For example, the Doxygen XML ``<para>This defaults to <computeroutput>&amp;HFFFFFF</computeroutput></para>`` returns
    the docutils nodes ``<paragraph>This defaults to <literal>&HFFFFFF</literal></para>``.
    """

    out_nodes = []

    # Assume all code blocks will be in VBScript
    out_nodes.append(addnodes.highlightlang(lang="vbscript", force=True, linenothreshold=0))

    for node in xml.find("."):  # Loop over direct children
        convert_func = _DOXYGEN_TAG_TO_DOCUTILS_NODE.get(node.tag)
        if convert_func is None:
            convert_func = lambda xml: [nodes.inline(text=xml.text) if xml.text is not None else nodes.inline()]

        # Add node/text
        converted_nodes = convert_func(node)
        out_nodes.extend(converted_nodes)
        doc_node = converted_nodes[-1]

        # Add inner nodes
        doc_node.extend(docutils_nodes_for_description(node))

        # Special case for codeline: Add a newline at the end of each line
        if node.tag == "codeline":
            doc_node.append(nodes.Text("\n"))

        # Add tail (the text *after* the current node)
        if node.tail is not None and len(node.tail.strip()) > 0:
            out_nodes.append(nodes.Text(node.tail))

    return out_nodes


def vbs_typename_for_com(com_typename):
    """
    Returns the appropriate Visual Basic typename given a COM typename

    Unknown type names will return themselves

    Eg: float -> Single, BSTR -> String, Stroopwafel -> Stroopwafel
    """

    try:
        return _TYPENAME_REMAP[com_typename]
    except KeyError:
        return com_typename


def run_doxygen(app):
    """
    Run Doxygen to parse interfaces and documentation in vpinball.idl

    Doxygen will output XML files in the build directory, which we can then read in to generate Sphinx documentation.
    """

    doxyfile = os.path.join(app.srcdir, "..", "Doxyfile")
    subprocess.run(["doxygen", doxyfile], check=True)
