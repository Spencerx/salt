"""
Salt package
"""

import asyncio
import importlib
import os
import re
import sys
import warnings

# Aweful hack to keep salt-ssh tests passing with tornado >=6.4.2. Salt ssh
# needs to be transitioned to use a relenv environemnt by default. This should
# be removed when salt-ssh uses relenv or we no longer want salt-ssh to support
# older system python versions <3.8
if not hasattr(re, "Match"):
    re.Match = object()


if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


class NaclImporter:
    """
    Import hook to force PyNaCl to perform dlopen on libsodium with the
    RTLD_DEEPBIND flag. This is to work around an issue where pyzmq does a dlopen
    with RTLD_GLOBAL which then causes calls to libsodium to resolve to
    tweetnacl when it's been bundled with pyzmq.

    See:  https://github.com/zeromq/pyzmq/issues/1878
    """

    loading = False

    def find_module(self, module_name, package_path=None):
        if not NaclImporter.loading and module_name.startswith("nacl"):
            NaclImporter.loading = True
            return self
        return None

    def create_module(self, spec):
        dlopen = hasattr(sys, "getdlopenflags")
        if dlopen:
            dlflags = sys.getdlopenflags()
            # Use RTDL_DEEPBIND in case pyzmq was compiled with ZMQ_USE_TWEETNACL. This is
            # needed because pyzmq imports libzmq with RTLD_GLOBAL.
            if hasattr(os, "RTLD_DEEPBIND"):
                flags = os.RTLD_DEEPBIND | dlflags
            else:
                flags = dlflags
            sys.setdlopenflags(flags)
        try:
            mod = importlib.import_module(spec.name)
        finally:
            if dlopen:
                sys.setdlopenflags(dlflags)
        NaclImporter.loading = False
        sys.modules[spec.name] = mod
        return mod

    def exec_module(self, module):
        return None


# Try our importer first
sys.meta_path = [NaclImporter()] + sys.meta_path


# All salt related deprecation warnings should be shown once each!
warnings.filterwarnings(
    "once",  # Show once
    "",  # No deprecation message match
    DeprecationWarning,  # This filter is for DeprecationWarnings
    r"^(salt|salt\.(.*))$",  # Match module(s) 'salt' and 'salt.<whatever>'
    # Do *NOT* add append=True here - if we do, salt's DeprecationWarnings will
    # never show up
)

# Filter the backports package UserWarning about being re-imported
warnings.filterwarnings(
    "ignore",
    "^Module backports was already imported from (.*), but (.*) is being added to sys.path$",
    UserWarning,
    append=True,
)

# Filter the setuptools UserWarning until we stop relying on distutils
warnings.filterwarnings(
    "ignore",
    message="Setuptools is replacing distutils.",
    category=UserWarning,
    module="_distutils_hack",
)

warnings.filterwarnings(
    "ignore",
    message="invalid escape sequence.*",
    category=DeprecationWarning,
)

warnings.filterwarnings(
    "ignore",
    "Deprecated call to `pkg_resources.declare_namespace.*",
    category=DeprecationWarning,
)
warnings.filterwarnings(
    "ignore",
    ".*pkg_resources is deprecated as an API.*",
    category=DeprecationWarning,
)


def __define_global_system_encoding_variable__():
    import builtins
    import sys

    # Define the detected encoding as a built-in variable for ease of use
    setattr(builtins, "__salt_system_encoding__", sys.getdefaultencoding())

    # This is now garbage collectable
    del builtins
    del sys


__define_global_system_encoding_variable__()

# This is now garbage collectable
del __define_global_system_encoding_variable__

# Make sure Salt's logging tweaks are always present
# DO NOT MOVE THIS IMPORT
# pylint: disable=unused-import
import salt._logging  # isort:skip

# pylint: enable=unused-import
