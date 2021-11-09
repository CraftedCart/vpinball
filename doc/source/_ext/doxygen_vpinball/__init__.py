import doxygen_vpinball.doxygen
import doxygen_vpinball.vbs_domain
from docutils import nodes
from sphinx.util.docutils import SphinxDirective


def setup(app):
    # Run doxygen to generate XML docs from the .idl
    app.connect("builder-inited", doxygen.run_doxygen)

    app.add_domain(vbs_domain.VbsDomain)

    return {
        "version": "0.1",
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
