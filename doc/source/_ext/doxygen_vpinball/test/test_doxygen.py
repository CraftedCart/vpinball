import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(__file__, "../../..")))

from doxygen_vpinball import doxygen
from doxygen_vpinball.doxygen import ParamDir
import xml.etree.ElementTree as ET


def test_parse_function():
    xml = ET.fromstring("""
        <memberdef
                kind="function"
                id="interfaceVPinballLib_1_1IBall_1a7b73ea25757cf5a090910e05dd21f856"
                prot="public"
                static="no"
                const="no"
                explicit="no"
                inline="no"
                virt="non-virtual">
            <type>HRESULT</type>
            <definition>HRESULT VPinballLib::IBall::DestroyBall</definition>
            <argsstring>([out, retval] int *pVal)</argsstring>
            <name>DestroyBall</name>
            <param>
                <attributes>[in]</attributes>
                <type>int</type>
                <declname>testVal</declname>
            </param>
            <param>
                <type>BSTR *</type>
                <declname>testVal2</declname>
            </param>
            <param>
                <attributes>[out]</attributes>
                <type>BSTR *</type>
                <declname>outVal</declname>
            </param>
            <param>
                <attributes>[out, retval]</attributes>
                <type>int *</type>
                <declname>pVal</declname>
            </param>
            <briefdescription><!-- snip --></briefdescription>
            <detaileddescription><!-- snip --></detaileddescription>
            <inbodydescription></inbodydescription>
            <location file="/path/to/vpinball/vpinball.idl" line="2530" column="27"/>
        </memberdef>
    """)

    func = doxygen.parse_function(xml)

    assert func.xml == xml
    assert func.name == "DestroyBall"

    assert len(func.args) == 3

    assert func.args[0].name == "testVal"
    assert func.args[0].type == "int"
    assert func.args[0].dir == ParamDir.IN

    assert func.args[1].name == "testVal2"
    assert func.args[1].type == "BSTR"
    assert func.args[1].dir == ParamDir.IN

    assert func.args[2].name == "outVal"
    assert func.args[2].type == "BSTR"
    assert func.args[2].dir == ParamDir.OUT

    assert func.returns != None
    assert func.returns.name == "pVal"
    assert func.returns.type == "int"
    assert func.returns.dir == ParamDir.OUT


def test_split_function_attributes():
    attrs = doxygen._split_function_attributes("[in, defaultvalue(1)]")
    assert attrs == { "in": None, "defaultvalue": "1" }
