# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------

project = u"mdsisclienttools"
copyright = u"2022, RRAP"
author = u"RRAP"

# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "myst_nb",
    "autoapi.extension",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
]
autoapi_dirs = ["../src"]

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = "sphinx_rtd_theme"


# Temporary workaround for 5.1.0 bug
import sphinx
if sphinx.__version__ == '5.1.0':
    # see https://github.com/sphinx-doc/sphinx/issues/10701
    # hope is it would get fixed for the next release

    # Although crash happens within NumpyDocstring, it is subclass of GoogleDocstring
    # so we need to overload method there
    from sphinx.ext.napoleon.docstring import GoogleDocstring
    from functools import wraps

    @wraps(GoogleDocstring._consume_inline_attribute)
    def _consume_inline_attribute_safe(self):
        try:
            return self._consume_inline_attribute_safe()
        except:
            return "", []

    GoogleDocstring._consume_inline_attribute = _consume_inline_attribute_safe
