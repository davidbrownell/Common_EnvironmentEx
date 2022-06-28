# ----------------------------------------------------------------------
# |
# |  LazyContainer.py
# |
# |  David Brownell <db@DavidBrownell.com>
# |      2022-06-17 08:09:29
# |
# ----------------------------------------------------------------------
# |
# |  Copyright David Brownell 2022
# |  Distributed under the Boost Software License, Version 1.0. See
# |  accompanying file LICENSE_1_0.txt or copy at
# |  http://www.boost.org/LICENSE_1_0.txt.
# |
# ----------------------------------------------------------------------
"""Contains the LazyContainer object"""

import copy
import os
import types

from typing import Callable, Generic, Optional, TypeVar

import CommonEnvironment

# ----------------------------------------------------------------------
_script_fullpath                            = CommonEnvironment.ThisFullpath()
_script_dir, _script_name                   = os.path.split(_script_fullpath)
# ----------------------------------------------------------------------


# ----------------------------------------------------------------------
ContainerT                                  = TypeVar("ContainerT")

class LazyContainer(Generic[ContainerT]):
    """Object that initializes itself on first access."""

    # ----------------------------------------------------------------------
    def __init__(
        self,
        create_container_func: Callable[[], ContainerT],
        initialized_value: Optional[ContainerT]=None,
    ):
        self._create_container_func         = create_container_func
        self._initialized_value             = initialized_value
        self._working_value                 = None

        # It isn't possible to monkeypatch __getitem__, so we need to have this level of
        # indirection. This means that there will always be an extra function call to get
        # to the underlying implementation, but that might be acceptable in some scenarios.

        # ----------------------------------------------------------------------
        def InternalInit(self):
            # Disconnect our overload of __getattr__ so that we can set these internal values

            # ----------------------------------------------------------------------
            def TempGetAttrImpl(self, *args, **kwargs):
                if args[0] == "_create_container_func":
                    return self._create_container_func

                return None

            # ----------------------------------------------------------------------

            self._getattr_impl = types.MethodType(TempGetAttrImpl, self)

            if self._initialized_value is None:
                container = self._create_container_func()

                self._initialized_value = container

            self._working_value = copy.deepcopy(self._initialized_value)

            # ----------------------------------------------------------------------
            def GetAttrImpl(self, *args, **kwargs):
                return self._working_value.__getattribute__(*args, **kwargs)

            # ----------------------------------------------------------------------
            def GetItemImpl(self, *args, **kwargs):
                return self._working_value.__getitem__(*args, **kwargs)

            # ----------------------------------------------------------------------

            self._getattr_impl = types.MethodType(GetAttrImpl, self)
            self._getitem_impl = types.MethodType(GetItemImpl, self)

        # ----------------------------------------------------------------------
        def InitialGetAttributeImpl(self, *args, **kwargs):
            InternalInit(self)
            return self._getattr_impl(*args, **kwargs)

        # ----------------------------------------------------------------------
        def InitialGetItemImpl(self, *args, **kwargs):
            InternalInit(self)
            return self._getitem_impl(*args, **kwargs)

        # ----------------------------------------------------------------------

        if self._initialized_value is not None:
            InternalInit(self)
        else:
            self._getattr_impl = types.MethodType(InitialGetAttributeImpl, self)
            self._getitem_impl = types.MethodType(InitialGetItemImpl, self)

    # ----------------------------------------------------------------------
    def Clone(self) -> "LazyContainer":
        return self.__class__(
            self._create_container_func,
            self._initialized_value,
        )

    # ----------------------------------------------------------------------
    def __getattr__(self, *args, **kwargs):
        return self._getattr_impl(*args, **kwargs)  # pylint: disable=not-callable

    # ----------------------------------------------------------------------
    def __getitem__(self, *args, **kwargs):
        return self._getitem_impl(*args, **kwargs)  # pylint: disable=not-callable
